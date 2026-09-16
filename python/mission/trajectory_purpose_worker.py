"""Per-Purpose trajectory observation worker.

This module owns only the work performed for one Purpose inside a worker
process. Parent-process job preparation, process-pool orchestration, manifest
updates, and checkpoint eligibility remain in the runner/stage boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition_fingerprint_store import fingerprint_path, load_fingerprint
from .models import Purpose
from .survivor_trajectory_experiment import (
    TRAJECTORY_CONTRACT_VERSION,
    observe_survivors_for_purpose,
)


@dataclass(frozen=True)
class TrajectoryPurposeWorkerDeps:
    output_dir: Path
    fingerprint_dir: Path
    composition_from_identity: Callable
    fingerprint_path: Callable
    load_fingerprint: Callable
    observe_survivors_for_purpose: Callable
    composition_identity: Callable
    sha256: Callable
    trajectory_contract_version: str
    write_rows: Callable
    detail: Callable


class TrajectoryPurposeWorker:
    def __init__(self, deps: TrajectoryPurposeWorkerDeps):
        self.deps = deps

    def run(
        self,
        purpose: Purpose,
        identities: list[str],
        funds_by_isin,
        as_of: str,
    ) -> tuple[int, int]:
        pairs: list[tuple[Composition, CompositionFingerprint]] = []
        self.deps.detail(
            f"TRAJECTORY_PURPOSE_START purpose={purpose.name} survivors={len(identities)}"
        )

        for identity in identities:
            composition = self.deps.composition_from_identity(identity, funds_by_isin)
            fingerprint = self.deps.load_fingerprint(
                self.deps.fingerprint_path(self.deps.fingerprint_dir, composition),
                composition,
            )
            pairs.append((composition, fingerprint))

        observations = self.deps.observe_survivors_for_purpose(
            pairs, purpose.trajectory_horizon_years
        )
        rows: list[dict] = []

        for composition, _ in pairs:
            observation = observations.get(self.deps.composition_identity(composition))
            if observation is None:
                continue
            for point in observation.points:
                rows.append(
                    {
                        "composition": self.deps.composition_identity(composition),
                        "horizon_years": observation.horizon_years,
                        "date": point.date.strftime("%Y-%m-%d"),
                        "elapsed_days": point.elapsed_days,
                        "nav": point.nav,
                        "normalized_nav": point.normalized_nav,
                    }
                )

        mission_path = self.deps.output_dir / f"mission_survivors_{purpose.name}.csv"
        trajectory_path = (
            self.deps.output_dir
            / "trajectory_observations"
            / f"{purpose.name}.csv"
        )
        self.deps.write_rows(
            trajectory_path,
            rows,
            stage="trajectory",
            inputs={
                "mission_sha256": self.deps.sha256(mission_path),
                "trajectory_contract_version": str(
                    self.deps.trajectory_contract_version
                ),
            },
            as_of=as_of,
        )
        self.deps.detail(
            f"TRAJECTORY_PURPOSE_COMPLETE purpose={purpose.name} "
            f"survivors={len(pairs)} rows={len(rows)}"
        )
        return len(pairs), len(rows)
