"""Resilient execution engine for the surviving-Composition experiment.

Core invariant:

    compute -> persist -> consume

Expensive Composition fingerprints are durable evidence.  Downstream stages
load that evidence rather than reconstructing it.  The runner is restart-safe
across interruption, sleep, worker failure, and process crashes.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd

from fund_analysis.admissible_funds import load_admissible_funds
from lakshya_core.nav_history import normalize_nav_history
from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition_fingerprint_store import (
    fingerprint_path,
    has_fingerprint,
    load_fingerprint,
    persist_fingerprint,
)
from team_analysis.composition_frontier import global_composition_frontier
from team_analysis.composition_pipeline import (
    analyze_compositions_parallel_resilient,
)
from team_analysis.generate_compositions import generate_compositions
from team_analysis.protection_frontier import protection_frontier
from team_analysis.run_team_pipeline import run_team_pipeline
from team_analysis.team import Team

from .achievability_interpretation import AchievabilityStatus, assess_achievability
from .models import Purpose
from .survivor_trajectory_experiment import observe_survivors_for_purpose

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
NAV_DIR = DATA_DIR / "nav"
PURPOSES_PATH = DATA_DIR / "purpose" / "purposes.csv"
FINGERPRINT_DIR = DATA_DIR / "fingerprints" / "composition"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_PATH = OUTPUT_DIR / "trajectory_pipeline.log"


def _wall_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _console(message: str) -> None:
    print(f"[trajectory-runner] {message}", flush=True)


def _detail(message: str) -> None:
    """Write forensic detail to the persistent flight-recorder log only."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{_wall_timestamp()} | {message}\n")
        handle.flush()


def _log(message: str) -> None:
    """Write a macro console heartbeat and the same event to the log."""
    _console(message)
    _detail(message)


def _load_fund_histories(funds) -> dict[str, pd.DataFrame]:
    histories: dict[str, pd.DataFrame] = {}
    _log(f"Loading NAV histories for {len(funds)} admitted funds")
    for index, fund in enumerate(funds, start=1):
        path = NAV_DIR / f"{fund.isin}.json"
        _log(f"  NAV {index}/{len(funds)}: {fund.isin}")
        if not path.exists():
            raise FileNotFoundError(f"Missing NAV evidence for {fund.isin}: {path}")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        observations = payload.get("observations")
        if not isinstance(observations, list):
            raise ValueError(f"Invalid NAV evidence observations: {path}")
        histories[fund.isin] = normalize_nav_history(pd.DataFrame(observations))
        _detail(f"NAV_READY isin={fund.isin} rows={len(histories[fund.isin])}")
    return histories


def _floor_years(start: pd.Timestamp, due: pd.Timestamp) -> int:
    years = due.year - start.year
    anniversary = start + pd.DateOffset(years=years)
    if anniversary > due:
        years -= 1
    return years


def _load_purposes(as_of: pd.Timestamp) -> list[Purpose]:
    df = pd.read_csv(PURPOSES_PATH, keep_default_na=False)
    required = {"name", "due", "value", "desired", "monthly_plan"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Purpose input is missing required columns: {sorted(missing)}")

    purposes: list[Purpose] = []
    for row in df.to_dict("records"):
        due_raw = str(row["due"]).strip()
        if due_raw.upper() == "NA" or not due_raw:
            purposes.append(Purpose(name=str(row["name"]), current_capital=float(row["value"])))
            continue
        due = pd.Timestamp(due_raw)
        horizon = _floor_years(as_of, due)
        if horizon <= 0:
            raise ValueError(f"Purpose due date is not beyond as-of date: {row['name']}")
        purposes.append(
            Purpose(
                name=str(row["name"]),
                current_capital=float(row["value"]),
                desired_target=float(row["desired"]),
                horizon_years=horizon,
                monthly_contribution=float(row["monthly_plan"]),
            )
        )
    _log("Loaded purposes: " + ", ".join(f"{p.name}={p.horizon_years}Y" for p in purposes))
    return purposes


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    _log(f"  wrote {path.relative_to(PROJECT_ROOT)} ({len(rows)} rows)")


def _write_composition_candidates(teams) -> int:
    path = OUTPUT_DIR / "composition_candidates.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("composition", "team"))
        writer.writeheader()
        for team in teams:
            for composition in generate_compositions(team):
                writer.writerow(
                    {
                        "composition": composition_identity(composition),
                        "team": "|".join(member.isin for member in composition.team.members),
                    }
                )
                count += 1
    _log(f"  wrote {path.relative_to(PROJECT_ROOT)} ({count} rows)")
    return count


def _candidate_compositions(teams):
    for team in teams:
        yield from generate_compositions(team)


def _persist_composition_evidence(
    teams,
    fund_histories: dict[str, pd.DataFrame],
    *,
    max_workers: int | None,
) -> int:
    """Compute only missing fingerprints and persist each result immediately."""
    all_compositions = list(_candidate_compositions(teams))
    missing = [c for c in all_compositions if not has_fingerprint(FINGERPRINT_DIR, c)]
    existing = len(all_compositions) - len(missing)
    _log(
        f"  fingerprint checkpoint scan: total={len(all_compositions)} "
        f"existing={existing} missing={len(missing)}"
    )
    _detail(
        f"FINGERPRINT_CHECKPOINT_SCAN total={len(all_compositions)} "
        f"existing={existing} missing={len(missing)} workers={max_workers or 'auto'}"
    )
    if not missing:
        _log("  all Composition fingerprints already persisted; no recomputation required")
        return len(all_compositions)

    started = time.perf_counter()
    completed = 0
    failed = 0
    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=None,
    ) as _unused:
        pass

    # The resilient helper owns the worker pool and converts one failed work
    # unit into an error result, so unrelated completed work remains durable.
    for composition, fingerprint, error in analyze_compositions_parallel_resilient(
        missing,
        fund_histories,
        max_workers=max_workers,
    ):
        identity = composition_identity(composition)
        if error is not None:
            failed += 1
            _detail(f"FINGERPRINT_FAILED composition={identity} error={error!r}")
            continue
        destination = persist_fingerprint(fingerprint, FINGERPRINT_DIR)
        completed += 1
        _detail(
            f"FINGERPRINT_PERSISTED index={completed}/{len(missing)} "
            f"composition={identity} path={destination.relative_to(PROJECT_ROOT)}"
        )
        processed = completed + failed
        if processed % 1000 == 0 or processed == len(missing):
            elapsed = time.perf_counter() - started
            rate = processed / elapsed if elapsed else 0.0
            eta = (len(missing) - processed) / rate if rate else 0.0
            _log(
                f"  Composition evidence: {processed}/{len(missing)} missing work units "
                f"| persisted={completed} failed={failed} | rate={rate:.1f}/s | ETA~{eta:.0f}s"
            )

    if failed:
        raise RuntimeError(f"Composition evidence stage completed with {failed} failed work units")
    _log(
        f"  Composition evidence complete: {len(all_compositions)} persisted | "
        f"newly computed={completed} | elapsed={time.perf_counter() - started:.1f}s"
    )
    return len(all_compositions)


def _load_global_pairs_for_frontier(teams):
    """Stream persisted fingerprints into the global frontier."""
    for composition in _candidate_compositions(teams):
        path = fingerprint_path(FINGERPRINT_DIR, composition)
        if not path.is_file():
            raise FileNotFoundError(f"Missing Composition fingerprint checkpoint: {path}")
        yield composition, load_fingerprint(path, composition)


def _load_global_identities() -> list[str]:
    path = OUTPUT_DIR / "global_survivors.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing global frontier checkpoint: {path}")
    df = pd.read_csv(path, keep_default_na=False)
    if "composition" not in df.columns:
        raise ValueError(f"Invalid global frontier checkpoint: {path}")
    return df["composition"].tolist()


def _composition_from_identity(identity: str, funds_by_isin) -> Composition:
    members_raw, weights_raw = identity.split("|", 1)
    member_isins = [value for value in members_raw.split(",") if value]
    weights = {}
    for token in weights_raw.split(","):
        isin, value = token.split("=", 1)
        weights[isin] = float(value)
    if set(member_isins) != set(weights):
        raise ValueError(f"Composition identity has inconsistent members/weights: {identity}")
    members = tuple(funds_by_isin[isin] for isin in sorted(member_isins))
    return Composition(team=Team(members=members), weights=weights)


def _run_one_purpose(purpose: Purpose, identities: list[str], funds_by_isin):
    """Run one independent Purpose from durable global Composition evidence."""
    if purpose.horizon_years is None:
        return purpose.name, 0, 0, 0
    achievability_survivors: list[tuple[Composition, CompositionFingerprint]] = []
    assessments: list[dict] = []
    for identity in identities:
        composition = _composition_from_identity(identity, funds_by_isin)
        fingerprint = load_fingerprint(fingerprint_path(FINGERPRINT_DIR, composition), composition)
        assessment = assess_achievability(purpose, fingerprint)
        assessments.append(
            {
                "composition": identity,
                "status": assessment.status.value,
                "required_annual_return": assessment.required_annual_return,
                "comparison_horizon_years": assessment.comparison_horizon_years,
                "observed_upper_return": assessment.observed_upper_return,
            }
        )
        if assessment.status == AchievabilityStatus.WITHIN_OBSERVED_TERRAIN:
            achievability_survivors.append((composition, fingerprint))

    _write_rows(OUTPUT_DIR / f"achievability_{purpose.name}.csv", assessments)
    protected = protection_frontier(achievability_survivors)
    _write_rows(
        OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv",
        [{"composition": composition_identity(composition)} for composition in protected],
    )
    return purpose.name, len(identities), len(achievability_survivors), len(protected)


def _run_mission_from_global(
    purposes: list[Purpose],
    funds_by_isin,
    *,
    max_workers: int | None,
    skip_existing: bool,
) -> None:
    identities = _load_global_identities()
    runnable = [
        purpose
        for purpose in purposes
        if purpose.horizon_years is not None
        and not (skip_existing and (OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv").exists())
    ]
    if not runnable:
        _log("No Purpose requires MISSION work")
        return

    _log(
        f"[MISSION] running {len(runnable)} independent Purpose gates from "
        f"{len(identities)} persisted global survivors"
    )
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_one_purpose, purpose, identities, funds_by_isin): purpose.name
            for purpose in runnable
        }
        for future in as_completed(futures):
            purpose_name = futures[future]
            try:
                name, assessed, achievable, protected = future.result()
                _log(
                    f"  {name}: assessed={assessed} achievability={achievable} "
                    f"protection={protected}"
                )
            except Exception as exc:
                _detail(f"MISSION_FAILED purpose={purpose_name} error={exc!r}")
                raise


def _observe_one_purpose(purpose: Purpose, identities: list[str], funds_by_isin) -> tuple[int, int]:
    pairs: list[tuple[Composition, CompositionFingerprint]] = []
    for identity in identities:
        composition = _composition_from_identity(identity, funds_by_isin)
        fingerprint = load_fingerprint(fingerprint_path(FINGERPRINT_DIR, composition), composition)
        pairs.append((composition, fingerprint))
    observations = observe_survivors_for_purpose(pairs, purpose.horizon_years)
    rows: list[dict] = []
    for composition, _ in pairs:
        observation = observations[composition_identity(composition)]
        for point in observation.points:
            rows.append(
                {
                    "composition": composition_identity(composition),
                    "horizon_years": observation.horizon_years,
                    "date": point.date.strftime("%Y-%m-%d"),
                    "elapsed_days": point.elapsed_days,
                    "nav": point.nav,
                    "normalized_nav": point.normalized_nav,
                }
            )
    _write_rows(OUTPUT_DIR / "trajectory_observations" / f"{purpose.name}.csv", rows)
    return len(pairs), len(rows)


def _observe_persisted_mission_outputs(
    purposes: list[Purpose],
    funds_by_isin,
    *,
    max_workers: int | None,
) -> None:
    jobs = []
    for purpose in purposes:
        if purpose.horizon_years is None:
            _log(f"  {purpose.name}: no finite horizon; skipping trajectory")
            continue
        mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
        if not mission_path.exists():
            _log(f"  {purpose.name}: no persisted MISSION checkpoint; skipping")
            continue
        df = pd.read_csv(mission_path, keep_default_na=False)
        jobs.append((purpose, df["composition"].tolist()))

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_observe_one_purpose, purpose, identities, funds_by_isin): purpose.name
            for purpose, identities in jobs
        }
        for future in as_completed(futures):
            purpose_name = futures[future]
            try:
                count, rows = future.result()
                _log(f"  {purpose_name}: trajectory complete survivors={count} rows={rows}")
            except Exception as exc:
                _detail(f"TRAJECTORY_FAILED purpose={purpose_name} error={exc!r}")
                raise
    _log("RESUME DONE")


def run(as_of: str, resume_from: str | None = None, workers: int | None = None) -> None:
    valuation_date = pd.Timestamp(as_of)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _log(f"START as-of {valuation_date.date()} mode={resume_from or 'full'} workers={workers or 'auto'}")

    funds = load_admissible_funds()
    histories = _load_fund_histories(funds)
    purposes = _load_purposes(valuation_date)
    funds_by_isin = {fund.isin: fund for fund in funds}

    if resume_from == "mission":
        _log("[RESUME MISSION] Loading persisted Purpose checkpoints")
        _observe_persisted_mission_outputs(purposes, funds_by_isin, max_workers=workers)
        return

    if resume_from == "global":
        _log("[RESUME GLOBAL] Loading persisted global Composition evidence")
        _run_mission_from_global(purposes, funds_by_isin, max_workers=workers, skip_existing=True)
        _log("RESUME GLOBAL DONE")
        return

    _log("[1/7] Loading admitted funds")
    _log(f"  admitted funds: {len(funds)}")
    _log("[2/7] Loading persisted NAV evidence")
    _log("[3/7] Loading Purpose inputs")
    _log("[4/7] Running TEAM pipeline — this may be computationally heavy")
    stage_started = time.perf_counter()
    teams = run_team_pipeline(funds=funds, fund_histories=histories)
    _log(f"  TEAM survivors: {len(teams)} | elapsed={time.perf_counter() - stage_started:.1f}s")
    _write_rows(
        OUTPUT_DIR / "team_survivors.csv",
        [{"team": "|".join(member.isin for member in team.members), "members": len(team.members)} for team in teams],
    )

    _log("[5/7] Generating and persisting Composition fingerprints")
    expected_total = _write_composition_candidates(teams)
    _persist_composition_evidence(teams, histories, max_workers=workers)

    _log("[6/7] Applying existing MISSION gates")
    stage_started = time.perf_counter()
    global_survivors = global_composition_frontier(_load_global_pairs_for_frontier(teams))
    _log(
        f"  global Composition frontier: {len(global_survivors)} | "
        f"elapsed={time.perf_counter() - stage_started:.1f}s"
    )
    _write_rows(
        OUTPUT_DIR / "global_survivors.csv",
        [{"composition": composition_identity(composition)} for composition in global_survivors],
    )
    _run_mission_from_global(purposes, funds_by_isin, max_workers=workers, skip_existing=False)

    _log("[7/7] Observing Purpose trajectories")
    _observe_persisted_mission_outputs(purposes, funds_by_isin, max_workers=workers)
    _write_rows(
        OUTPUT_DIR / "pipeline_summary.csv",
        [
            {"stage": "admissible_funds", "count": len(funds)},
            {"stage": "team_frontier", "count": len(teams)},
            {"stage": "composition_candidates", "count": expected_total},
            {"stage": "global_composition_frontier", "count": len(global_survivors)},
        ],
    )
    _log("DONE")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="Purpose valuation date, e.g. 2026-08-31")
    parser.add_argument(
        "--resume-from",
        choices=("mission", "global"),
        help="Resume from persisted MISSION or global checkpoints without recomputing fingerprints",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Optional ProcessPoolExecutor worker count; default delegates to Python",
    )
    args = parser.parse_args()
    run(args.as_of, args.resume_from, args.workers)
