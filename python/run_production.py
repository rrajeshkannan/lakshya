"""Production Lakshya runner: MISSION followed by FINAL."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import pandas as pd

from final.compromise_programming import (
    DEFAULT_BOOTSTRAP_RESAMPLES,
    DEFAULT_BOOTSTRAP_SEED,
    FINAL_CONTRACT_VERSION,
    analyze_purpose,
    write_analysis,
)
from mission.resilient_pipeline import _load_purposes, run as run_mission

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint_path(purpose_name: str) -> Path:
    return OUTPUT_DIR / f"final_{purpose_name}_checkpoint.json"


def _write_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _final_checkpoint_valid(
    purpose_name: str,
    mission_path: Path,
    *,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> bool:
    checkpoint = _checkpoint_path(purpose_name)
    summary = OUTPUT_DIR / f"final_{purpose_name}_summary.csv"
    if not checkpoint.is_file() or not summary.is_file():
        return False
    try:
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        return (
            payload.get("contract_version") == FINAL_CONTRACT_VERSION
            and payload.get("purpose") == purpose_name
            and payload.get("mission_sha256") == _sha256(mission_path)
            and payload.get("bootstrap_resamples") == bootstrap_resamples
            and payload.get("bootstrap_seed") == bootstrap_seed
        )
    except (OSError, ValueError, TypeError):
        return False


def run_final_stage(
    as_of: str,
    purpose_names: list[str] | None = None,
    *,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    reuse_valid: bool = True,
) -> None:
    """Consume persisted MISSION survivors and execute/reuse FINAL outputs."""
    purposes = _load_purposes(pd.Timestamp(as_of))
    if purpose_names is not None:
        requested = set(purpose_names)
        unknown = requested - {purpose.name for purpose in purposes}
        if unknown:
            raise ValueError(f"Unknown Purpose(s): {sorted(unknown)}")
        purposes = [purpose for purpose in purposes if purpose.name in requested]

    for purpose in purposes:
        if purpose.trajectory_horizon_years is None:
            raise ValueError(f"Purpose has no analytical horizon: {purpose.name}")
        mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
        if not mission_path.is_file():
            raise FileNotFoundError(
                f"Required MISSION checkpoint is missing for {purpose.name}: {mission_path}"
            )
        if reuse_valid and _final_checkpoint_valid(
            purpose.name,
            mission_path,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        ):
            print(f"FINAL {purpose.name}: valid checkpoint reused")
            continue

        identities = pd.read_csv(mission_path)["composition"].astype(str).tolist()
        if not identities:
            raise ValueError(f"MISSION checkpoint is empty for {purpose.name}")

        analysis = analyze_purpose(
            purpose.name,
            identities,
            purpose.trajectory_horizon_years,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
        paths = write_analysis(analysis, OUTPUT_DIR)
        _write_checkpoint(
            _checkpoint_path(purpose.name),
            {
                "contract_version": FINAL_CONTRACT_VERSION,
                "purpose": purpose.name,
                "purpose_horizon_years": purpose.trajectory_horizon_years,
                "mission_sha256": _sha256(mission_path),
                "bootstrap_resamples": bootstrap_resamples,
                "bootstrap_seed": bootstrap_seed,
                "informative_spoke_count": len(analysis.axes),
                "primary_winner": analysis.results.iloc[0]["composition"],
            },
        )
        print(
            f"FINAL {purpose.name}: winner={analysis.results.iloc[0]['composition']} "
            f"spokes={len(analysis.axes)} bootstrap={bootstrap_resamples}"
        )
        for path in paths.values():
            print(path.relative_to(PROJECT_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True)
    parser.add_argument(
        "--resume-from",
        choices=("mission", "global"),
        help="Resume the upstream resilient pipeline from its persisted checkpoints.",
    )
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--purposes", nargs="+")
    parser.add_argument("--bootstrap-resamples", type=int, default=DEFAULT_BOOTSTRAP_RESAMPLES)
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    parser.add_argument(
        "--no-final-reuse",
        action="store_true",
        help="Force FINAL recomputation even when its checkpoint is valid.",
    )
    args = parser.parse_args()

    run_mission(
        args.as_of,
        resume_from=args.resume_from,
        workers=args.workers,
        purpose_names=args.purposes,
    )
    run_final_stage(
        args.as_of,
        args.purposes,
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
        reuse_valid=not args.no_final_reuse,
    )


if __name__ == "__main__":
    main()
