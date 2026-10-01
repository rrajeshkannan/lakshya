"""Canonical locations under the Lakshya output root."""

from __future__ import annotations

from pathlib import Path


def stages_dir(output_root: Path) -> Path:
    return output_root / "stages"


def goals_dir(output_root: Path, purpose: str) -> Path:
    return output_root / "goals" / purpose


def audits_dir(output_root: Path) -> Path:
    return output_root / "audits"


def runtime_dir(output_root: Path) -> Path:
    return output_root / ".runtime"


def team_survivors_path(output_root: Path) -> Path:
    return stages_dir(output_root) / "team_survivors.csv"


def global_survivors_path(output_root: Path) -> Path:
    return stages_dir(output_root) / "global_survivors.csv"


def composition_candidates_path(output_root: Path) -> Path:
    return stages_dir(output_root) / "composition_candidates.csv"


def pipeline_summary_path(output_root: Path) -> Path:
    return stages_dir(output_root) / "pipeline_summary.csv"


def mission_survivors_path(output_root: Path, purpose: str) -> Path:
    return stages_dir(output_root) / f"mission_survivors_{purpose}.csv"


def trajectory_observations_dir(output_root: Path) -> Path:
    return stages_dir(output_root) / "trajectory_observations"


def achievability_path(output_root: Path, purpose: str) -> Path:
    return goals_dir(output_root, purpose) / f"achievability_{purpose}.csv"


def final_summary_path(output_root: Path, purpose: str) -> Path:
    return goals_dir(output_root, purpose) / f"final_{purpose}_summary.csv"


def final_evidence_prefix(output_root: Path, purpose: str) -> Path:
    return goals_dir(output_root, purpose) / f"final_{purpose}"


def positions_as_of_path(output_root: Path, as_of: str) -> Path:
    return audits_dir(output_root) / f"positions_as_of_{as_of}.csv"


def fund_frontier_audit_path(output_root: Path, as_of: str) -> Path:
    return audits_dir(output_root) / f"fund_frontier_audit_{as_of}.csv"


def pipeline_log_path(output_root: Path) -> Path:
    return runtime_dir(output_root) / "trajectory_pipeline.log"


def purpose_intent_path(data_dir: Path) -> Path:
    """Return the reviewer goal file.

    The canonical file is ``data/lfs/purpose.csv``. A data directory that still
    has only ``data/purpose/purposes.csv`` keeps working until that file is moved.
    """
    canonical = data_dir / "lfs" / "purpose.csv"
    legacy = data_dir / "purpose" / "purposes.csv"
    if canonical.is_file() or not legacy.is_file():
        return canonical
    return legacy


def lfs_manifest_path(data_dir: Path) -> Path:
    """LFS optimization metadata. Distinct from the LTS and LPS manifests."""
    return data_dir / "lfs" / "manifest.json"


def final_checkpoint_path(output_root: Path, purpose: str) -> Path:
    return runtime_dir(output_root) / f"final_{purpose}_checkpoint.json"
