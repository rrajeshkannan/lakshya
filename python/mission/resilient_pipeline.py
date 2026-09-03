"""Resilient execution engine for the surviving-Composition experiment.

Core invariant:

    compute -> persist -> validate -> consume

Expensive Composition fingerprints are durable evidence. Downstream stages
load that evidence rather than reconstructing it. Stage CSVs are reusable only
when their atomic completion marker, content hash, as-of date, and input
provenance all validate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd

from fund_analysis.admissible_funds import load_admissible_funds
from lakshya_core.nav_history import normalize_nav_history
from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition_fingerprint_store import (
    FINGERPRINT_SCHEMA_VERSION,
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
from .durable_stage_output import (
    is_valid_csv_checkpoint,
    load_csv_checkpoint,
    write_csv_checkpoint,
)
from .models import Purpose
from .observation_horizon import nearest_supported_horizon
from .survivor_trajectory_experiment import (
    TRAJECTORY_CONTRACT_VERSION,
    observe_survivors_for_purpose,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
NAV_DIR = DATA_DIR / "nav"
PURPOSES_PATH = DATA_DIR / "purpose" / "purposes.csv"
FINGERPRINT_DIR = DATA_DIR / "fingerprints" / "composition"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_PATH = OUTPUT_DIR / "trajectory_pipeline.log"
MANIFEST_PATH = OUTPUT_DIR / "pipeline_run_manifest.json"

_RUN_MANIFEST: dict | None = None


def _wall_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _console(message: str) -> None:
    print(f"[trajectory-runner] {message}", flush=True)


def _detail(message: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{_wall_timestamp()} | {message}\n")
        handle.flush()


def _log(message: str) -> None:
    _console(message)


def _event(message: str) -> None:
    """Write a forensic event without echoing it to the console."""
    _detail(message)


def _write_manifest() -> None:
    if _RUN_MANIFEST is None:
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(MANIFEST_PATH.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(_RUN_MANIFEST, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
    temporary.replace(MANIFEST_PATH)


def _manifest_update(stage: str, status: str, **metrics) -> None:
    if _RUN_MANIFEST is None:
        return
    entry = {"status": status, "updated_at": _wall_timestamp()}
    entry.update(metrics)
    _RUN_MANIFEST["stages"][stage] = entry
    _write_manifest()
    _detail(
        "MANIFEST_UPDATE "
        + " ".join(
            [f"stage={stage}", f"status={status}"]
            + [f"{key}={value}" for key, value in metrics.items()]
        )
    )


def _as_of_string() -> str:
    if _RUN_MANIFEST is None:
        raise RuntimeError("Pipeline manifest has not been initialized")
    return str(_RUN_MANIFEST["as_of"])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _input_hash(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Required checkpoint input is missing: {path}")
    return _sha256(path)


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
    required = {"name", "due", "value", "desired", "monthly_plan", "analytical_horizon_years"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Purpose input is missing required columns: {sorted(missing)}")
    purposes: list[Purpose] = []
    for row in df.to_dict("records"):
        name = str(row["name"])
        due_raw = str(row["due"]).strip()
        analytical_raw = str(row["analytical_horizon_years"]).strip()
        analytical_horizon = int(analytical_raw) if analytical_raw else None
        if due_raw.upper() == "NA" or not due_raw:
            if analytical_horizon is None:
                raise ValueError(f"Purpose without a finite due date requires analytical_horizon_years: {name}")
            purposes.append(
                Purpose(
                    name=name,
                    current_capital=float(row["value"]),
                    analytical_horizon_years=analytical_horizon,
                )
            )
            continue
        due = pd.Timestamp(due_raw)
        horizon = _floor_years(as_of, due)
        if horizon <= 0:
            raise ValueError(f"Purpose due date is not beyond as-of date: {name}")
        purposes.append(
            Purpose(
                name=name,
                current_capital=float(row["value"]),
                desired_target=float(row["desired"]),
                horizon_years=horizon,
                monthly_contribution=float(row["monthly_plan"]),
            )
        )
    _log("Loaded purposes: " + ", ".join(f"{p.name}={p.trajectory_horizon_years}Y" for p in purposes))
    _detail(
        "PURPOSES_READY "
        + " ".join(f"name={p.name} horizon={p.trajectory_horizon_years}Y achievability={p.has_achievability}" for p in purposes)
    )
    return purposes


def _write_rows(
    path: Path,
    rows: list[dict],
    *,
    stage: str | None = None,
    inputs: dict[str, str] | None = None,
    as_of: str | None = None,
) -> int:
    """Write a CSV atomically; stage outputs also receive a durable marker."""
    if stage is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        pd.DataFrame(rows).to_csv(temporary, index=False)
        temporary.replace(path)
        count = len(rows)
    else:
        checkpoint_as_of = as_of if as_of is not None else _as_of_string()
        count = write_csv_checkpoint(path, rows, stage=stage, as_of=checkpoint_as_of, inputs=inputs)
    _log(f"  wrote {path.relative_to(PROJECT_ROOT)} ({count} rows)")
    _detail(
        f"CHECKPOINT_WRITTEN path={path.relative_to(PROJECT_ROOT)} rows={count}"
        + (f" stage={stage}" if stage else "")
    )
    return count


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


def _persist_composition_evidence(teams, fund_histories, *, max_workers: int | None) -> int:
    """Compute only missing fingerprints and persist each result immediately."""
    total = existing = missing = 0
    for composition in _candidate_compositions(teams):
        total += 1
        if has_fingerprint(FINGERPRINT_DIR, composition):
            existing += 1
        else:
            missing += 1
    _log(f"  fingerprint checkpoint scan: total={total} existing={existing} missing={missing}")
    _detail(f"FINGERPRINT_CHECKPOINT_SCAN total={total} existing={existing} missing={missing} workers={max_workers or 'auto'}")
    _manifest_update("composition_evidence", "running", total=total, existing=existing, missing=missing)
    if missing == 0:
        _log("  all Composition fingerprints already persisted; no recomputation required")
        _detail("FINGERPRINT_STAGE_SKIPPED reason=all_checkpoints_present")
        _manifest_update("composition_evidence", "complete", total=total, newly_computed=0, reused=existing)
        return total

    def missing_compositions():
        for composition in _candidate_compositions(teams):
            if not has_fingerprint(FINGERPRINT_DIR, composition):
                yield composition

    started = time.perf_counter()
    completed = failed = 0
    for composition, fingerprint, error in analyze_compositions_parallel_resilient(
        missing_compositions(), fund_histories, max_workers=max_workers
    ):
        identity = composition_identity(composition)
        if error is not None:
            failed += 1
            _detail(f"FINGERPRINT_FAILED composition={identity} error={error!r}")
            continue
        destination = persist_fingerprint(fingerprint, FINGERPRINT_DIR)
        completed += 1
        _detail(f"FINGERPRINT_PERSISTED index={completed}/{missing} composition={identity} path={destination.relative_to(PROJECT_ROOT)}")
        processed = completed + failed
        if processed % 1000 == 0 or processed == missing:
            elapsed = time.perf_counter() - started
            rate = processed / elapsed if elapsed else 0.0
            eta = (missing - processed) / rate if rate else 0.0
            _log(f"  Composition evidence: {processed}/{missing} missing work units | persisted={completed} failed={failed} | rate={rate:.1f}/s | ETA~{eta:.0f}s")
            _detail(f"FINGERPRINT_PROGRESS processed={processed} total_missing={missing} persisted={completed} failed={failed} rate={rate:.3f} eta_seconds={eta:.1f}")
            _manifest_update("composition_evidence", "running", total=total, existing=existing, missing=missing, processed=processed, persisted=completed, failed=failed)
    if failed:
        _detail(f"FINGERPRINT_STAGE_FAILED failed={failed} total_missing={missing}")
        _manifest_update("composition_evidence", "failed", total=total, newly_computed=completed, failed=failed)
        raise RuntimeError(f"Composition evidence stage completed with {failed} failed work units")
    elapsed = time.perf_counter() - started
    _log(f"  Composition evidence complete: {total} persisted | newly computed={completed} | elapsed={elapsed:.1f}s")
    _detail(f"FINGERPRINT_STAGE_COMPLETE total={total} newly_computed={completed} elapsed_seconds={elapsed:.3f}")
    _manifest_update("composition_evidence", "complete", total=total, reused=existing, newly_computed=completed, elapsed_seconds=round(elapsed, 3))
    return total


def _load_global_pairs_for_frontier(teams):
    for composition in _candidate_compositions(teams):
        path = fingerprint_path(FINGERPRINT_DIR, composition)
        if not path.is_file():
            _detail(f"GLOBAL_FINGERPRINT_MISSING composition={composition_identity(composition)} path={path}")
            raise FileNotFoundError(f"Missing Composition fingerprint checkpoint: {path}")
        _detail(f"GLOBAL_FINGERPRINT_LOADED composition={composition_identity(composition)} path={path}")
        yield composition, load_fingerprint(path, composition)


def _global_inputs() -> dict[str, str]:
    return {
        "composition_candidates_sha256": _input_hash(OUTPUT_DIR / "composition_candidates.csv"),
        "fingerprint_schema_version": str(FINGERPRINT_SCHEMA_VERSION),
    }


def _load_global_identities() -> list[str]:
    path = OUTPUT_DIR / "global_survivors.csv"
    df = load_csv_checkpoint(path, stage="global_frontier", as_of=_as_of_string(), inputs=_global_inputs())
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


def _run_one_purpose(purpose: Purpose, identities: list[str], funds_by_isin, as_of: str):
    if purpose.trajectory_horizon_years is None:
        return purpose.name, 0, 0, 0

    qualified: list[tuple[Composition, CompositionFingerprint]] = []
    assessments: list[dict] = []
    _detail(f"MISSION_PURPOSE_START purpose={purpose.name} identities={len(identities)} achievability={purpose.has_achievability}")
    for identity in identities:
        composition = _composition_from_identity(identity, funds_by_isin)
        fingerprint = load_fingerprint(fingerprint_path(FINGERPRINT_DIR, composition), composition)
        assessment = assess_achievability(purpose, fingerprint)
        comparison_horizon = (
            assessment.comparison_horizon_years
            if purpose.has_achievability
            else nearest_supported_horizon(purpose.analytical_horizon_years)
        )
        assessments.append({
            "composition": identity,
            "status": assessment.status.value,
            "required_annual_return": assessment.required_annual_return,
            "comparison_horizon_years": comparison_horizon,
            "observed_upper_return": assessment.observed_upper_return,
        })
        if not purpose.has_achievability or assessment.status == AchievabilityStatus.WITHIN_OBSERVED_TERRAIN:
            qualified.append((composition, fingerprint))

    global_path = OUTPUT_DIR / "global_survivors.csv"
    global_inputs = {
        "global_survivors_sha256": _sha256(global_path),
        "global_checkpoint_stage": "global_frontier",
    }
    achievability_path = OUTPUT_DIR / f"achievability_{purpose.name}.csv"
    _write_rows(achievability_path, assessments, stage="mission_achievability", inputs=global_inputs, as_of=as_of)

    protected = protection_frontier(qualified)
    mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
    _write_rows(
        mission_path,
        [{"composition": composition_identity(composition)} for composition in protected],
        stage="mission",
        inputs={"achievability_sha256": _sha256(achievability_path)},
        as_of=as_of,
    )
    _detail(
        f"MISSION_PURPOSE_COMPLETE purpose={purpose.name} assessed={len(identities)} "
        f"achievability={len(qualified) if purpose.has_achievability else 'not_applicable'} protection={len(protected)}"
    )
    return purpose.name, len(identities), len(qualified), len(protected)


def _mission_checkpoint_valid(purpose: Purpose) -> bool:
    mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
    achievability_path = OUTPUT_DIR / f"achievability_{purpose.name}.csv"
    if not mission_path.is_file() or not achievability_path.is_file():
        return False
    try:
        if not is_valid_csv_checkpoint(
            achievability_path,
            stage="mission_achievability",
            as_of=_as_of_string(),
            inputs={
                "global_survivors_sha256": _sha256(OUTPUT_DIR / "global_survivors.csv"),
                "global_checkpoint_stage": "global_frontier",
            },
        ):
            return False
        return is_valid_csv_checkpoint(
            mission_path,
            stage="mission",
            as_of=_as_of_string(),
            inputs={"achievability_sha256": _sha256(achievability_path)},
        )
    except (FileNotFoundError, OSError):
        return False


def _run_mission_from_global(purposes, funds_by_isin, *, max_workers, skip_existing) -> None:
    identities = _load_global_identities()
    runnable = [
        purpose for purpose in purposes
        if purpose.trajectory_horizon_years is not None
        and not (skip_existing and _mission_checkpoint_valid(purpose))
    ]
    if not runnable:
        _log("No Purpose requires MISSION work")
        _detail("MISSION_SKIPPED reason=no_runnable_purposes")
        _manifest_update("mission", "complete", purposes=0, global_survivors=len(identities))
        return
    _log(f"[MISSION] running {len(runnable)} independent Purpose gates from {len(identities)} persisted global survivors")
    _detail(f"MISSION_STAGE_START purposes={len(runnable)} identities={len(identities)} workers={max_workers or 'auto'} skip_existing={skip_existing}")
    _manifest_update("mission", "running", purposes=len(runnable), global_survivors=len(identities))
    as_of = _as_of_string()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_one_purpose, purpose, identities, funds_by_isin, as_of): purpose.name
            for purpose in runnable
        }
        _detail(f"MISSION_WORKERS_READY submitted={len(futures)}")
        for future in as_completed(futures):
            purpose_name = futures[future]
            try:
                name, assessed, qualified, protected = future.result()
                label = "achievability" if next(p for p in runnable if p.name == name).has_achievability else "analytical_horizon"
                _log(f"  {name}: assessed={assessed} {label}={qualified} protection={protected}")
                _detail(f"MISSION_WORKER_COMPLETE purpose={name} assessed={assessed} qualified={qualified} protection={protected}")
            except Exception as exc:
                _detail(f"MISSION_FAILED purpose={purpose_name} error={exc!r}")
                _manifest_update("mission", "failed", failed_purpose=purpose_name, error=repr(exc))
                raise
    _detail("MISSION_STAGE_COMPLETE")
    _manifest_update("mission", "complete", purposes=len(runnable), global_survivors=len(identities))


def _observe_one_purpose(purpose: Purpose, identities: list[str], funds_by_isin, as_of: str):
    pairs: list[tuple[Composition, CompositionFingerprint]] = []
    _detail(f"TRAJECTORY_PURPOSE_START purpose={purpose.name} survivors={len(identities)}")
    for identity in identities:
        composition = _composition_from_identity(identity, funds_by_isin)
        fingerprint = load_fingerprint(fingerprint_path(FINGERPRINT_DIR, composition), composition)
        pairs.append((composition, fingerprint))

    purpose_horizon = purpose.trajectory_horizon_years
    if purpose_horizon is None:
        raise ValueError(f"Purpose has no trajectory horizon: {purpose.name}")
    nominal_horizon = nearest_supported_horizon(purpose_horizon)
    observations = observe_survivors_for_purpose(pairs, purpose_horizon)
    rows: list[dict] = []
    coverage_rows: list[dict] = []
    for composition, _ in pairs:
        identity = composition_identity(composition)
        observation = observations.get(identity)
        if observation is None:
            coverage_rows.append({
                "composition": identity,
                "purpose_horizon_years": purpose_horizon,
                "nominal_trajectory_horizon_years": nominal_horizon,
                "trajectory_horizon_years": "",
                "status": "insufficient_history",
            })
            continue
        coverage_rows.append({
            "composition": identity,
            "purpose_horizon_years": purpose_horizon,
            "nominal_trajectory_horizon_years": nominal_horizon,
            "trajectory_horizon_years": observation.horizon_years,
            "status": "observed",
        })
        for point in observation.points:
            rows.append({
                "composition": identity,
                "purpose_horizon_years": purpose_horizon,
                "nominal_trajectory_horizon_years": nominal_horizon,
                "horizon_years": observation.horizon_years,
                "date": point.date.strftime("%Y-%m-%d"),
                "elapsed_days": point.elapsed_days,
                "nav": point.nav,
                "normalized_nav": point.normalized_nav,
            })
    mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
    trajectory_inputs = {
        "mission_sha256": _sha256(mission_path),
        "trajectory_contract_version": str(TRAJECTORY_CONTRACT_VERSION),
    }
    trajectory_path = OUTPUT_DIR / "trajectory_observations" / f"{purpose.name}.csv"
    coverage_path = OUTPUT_DIR / "trajectory_observations" / f"{purpose.name}_coverage.csv"
    _write_rows(trajectory_path, rows, stage="trajectory", inputs=trajectory_inputs, as_of=as_of)
    _write_rows(coverage_path, coverage_rows, stage="trajectory_coverage", inputs=trajectory_inputs, as_of=as_of)
    observed = sum(1 for row in coverage_rows if row["status"] == "observed")
    unavailable = len(coverage_rows) - observed
    _detail(f"TRAJECTORY_PURPOSE_COMPLETE purpose={purpose.name} survivors={len(pairs)} observed={observed} insufficient_history={unavailable} rows={len(rows)}")
    return len(pairs), len(rows), observed, unavailable


def _trajectory_checkpoint_valid(purpose: Purpose) -> bool:
    trajectory_path = OUTPUT_DIR / "trajectory_observations" / f"{purpose.name}.csv"
    coverage_path = OUTPUT_DIR / "trajectory_observations" / f"{purpose.name}_coverage.csv"
    mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
    if not mission_path.is_file() or not trajectory_path.is_file() or not coverage_path.is_file():
        return False
    try:
        inputs = {
            "mission_sha256": _sha256(mission_path),
            "trajectory_contract_version": str(TRAJECTORY_CONTRACT_VERSION),
        }
        return (
            is_valid_csv_checkpoint(trajectory_path, stage="trajectory", as_of=_as_of_string(), inputs=inputs)
            and is_valid_csv_checkpoint(coverage_path, stage="trajectory_coverage", as_of=_as_of_string(), inputs=inputs)
        )
    except (FileNotFoundError, OSError):
        return False


def _observe_persisted_mission_outputs(purposes, funds_by_isin, *, max_workers) -> None:
    jobs = []
    for purpose in purposes:
        if purpose.trajectory_horizon_years is None:
            _log(f"  {purpose.name}: no analytical/finite horizon; skipping trajectory")
            _detail(f"TRAJECTORY_SKIPPED purpose={purpose.name} reason=no_trajectory_horizon")
            continue
        if _trajectory_checkpoint_valid(purpose):
            _log(f"  {purpose.name}: valid trajectory checkpoint; reusing")
            _detail(f"TRAJECTORY_REUSED purpose={purpose.name}")
            continue
        if not _mission_checkpoint_valid(purpose):
            _log(f"  {purpose.name}: no valid persisted MISSION checkpoint; skipping")
            _detail(f"TRAJECTORY_SKIPPED purpose={purpose.name} reason=invalid_mission_checkpoint")
            continue
        mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
        df = load_csv_checkpoint(
            mission_path,
            stage="mission",
            as_of=_as_of_string(),
            inputs={"achievability_sha256": _sha256(OUTPUT_DIR / f"achievability_{purpose.name}.csv")},
        )
        identities = df["composition"].tolist()
        jobs.append((purpose, identities))
        _detail(f"TRAJECTORY_JOB_READY purpose={purpose.name} survivors={len(identities)} path={mission_path}")
    if not jobs:
        _log("No persisted MISSION outputs require trajectory observation")
        _detail("TRAJECTORY_STAGE_SKIPPED reason=no_jobs")
        _manifest_update("trajectory", "complete", purposes=0)
        return
    _detail(f"TRAJECTORY_STAGE_START purposes={len(jobs)} workers={max_workers or 'auto'}")
    _manifest_update("trajectory", "running", purposes=len(jobs))
    as_of = _as_of_string()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_observe_one_purpose, purpose, identities, funds_by_isin, as_of): purpose.name
            for purpose, identities in jobs
        }
        _detail(f"TRAJECTORY_WORKERS_READY submitted={len(futures)}")
        for future in as_completed(futures):
            purpose_name = futures[future]
            try:
                count, rows, observed, unavailable = future.result()
                _log(f"  {purpose_name}: trajectory complete survivors={count} observed={observed} insufficient_history={unavailable} rows={rows}")
                _detail(f"TRAJECTORY_WORKER_COMPLETE purpose={purpose_name} survivors={count} observed={observed} insufficient_history={unavailable} rows={rows}")
            except Exception as exc:
                _detail(f"TRAJECTORY_FAILED purpose={purpose_name} error={exc!r}")
                _manifest_update("trajectory", "failed", failed_purpose=purpose_name, error=repr(exc))
                raise
    _log("RESUME DONE")
    _detail("TRAJECTORY_STAGE_COMPLETE")
    _manifest_update("trajectory", "complete", purposes=len(jobs))


def run(
    as_of: str,
    resume_from: str | None = None,
    workers: int | None = None,
    purpose_names: list[str] | None = None,
) -> None:
    global _RUN_MANIFEST
    valuation_date = pd.Timestamp(as_of)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    _RUN_MANIFEST = {
        "run_id": run_id,
        "started_at": _wall_timestamp(),
        "as_of": str(valuation_date.date()),
        "mode": resume_from or "full",
        "workers": workers or "auto",
        "purpose_selection": purpose_names or "all",
        "python": platform.python_version(),
        "pipeline": "resilient_pipeline",
        "stages": {},
    }
    _write_manifest()
    _log(f"START as-of {valuation_date.date()} mode={resume_from or 'full'} workers={workers or 'auto'}")
    _detail(f"RUN_START run_id={run_id} as_of={valuation_date.date()} mode={resume_from or 'full'} workers={workers or 'auto'} log={LOG_PATH} manifest={MANIFEST_PATH}")

    funds = load_admissible_funds()
    histories = _load_fund_histories(funds)
    purposes = _load_purposes(valuation_date)
    if purpose_names is not None:
        requested = set(purpose_names)
        known = {purpose.name for purpose in purposes}
        unknown = requested - known
        if unknown:
            raise ValueError(f"Unknown Purpose(s): {sorted(unknown)}; available={sorted(known)}")
        purposes = [purpose for purpose in purposes if purpose.name in requested]
        _log("Selected purposes: " + ", ".join(purpose.name for purpose in purposes))
        _detail("PURPOSE_SELECTION " + " ".join(purpose.name for purpose in purposes))
    funds_by_isin = {fund.isin: fund for fund in funds}
    _detail(f"INPUTS_READY funds={len(funds)} purposes={len(purposes)}")

    if resume_from == "mission":
        _log("[RESUME MISSION] Loading persisted Purpose checkpoints")
        _detail("RESUME_MISSION_START")
        _observe_persisted_mission_outputs(purposes, funds_by_isin, max_workers=workers)
        _log("RESUME MISSION DONE")
        _detail("RESUME_MISSION_COMPLETE")
        _RUN_MANIFEST["completed_at"] = _wall_timestamp()
        _RUN_MANIFEST["status"] = "complete"
        _write_manifest()
        return

    if resume_from == "global":
        _log("[RESUME GLOBAL] Loading persisted global Composition evidence")
        _detail("RESUME_GLOBAL_START")
        _run_mission_from_global(purposes, funds_by_isin, max_workers=workers, skip_existing=True)
        _observe_persisted_mission_outputs(purposes, funds_by_isin, max_workers=workers)
        _log("RESUME GLOBAL DONE")
        _detail("RESUME_GLOBAL_COMPLETE")
        _RUN_MANIFEST["completed_at"] = _wall_timestamp()
        _RUN_MANIFEST["status"] = "complete"
        _write_manifest()
        return

    _log("[1/7] Loading admitted funds")
    _log(f"  admitted funds: {len(funds)}")
    _detail(f"STAGE_1_COMPLETE admitted_funds={len(funds)}")
    _manifest_update("admitted_funds", "complete", count=len(funds))
    _log("[2/7] Loading persisted NAV evidence")
    _log("[3/7] Loading Purpose inputs")
    _detail(f"STAGE_2_3_COMPLETE nav_funds={len(histories)} purposes={len(purposes)}")
    _manifest_update("inputs", "complete", nav_funds=len(histories), purposes=len(purposes))
    _log("[4/7] Running TEAM pipeline — this may be computationally heavy")
    stage_started = time.perf_counter()
    _detail("TEAM_STAGE_START")
    _manifest_update("team", "running")
    teams = run_team_pipeline(funds=funds, fund_histories=histories)
    team_elapsed = time.perf_counter() - stage_started
    _log(f"  TEAM survivors: {len(teams)} | elapsed={team_elapsed:.1f}s")
    _detail(f"TEAM_STAGE_COMPLETE survivors={len(teams)} elapsed_seconds={team_elapsed:.3f}")
    _manifest_update("team", "complete", survivors=len(teams), elapsed_seconds=round(team_elapsed, 3))
    _write_rows(OUTPUT_DIR / "team_survivors.csv", [{"team": "|".join(member.isin for member in team.members), "members": len(team.members)} for team in teams])

    _log("[5/7] Generating and persisting Composition fingerprints")
    expected_total = _write_composition_candidates(teams)
    _persist_composition_evidence(teams, histories, max_workers=workers)

    _log("[6/7] Applying existing MISSION gates")
    stage_started = time.perf_counter()
    global_inputs = _global_inputs()
    global_path = OUTPUT_DIR / "global_survivors.csv"
    if is_valid_csv_checkpoint(global_path, stage="global_frontier", as_of=_as_of_string(), inputs=global_inputs):
        global_df = load_csv_checkpoint(global_path, stage="global_frontier", as_of=_as_of_string(), inputs=global_inputs)
        global_survivors = [_composition_from_identity(identity, funds_by_isin) for identity in global_df["composition"].tolist()]
        _log(f"  global Composition frontier: {len(global_survivors)} | valid checkpoint reused")
        _detail(f"GLOBAL_FRONTIER_REUSED survivors={len(global_survivors)}")
        _manifest_update("global_frontier", "complete", candidates=expected_total, survivors=len(global_survivors), reused=True)
    else:
        _detail("GLOBAL_FRONTIER_STAGE_START")
        _manifest_update("global_frontier", "running", candidates=expected_total)
        global_survivors = global_composition_frontier(_load_global_pairs_for_frontier(teams))
        global_elapsed = time.perf_counter() - stage_started
        _write_rows(
            global_path,
            [{"composition": composition_identity(composition)} for composition in global_survivors],
            stage="global_frontier",
            inputs=global_inputs,
        )
        _log(f"  global Composition frontier: {len(global_survivors)} | elapsed={global_elapsed:.1f}s")
        _detail(f"GLOBAL_FRONTIER_STAGE_COMPLETE survivors={len(global_survivors)} elapsed_seconds={global_elapsed:.3f}")
        _manifest_update("global_frontier", "complete", candidates=expected_total, survivors=len(global_survivors), elapsed_seconds=round(global_elapsed, 3), reused=False)

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
    _RUN_MANIFEST["completed_at"] = _wall_timestamp()
    _RUN_MANIFEST["status"] = "complete"
    _write_manifest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="Purpose valuation date, e.g. 2026-08-31")
    parser.add_argument("--resume-from", choices=("mission", "global"), help="Resume from persisted MISSION or global checkpoints without recomputing fingerprints")
    parser.add_argument("--workers", type=int, default=None, help="Optional ProcessPoolExecutor worker count; default delegates to Python")
    parser.add_argument("--purposes", nargs="+", help="Run only the named Purposes; default runs all")
    args = parser.parse_args()
    run(args.as_of, args.resume_from, args.workers, args.purposes)


if __name__ == "__main__":
    main()
