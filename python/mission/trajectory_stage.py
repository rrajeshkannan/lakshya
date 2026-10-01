"""Trajectory-stage checkpoint helpers extracted from resilient_pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from lfs.layout import mission_survivors_path, trajectory_observations_dir


@dataclass(frozen=True)
class TrajectoryCheckpointDeps:
    output_dir: Path
    as_of_string: Callable[[], str]
    sha256: Callable[[Path], str]
    is_valid_csv_checkpoint: Callable[..., bool]
    trajectory_contract_version: object


class TrajectoryStage:
    """Own validation of persisted trajectory checkpoints.

    The trajectory worker and orchestration loop remain in the runner so the
    existing ProcessPoolExecutor and monkeypatch seams remain unchanged.
    """

    def __init__(self, deps: TrajectoryCheckpointDeps):
        self.deps = deps

    def checkpoint_valid(self, purpose) -> bool:
        output_dir = self.deps.output_dir
        trajectory_path = trajectory_observations_dir(output_dir) / f"{purpose.name}.csv"
        mission_path = mission_survivors_path(output_dir, purpose.name)
        if not mission_path.is_file() or not trajectory_path.is_file():
            return False
        try:
            return self.deps.is_valid_csv_checkpoint(
                trajectory_path,
                stage="trajectory",
                as_of=self.deps.as_of_string(),
                inputs={
                    "mission_sha256": self.deps.sha256(mission_path),
                    "trajectory_contract_version": str(self.deps.trajectory_contract_version),
                },
            )
        except (FileNotFoundError, OSError):
            return False
