"""Resilient execution engine for the surviving-Composition experiment.

Core invariant:

    compute -> persist -> consume

Expensive Composition fingerprints are durable evidence. Downstream stages
load that evidence rather than reconstructing it. The runner is restart-safe
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
from team_analysis.composition_pipeline import analyze_compositions_parallel_resilient
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
    """Emit a macro operational message to the live console only."""
    print(f"[trajectory-runner] {message}", flush=True)


def _detail(message: str) -> None:
    """Write forensic detail to the persistent flight-recorder log only."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{_wall_timestamp()} | {message}\n")
        handle.flush()


def _log(message: str) -> None:
    """Emit a macro operational event without mirroring it to the log.

    The console and forensic log are intentionally different observability
    channels. Callers use ``_detail`` for persistent forensic events.
    """
    _console(message)


def _load_fund_histories(funds) -> dict[str, pd.DataFrame]:
    histories: dict[str, pd.DataFrame] = {}
    _log(f"Loading NAV histories for {len(funds)} admitted funds")
    _detail(f"NAV_LOAD_START funds={len(funds)}")
    for index, fund in enumerate(funds, start=1):
        path = NAV_DIR / f"{fund.isin}.json"
        _log(f"  NAV {index}/{len(funds)}: {fund.isin}")
        _detail(f"NAV_LOAD_START index={index} total={len(funds)} isin={fund.isin} path={path}")
        if not path.exists():
            _detail(f"NAV_LOAD_FAILED isin={fund.isin} reason=missing_file path={path}")
            raise FileNotFoundError(f"Missing NAV evidence for {fund.isin}: {path}")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        observations = payload.get("observations")
        if not isinstance(observations, list):
            _detail(f"NAV_LOAD_FAILED isin={fund.isin} reason=invalid_observations")
            raise ValueError(f"Invalid NAV evidence observations: {path}")
        histories[fund.isin] = normalize_nav_history(pd.DataFrame(observations))
        _detail(f"NAV_READY isin={fund.isin} rows={len(histories[fund.isin])}")
    _detail(f"NAV_LOAD_COMPLETE funds={len(histories)}")
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
    _detail(
        "PURPOSES_READY "
        + " ".join(f"name={p.name} horizon={p.horizon_years}Y" for p in purposes)
    )
    return purposes


def _write_rows(path: Path, rows: list[dict]) -> None:
    """Atomically replace a CSV checkpoint after fully materializing its rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pd.DataFrame(rows).to_csv(temporary, index=False)
    temporary.replace(path)
    _log(f"  wrote {path.relative_to(PROJECT_ROOT)} ({len(rows)} rows)")
    _detail(f"CHECKPOINT_WRITTEN path={path.relative_to(PROJECT_ROOT)} rows={len(rows)}")


def _write_composition_candidates(teams) -> int:
    path = OUTPUT_DIR / "composition_candidates.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temporary.open("w", newline="", encoding="utf-8") as handle:
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
    temporary.replace(path)
    _log(f"  wrote {path.relative_to(PROJECT_ROOT)} ({count} rows)")
    _detail(f"COMPOSITION_CANDIDATES_WRITTEN path={path.relative_to(PROJECT_ROOT)} rows={count}")
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
    """Compute only missing fingerprints and persist each result immediately.

    The checkpoint scan deliberately uses two generator passes rather than
    materializing all Composition objects or all missing work units in memory.
    Composition generation is cheap and deterministic; expensive fingerprint
    computation is the part protected by durable per-Composition checkpoints.
    """
    total = 0
    existing = 0
    missing = 0
    for composition in _candidate_compositions(teams):
        total += 1
        if has_fingerprint(FINGERPRINT_DIR, composition):
            existing += 1
        else:
            missing += 1

    _log(
        f"  fingerprint checkpoint scan: total={total} "
        f"existing={existing} missing={missing}"
    )
    _detail(
        f"FINGERPRINT_CHECKPOINT_SCAN total={total} existing={existing} "
        f"missing={missing} workers={max_workers or 'auto'}"
    )
    if missing == 0:
        _log("  all Composition fingerprints already persisted; no recomputation required")
        _detail("FINGERPRINT_STAGE_SKIPPED reason=all_checkpoints_present")
        return total

    def missing_compositions():
        for composition in _candidate_compositions(teams):
            if not has_fingerprint(FINGERPRINT_DIR, composition):
                yield composition

    started = time.perf_counter()
    completed = 0
    failed = 0
    for composition, fingerprint, error in analyze_compositions_parallel_resilient(
        missing_compositions(),
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
            f"FINGERPRINT_PERSISTED index={completed}/{missing} "
            f"composition={identity} path={destination.relative_to(PROJECT_ROOT)}"
        )
        processed = completed + failed
        if processed % 1000 == 0 or processed == missing:
            elapsed = time.perf_counter() - started
            rate = processed / elapsed if elapsed else 0.0
            eta = (missing - processed) / rate if rate else 0.0
            _log(
                f"  Composition evidence: {processed}/{missing} missing work units "
                f"| persisted={completed} failed={failed} | rate={rate:.1f}/s | ETA~{eta:.0f}s"
            )
            _detail(
                f"FINGERPRINT_PROGRESS processed={processed} total_missing={missing} "
                f"persisted={completed} failed={failed} rate={rate:.3f} eta_seconds={eta:.1f}"
            )

    if failed:
        _detail(f"FINGERPRINT_STAGE_FAILED failed={failed} total_missing={missing}")
        raise RuntimeError(f"Composition evidence stage completed with {failed} failed work units")
    _log(
        f"  Composition evidence complete: {total} persisted | "
        f"newly computed={completed} | elapsed={time.perf_counter() - started:.1f}s"
    )
    _detail(
        f"FINGERPRINT_STAGE_COMPLETE total={total} newly_computed={completed} "
        f"elapsed_seconds={time.perf_counter() - started:.3f}"
    )
    return total


def _load_global_pairs_for_frontier(teams):
    """Stream persisted fingerprints into the global frontier."""
    for composition in _candidate_compositions(teams):
        path = fingerprint_path(FINGERPRINT_DIR, composition)
        if not path.is_file():
            _detail(f"GLOBAL_FINGERPRINT_MISSING composition={composition_identity(composition)} path={path}")
            raise FileNotFoundError(f"Missing Composition fingerprint checkpoint: {path}")
        _detail(f"GLOBAL_FINGERPRINT_LOADED composition={composition_identity(composition)} path={path}")
        yield composition, load_fingerprint(path, composition)


def _load_global_identities() -> list[str]:
    path = OUTPUT_DIR / "global_survivors.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing global frontier checkpoint: {path}")
    df = pd.read_csv(path, keep_default_na=False)
    if "composition" not in df.columns:
        raise ValueError(f"Invalid global frontier checkpoint: {path}")
    identities = df["composition"].tolist()
    _detail(f"GLOBAL_CHECKPOINT_READY path={path} survivors={len(identities)}")
    return identities


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
    _detail(f"MISSION_PURPOSE_START purpose={purpose.name} identities={len(identities)}")
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
    _detail(
        f"MISSION_PURPOSE_COMPLETE purpose={purpose.name} assessed={len(identities)} "
        f"achievability={len(achievability_survivors)} protection={len(protected)}"
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
        _detail("MISSION_SKIPPED reason=no_runnable_purposes")
        return

    _log(
        f"[MISSION] running {len(runnable)} independent Purpose gates from "
        f"{len(identities)} persisted global survivors"
    )
    _detail(
        f"MISSION_STAGE_START purposes={len(runnable)} identities={len(identities)} "
        f"workers={max_workers or 'auto'} skip_existing={skip_existing}"
    )
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_one_purpose, purpose, identities, funds_by_isin): purpose.name
            for purpose in runnable
        }
        _detail(f"MISSION_WORKERS_READY submitted={len(futures)}")
        for future in as_completed(futures):
            purpose_name = futures[future]
            try:
                name, assessed, achievable, protected = future.result()
                _log(
                    f"  {name}: assessed={assessed} achievability={achievable} "
                    f"protection={protected}"
                )
                _detail(
                    f"MISSION_WORKER_COMPLETE purpose={name} assessed={assessed} "
                    f"achievability={achievable} protection={protected}"
                )
            except Exception as exc:
                _detail(f"MISSION_FAILED purpose={purpose_name} error={exc!r}")
                raise
    _detail("MISSION_STAGE_COMPLETE")


def _observe_one_purpose(purpose: Purpose, identities: list[str], funds_by_isin) -> tuple[int, int]:
    pairs: list[tuple[Composition, CompositionFingerprint]] = []
    _detail(f"TRAJECTORY_PURPOSE_START purpose={purpose.name} survivors={len(identities)}")
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
    _detail(f"TRAJECTORY_PURPOSE_COMPLETE purpose={purpose.name} survivors={len(pairs)} rows={len(rows)}")
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
            _detail(f"TRAJECTORY_SKIPPED purpose={purpose.name} reason=no_finite_horizon")
            continue
        mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
        if not mission_path.exists():
            _log(f"  {purpose.name}: no persisted MISSION checkpoint; skipping")
            _detail(f"TRAJECTORY_SKIPPED purpose={purpose.name} reason=missing_mission_checkpoint")
            continue
        df = pd.read_csv(mission_path, keep_default_na=False)
        identities = df["composition"].tolist()
        jobs.append((purpose, identities))
        _detail(f"TRAJECTORY_JOB_READY purpose={purpose.name} survivors={len(identities)} path={mission_path}")

    if not jobs:
        _log("No persisted MISSION outputs require trajectory observation")
        _detail("TRAJECTORY_STAGE_SKIPPED reason=no_jobs")
        return

    _detail(f"TRAJECTORY_STAGE_START purposes={len(jobs)} workers={max_workers or 'auto'}")
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_observe_one_purpose, purpose, identities, funds_by_isin): purpose.name
            for purpose, identities in jobs
        }
        _detail(f"TRAJECTORY_WORKERS_READY submitted={len(futures)}")
        for future in as_completed(futures):
            purpose_name = futures[future]
            try:
                count, rows = future.result()
                _log(f"  {purpose_name}: trajectory complete survivors={count} rows={rows}")
                _detail(f"TRAJECTORY_WORKER_COMPLETE purpose={purpose_name} survivors={count} rows={rows}")
            except Exception as exc:
                _detail(f"TRAJECTORY_FAILED purpose={purpose_name} error={exc!r}")
                raise
    _log("RESUME DONE")
    _detail("TRAJECTORY_STAGE_COMPLETE")


def run(as_of: str, resume_from: str | None = None, workers: int | None = None) -> None:
    valuation_date = pd.Timestamp(as_of)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _log(f"START as-of {valuation_date.date()} mode={resume_from or 'full'} workers={workers or 'auto'}")
    _detail(
        f"RUN_START as_of={valuation_date.date()} mode={resume_from or 'full'} "
        f"workers={workers or 'auto'} log={LOG_PATH}"
    )

    funds = load_admissible_funds()
    histories = _load_fund_histories(funds)
    purposes = _load_purposes(valuation_date)
    funds_by_isin = {fund.isin: fund for fund in funds}
    _detail(f"INPUTS_READY funds={len(funds)} purposes={len(purposes)}")

    if resume_from == "mission":
        _log("[RESUME MISSION] Loading persisted Purpose checkpoints")
        _detail("RESUME_MISSION_START")
        _observe_persisted_mission_outputs(purposes, funds_by_isin, max_workers=workers)
        _detail("RESUME_MISSION_COMPLETE")
        return

    if resume_from == "global":
        _log("[RESUME GLOBAL] Loading persisted global Composition evidence")
        _detail("RESUME_GLOBAL_START")
        _run_mission_from_global(purposes, funds_by_isin, max_workers=workers, skip_existing=True)
        _log("RESUME GLOBAL DONE")
        _detail("RESUME_GLOBAL_COMPLETE")
        return

    _log("[1/7] Loading admitted funds")
    _log(f"  admitted funds: {len(funds)}")
    _detail(f"STAGE_1_COMPLETE admitted_funds={len(funds)}")
    _log("[2/7] Loading persisted NAV evidence")
    _log("[3/7] Loading Purpose inputs")
    _detail(f"STAGE_2_3_COMPLETE nav_funds={len(histories)} purposes={len(purposes)}")
    _log("[4/7] Running TEAM pipeline — this may be computationally heavy")
    stage_started = time.perf_counter()
    _detail("TEAM_STAGE_START")
    teams = run_team_pipeline(funds=funds, fund_histories=histories)
    _log(f"  TEAM survivors: {len(teams)} | elapsed={time.perf_counter() - stage_started:.1f}s")
    _detail(f"TEAM_STAGE_COMPLETE survivors={len(teams)} elapsed_seconds={time.perf_counter() - stage_started:.3f}")
    _write_rows(
        OUTPUT_DIR / "team_survivors.csv",
        [{"team": "|".join(member.isin for member in team.members), "members": len(team.members)} for team in teams],
    )

    _log("[5/7] Generating and persisting Composition fingerprints")
    expected_total = _write_composition_candidates(teams)
    _persist_composition_evidence(teams, histories, max_workers=workers)

    _log("[6/7] Applying existing MISSION gates")
    stage_started = time.perf_counter()
    _detail("GLOBAL_FRONTIER_STAGE_START")
    global_survivors = global_composition_frontier(_load_global_pairs_for_frontier(teams))
    _log(
        f"  global Composition frontier: {len(global_survivors)} | "
        f"elapsed={time.perf_counter() - stage_started:.1f}s"
    )
    _detail(
        f"GLOBAL_FRONTIER_STAGE_COMPLETE survivors={len(global_survivors)} "
        f"elapsed_seconds={time.perf_counter() - stage_started:.3f}"
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
    _detail("RUN_COMPLETE")


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


if __name__ == "__main__":
    main()
