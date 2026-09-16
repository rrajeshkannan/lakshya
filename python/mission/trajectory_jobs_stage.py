"""Preparation of reusable trajectory-observation jobs.

This module owns only the persisted-MISSION inspection and job-preparation
boundary. Worker execution, logging of worker outcomes, manifest transitions,
and ProcessPoolExecutor ownership remain in the resilient runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable, Any


@dataclass(frozen=True)
class TrajectoryJobDeps:
    output_dir: Path
    as_of_string: Callable[[], str]
    sha256: Callable[[Path], str]
    mission_checkpoint_valid: Callable[[Any], bool]
    trajectory_checkpoint_valid: Callable[[Any], bool]
    load_csv_checkpoint: Callable[..., Any]
    log: Callable[[str], None]
    detail: Callable[[str], None]


@dataclass(frozen=True)
class TrajectoryJobPreparation:
    jobs: list[tuple[Any, list[str]]]


class TrajectoryJobStage:
    def __init__(self, deps: TrajectoryJobDeps) -> None:
        self._deps = deps

    def _purpose_inputs_sha256(self, as_of: str) -> str:
        """Reproduce the MISSION Purpose-input provenance contract."""
        snapshot_path = self._deps.output_dir / f"positions_as_of_{as_of}.csv"
        purposes_path = self._deps.output_dir.parent / "data" / "purpose" / "purposes.csv"
        if not snapshot_path.is_file():
            raise FileNotFoundError(f"Historical Position snapshot is missing: {snapshot_path}")
        if not purposes_path.is_file():
            raise FileNotFoundError(f"Purpose inputs are missing: {purposes_path}")
        material = (
            f"purposes:{self._deps.sha256(purposes_path)}\n"
            f"positions_as_of:{self._deps.sha256(snapshot_path)}"
        )
        return sha256(material.encode("utf-8")).hexdigest()

    def prepare_jobs(self, purposes) -> TrajectoryJobPreparation:
        jobs: list[tuple[Any, list[str]]] = []
        for purpose in purposes:
            if purpose.horizon_years is None:
                self._deps.log(f"  {purpose.name}: no finite horizon; skipping trajectory")
                self._deps.detail(
                    f"TRAJECTORY_SKIPPED purpose={purpose.name} reason=no_finite_horizon"
                )
                continue
            if self._deps.trajectory_checkpoint_valid(purpose):
                self._deps.log(f"  {purpose.name}: valid trajectory checkpoint; reusing")
                self._deps.detail(f"TRAJECTORY_REUSED purpose={purpose.name}")
                continue
            mission_path = self._deps.output_dir / f"mission_survivors_{purpose.name}.csv"
            if not self._deps.mission_checkpoint_valid(purpose):
                self._deps.log(
                    f"  {purpose.name}: no valid persisted MISSION checkpoint; skipping"
                )
                self._deps.detail(
                    f"TRAJECTORY_SKIPPED purpose={purpose.name} reason=invalid_mission_checkpoint"
                )
                continue
            as_of = self._deps.as_of_string()
            purpose_inputs = self._purpose_inputs_sha256(as_of)
            df = self._deps.load_csv_checkpoint(
                mission_path,
                stage="mission",
                as_of=as_of,
                inputs={
                    "achievability_sha256": self._deps.sha256(
                        self._deps.output_dir / f"achievability_{purpose.name}.csv"
                    ),
                    "purpose_inputs_sha256": purpose_inputs,
                },
            )
            identities = df["composition"].tolist()
            jobs.append((purpose, identities))
            self._deps.detail(
                f"TRAJECTORY_JOB_READY purpose={purpose.name} "
                f"survivors={len(identities)} path={mission_path}"
            )
        return TrajectoryJobPreparation(jobs=jobs)
