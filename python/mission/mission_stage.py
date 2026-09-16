"""MISSION-stage helpers extracted from resilient_pipeline.

This module deliberately contains only orchestration-independent helpers.
The process-pool worker remains in resilient_pipeline because it relies on
module-level runner state and must remain safely pickleable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class MissionCheckpointDeps:
    output_dir: Path
    as_of_string: Callable[[], str]
    sha256: Callable[[Path], str]
    purpose_inputs_sha256: Callable[[str], str]
    is_valid_csv_checkpoint: Callable[..., bool]


class MissionStage:
    """Own MISSION checkpoint validation and job selection.

    The expensive per-Purpose worker remains a top-level function in the
    runner so ProcessPoolExecutor serialization behavior is unchanged.
    """

    def __init__(self, deps: MissionCheckpointDeps):
        self.deps = deps

    def checkpoint_valid(self, purpose) -> bool:
        output_dir = self.deps.output_dir
        mission_path = output_dir / f"mission_survivors_{purpose.name}.csv"
        achievability_path = output_dir / f"achievability_{purpose.name}.csv"
        if not mission_path.is_file() or not achievability_path.is_file():
            return False
        try:
            as_of = self.deps.as_of_string()
            purpose_inputs = self.deps.purpose_inputs_sha256(as_of)
            achievability_valid = self.deps.is_valid_csv_checkpoint(
                achievability_path,
                stage="mission_achievability",
                as_of=as_of,
                inputs={
                    "global_survivors_sha256": self.deps.sha256(output_dir / "global_survivors.csv"),
                    "global_checkpoint_stage": "global_frontier",
                    "purpose_inputs_sha256": purpose_inputs,
                },
            )
            if not achievability_valid:
                return False
            return self.deps.is_valid_csv_checkpoint(
                mission_path,
                stage="mission",
                as_of=as_of,
                inputs={
                    "achievability_sha256": self.deps.sha256(achievability_path),
                    "purpose_inputs_sha256": purpose_inputs,
                },
            )
        except (FileNotFoundError, OSError):
            return False

    def runnable_purposes(
        self,
        purposes: Iterable,
        *,
        skip_existing: bool,
        checkpoint_valid: Callable[[object], bool] | None = None,
    ) -> list:
        # Keep the runner-level checkpoint predicate injectable.  This preserves
        # the historical test/compatibility seam while the stage owns the
        # default implementation.
        is_valid = checkpoint_valid or self.checkpoint_valid
        return [
            purpose
            for purpose in purposes
            if purpose.horizon_years is not None
            and not (skip_existing and is_valid(purpose))
        ]
