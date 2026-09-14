"""Resilient execution engine for the surviving-Composition experiment.

Core invariant:

    compute -> persist -> validate -> consume

Expensive Composition fingerprints are durable evidence. Downstream stages
load that evidence rather than reconstructing it. Stage CSVs are reusable only
when their atomic completion marker, content hash, as-of date, and input
provenance all validate.
"""

from __future__ import annotations

from lakshya_core.hashing import sha256_file

_sha256 = sha256_file

import argparse
import csv
import json
import platform
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from fund_analysis.admissible_funds import load_admissible_funds
from .pipeline_inputs import load_fund_histories
from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition_fingerprint_store import (
    FINGERPRINT_SCHEMA_VERSION,
    evidence_path,
    fingerprint_path,
    has_fingerprint,
    load_fingerprint,
    load_fingerprint_evidence,
    materialize_fingerprint_evidence,
    persist_fingerprint,
)
from team_analysis.composition_frontier import global_composition_frontier
from team_analysis.composition_pipeline import analyze_compositions_parallel_resilient
from team_analysis.generate_compositions import generate_compositions
from team_analysis.protection_frontier import protection_frontier
from team_analysis.run_team_pipeline import run_team_pipeline
from team_analysis.team import Team

from .achievability_interpretation import AchievabilityStatus, assess_achievability
from .composition_checkpoint_index import (
    checkpoint_metadata,
    load_checkpoint_index,
    publish_checkpoint_index,
)
from .durable_stage_output import (
    is_valid_csv_checkpoint,
    load_csv_checkpoint,
    write_csv_checkpoint,
)
from .models import Purpose
from .purpose_loader import load_purposes
from .observation_horizon import nearest_supported_horizon
from .trajectory_stage import TrajectoryCheckpointDeps, TrajectoryStage
from .trajectory_jobs_stage import TrajectoryJobDeps, TrajectoryJobPreparation, TrajectoryJobStage
from .full_run_stage import FullRunStage, FullRunStageDeps
from .resume_stage import ResumeStage, ResumeStageDeps
from .survivor_trajectory_experiment import (
    TRAJECTORY_CONTRACT_VERSION,
    observe_survivors_for_purpose,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
NAV_DIR = DATA_DIR / "lps" / "nav"
PURPOSES_PATH = DATA_DIR / "purpose" / "purposes.csv"
FINGERPRINT_DIR = DATA_DIR / "fingerprints" / "composition"
CHECKPOINT_INDEX_PATH = FINGERPRINT_DIR / ".checkpoint_index.json"
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


def _input_hash(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Required checkpoint input is missing: {path}")
    return sha256_file(path)


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


from .composition_evidence_stage import CompositionEvidenceDeps, CompositionEvidenceStage
from .global_composition_stage import GlobalCompositionDeps, GlobalCompositionStage
from .mission_stage import MissionCheckpointDeps, MissionStage
from .mission_execution_stage import MissionExecutionDeps, MissionExecutionStage
from .mission_purpose_worker import MissionPurposeWorker, MissionPurposeWorkerDeps
from .trajectory_purpose_worker import TrajectoryPurposeWorker, TrajectoryPurposeWorkerDeps


def _composition_evidence_stage() -> CompositionEvidenceStage:
    return CompositionEvidenceStage(CompositionEvidenceDeps(
        output_dir=OUTPUT_DIR, project_root=PROJECT_ROOT, fingerprint_dir=FINGERPRINT_DIR,
        checkpoint_index_path=CHECKPOINT_INDEX_PATH, input_hash=_input_hash,
        load_checkpoint_index=load_checkpoint_index, publish_checkpoint_index=publish_checkpoint_index,
        checkpoint_metadata=checkpoint_metadata, has_fingerprint=has_fingerprint,
        fingerprint_path=fingerprint_path, composition_identity=composition_identity,
        generate_compositions=generate_compositions,
        analyze_compositions_parallel_resilient=analyze_compositions_parallel_resilient,
        persist_fingerprint=persist_fingerprint, log=_log, detail=_detail,
        manifest_update=_manifest_update,
    ))

def _write_composition_candidates(teams) -> int:
    return _composition_evidence_stage().write_candidates(teams)

def _candidate_compositions(teams):
    yield from _composition_evidence_stage().candidate_compositions(teams)

def _scan_composition_checkpoints(teams):
    return _composition_evidence_stage().scan_checkpoints(teams)

def _persist_composition_evidence(teams, fund_histories, *, max_workers: int | None) -> int:
    return _composition_evidence_stage().persist_evidence(teams, fund_histories, max_workers=max_workers)


def _global_composition_stage() -> GlobalCompositionStage:
    return GlobalCompositionStage(GlobalCompositionDeps(
        output_dir=OUTPUT_DIR,
        project_root=PROJECT_ROOT,
        fingerprint_dir=FINGERPRINT_DIR,
        candidates_path=OUTPUT_DIR / "composition_candidates.csv",
        global_survivors_path=OUTPUT_DIR / "global_survivors.csv",
        fingerprint_schema_version=FINGERPRINT_SCHEMA_VERSION,
        input_hash=_input_hash,
        candidate_compositions=_candidate_compositions,
        fingerprint_path=fingerprint_path,
        composition_identity=composition_identity,
        load_fingerprint=load_fingerprint,
        global_composition_frontier=global_composition_frontier,
        load_csv_checkpoint=load_csv_checkpoint,
        detail=_detail,
        as_of_string=_as_of_string,
    ))

def _load_global_pairs_for_frontier(teams):
    yield from _global_composition_stage().load_pairs_for_frontier(teams)

def _global_inputs() -> dict[str, str]:
    return _global_composition_stage().inputs()

def _load_global_identities() -> list[str]:
    return _global_composition_stage().load_identities()


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


def _materialize_missing_mission_evidence(identities: list[str], funds_by_isin) -> int:
    """Create missing compact MISSION evidence before parallel Purpose work."""
    missing = 0
    for identity in identities:
        composition = _composition_from_identity(identity, funds_by_isin)
        sidecar = evidence_path(FINGERPRINT_DIR, composition)
        if sidecar.is_file():
            continue
        materialize_fingerprint_evidence(
            fingerprint_path(FINGERPRINT_DIR, composition),
            composition,
        )
        missing += 1
    if missing:
        _detail(f"MISSION_EVIDENCE_MATERIALIZED missing={missing}")
    return missing


def _mission_purpose_worker() -> MissionPurposeWorker:
    return MissionPurposeWorker(
        MissionPurposeWorkerDeps(
            output_dir=OUTPUT_DIR,
            fingerprint_dir=FINGERPRINT_DIR,
            composition_from_identity=_composition_from_identity,
            fingerprint_path=fingerprint_path,
            load_fingerprint_evidence=load_fingerprint_evidence,
            assess_achievability=assess_achievability,
            nearest_supported_horizon=nearest_supported_horizon,
            protection_frontier=protection_frontier,
            composition_identity=composition_identity,
            sha256_file=sha256_file,
            write_rows=_write_rows,
            detail=_detail,
        )
    )


def _run_one_purpose(purpose: Purpose, identities: list[str], funds_by_isin, as_of: str):
    return _mission_purpose_worker().run(purpose, identities, funds_by_isin, as_of)


def _mission_stage() -> MissionStage:
    return MissionStage(MissionCheckpointDeps(
        output_dir=OUTPUT_DIR,
        as_of_string=_as_of_string,
        sha256=_sha256,
        is_valid_csv_checkpoint=is_valid_csv_checkpoint,
    ))


def _mission_checkpoint_valid(purpose: Purpose) -> bool:
    return _mission_stage().checkpoint_valid(purpose)


def _mission_execution_stage() -> MissionExecutionStage:
    return MissionExecutionStage(
        MissionExecutionDeps(
            load_global_identities=_load_global_identities,
            runnable_purposes=_mission_stage().runnable_purposes,
            checkpoint_valid=_mission_checkpoint_valid,
            as_of_string=_as_of_string,
            worker=_run_one_purpose,
            executor_cls=ProcessPoolExecutor,
            as_completed=as_completed,
            log=_log,
            detail=_detail,
            manifest_update=_manifest_update,
        )
    )


def _run_mission_from_global(purposes, funds_by_isin, *, max_workers, skip_existing) -> None:
    _mission_execution_stage().run(
        purposes,
        funds_by_isin,
        max_workers=max_workers,
        skip_existing=skip_existing,
    )


def _trajectory_purpose_worker() -> TrajectoryPurposeWorker:
    return TrajectoryPurposeWorker(
        TrajectoryPurposeWorkerDeps(
            output_dir=OUTPUT_DIR,
            fingerprint_dir=FINGERPRINT_DIR,
            composition_from_identity=_composition_from_identity,
            fingerprint_path=fingerprint_path,
            load_fingerprint=load_fingerprint,
            observe_survivors_for_purpose=observe_survivors_for_purpose,
            composition_identity=composition_identity,
            sha256=_sha256,
            trajectory_contract_version=TRAJECTORY_CONTRACT_VERSION,
            write_rows=_write_rows,
            detail=_detail,
        )
    )


def _observe_one_purpose(purpose: Purpose, identities: list[str], funds_by_isin, as_of: str):
    return _trajectory_purpose_worker().run(purpose, identities, funds_by_isin, as_of)


def _trajectory_stage() -> TrajectoryStage:
    return TrajectoryStage(TrajectoryCheckpointDeps(
        output_dir=OUTPUT_DIR,
        as_of_string=_as_of_string,
        sha256=_sha256,
        is_valid_csv_checkpoint=is_valid_csv_checkpoint,
        trajectory_contract_version=TRAJECTORY_CONTRACT_VERSION,
    ))


def _trajectory_checkpoint_valid(purpose: Purpose) -> bool:
    return _trajectory_stage().checkpoint_valid(purpose)


def _trajectory_job_stage() -> TrajectoryJobStage:
    return TrajectoryJobStage(TrajectoryJobDeps(
        output_dir=OUTPUT_DIR,
        as_of_string=_as_of_string,
        sha256=_sha256,
        mission_checkpoint_valid=_mission_checkpoint_valid,
        trajectory_checkpoint_valid=_trajectory_checkpoint_valid,
        load_csv_checkpoint=load_csv_checkpoint,
        log=_log,
        detail=_detail,
    ))


def _observe_persisted_mission_outputs(purposes, funds_by_isin, *, max_workers) -> None:
    preparation = _trajectory_job_stage().prepare_jobs(purposes)
    jobs = preparation.jobs
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
                count, rows = future.result()
                _log(f"  {purpose_name}: trajectory complete survivors={count} rows={rows}")
                _detail(f"TRAJECTORY_WORKER_COMPLETE purpose={purpose_name} survivors={count} rows={rows}")
            except Exception as exc:
                _detail(f"TRAJECTORY_FAILED purpose={purpose_name} error={exc!r}")
                _manifest_update("trajectory", "failed", failed_purpose=purpose_name, error=repr(exc))
                raise
    _log("RESUME DONE")
    _detail("TRAJECTORY_STAGE_COMPLETE")
    _manifest_update("trajectory", "complete", purposes=len(jobs))



def _manifest() -> dict:
    return _RUN_MANIFEST if _RUN_MANIFEST is not None else {}


def _resume_stage() -> ResumeStage:
    return ResumeStage(
        ResumeStageDeps(
            log=_log,
            detail=_detail,
            run_mission_resume=lambda purposes, funds_by_isin, workers: _run_mission_from_global(
                purposes, funds_by_isin, max_workers=workers, skip_existing=True
            ),
            observe_trajectories=lambda purposes, funds_by_isin, workers: _observe_persisted_mission_outputs(
                purposes, funds_by_isin, max_workers=workers
            ),
            get_manifest=_manifest,
            wall_timestamp=_wall_timestamp,
            write_manifest=_write_manifest,
        )
    )


def _full_run_stage() -> FullRunStage:
    return FullRunStage(
        FullRunStageDeps(
            output_dir=OUTPUT_DIR,
            log=_log,
            detail=_detail,
            manifest_update=_manifest_update,
            write_rows=_write_rows,
            write_manifest=_write_manifest,
            as_of_string=_as_of_string,
            global_inputs=_global_inputs,
            load_global_pairs_for_frontier=_load_global_pairs_for_frontier,
            persist_composition_evidence=_persist_composition_evidence,
            write_composition_candidates=_write_composition_candidates,
            run_team_pipeline=run_team_pipeline,
            global_composition_frontier=global_composition_frontier,
            load_csv_checkpoint=load_csv_checkpoint,
            is_valid_csv_checkpoint=is_valid_csv_checkpoint,
            composition_from_identity=_composition_from_identity,
            composition_identity=composition_identity,
            run_mission_from_global=_run_mission_from_global,
            observe_persisted_mission_outputs=_observe_persisted_mission_outputs,
            get_manifest=_manifest,
            wall_timestamp=_wall_timestamp,
        )
    )


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
    histories = load_fund_histories(
        funds,
        nav_dir=NAV_DIR,
        as_of=valuation_date,
        log=_log,
        detail=_detail,
    )
    purposes = load_purposes(valuation_date.date())
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

    if resume_from is not None:
        if _resume_stage().run(
            resume_from=resume_from,
            purposes=purposes,
            funds_by_isin=funds_by_isin,
            workers=workers,
        ):
            return

    _full_run_stage().run(
        funds=funds,
        histories=histories,
        purposes=purposes,
        funds_by_isin=funds_by_isin,
        workers=workers,
    )
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
