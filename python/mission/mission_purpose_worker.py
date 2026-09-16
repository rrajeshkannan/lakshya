"""Per-Purpose MISSION worker.

This module contains the existing per-Purpose MISSION computation and
checkpoint persistence logic extracted from ``resilient_pipeline``.
The worker preserves the original return contract:

    (purpose_name, assessed_count, qualified_count, protected_count)
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from pathlib import Path
from typing import Callable, Any

from .achievability_interpretation import AchievabilityStatus


@dataclass(frozen=True)
class MissionPurposeWorkerDeps:
    output_dir: Path
    fingerprint_dir: Path
    composition_from_identity: Callable[[str, Any], Any]
    fingerprint_path: Callable[[Path, Any], Path]
    load_fingerprint_evidence: Callable[[Path, Any], tuple[Any, Any]]
    assess_achievability: Callable[[Any, Any], Any]
    nearest_supported_horizon: Callable[[int], int]
    protection_frontier: Callable[[list[tuple[Any, Any]]], list[Any]]
    composition_identity: Callable[[Any], str]
    sha256_file: Callable[[Path], str]
    purpose_inputs_sha256: Callable[[], str]
    write_rows: Callable[..., int]
    detail: Callable[[str], None]


class MissionPurposeWorker:
    def __init__(self, deps: MissionPurposeWorkerDeps):
        self._deps = deps

    def run(self, purpose, identities, funds_by_isin, as_of: str):
        if purpose.trajectory_horizon_years is None:
            return purpose.name, 0, 0, 0

        qualified: list[tuple[Any, Any]] = []
        assessments: list[dict] = []
        self._deps.detail(
            f"MISSION_PURPOSE_START purpose={purpose.name} "
            f"identities={len(identities)} achievability={purpose.has_achievability}"
        )

        for identity in identities:
            composition = self._deps.composition_from_identity(identity, funds_by_isin)
            elevation, protection = self._deps.load_fingerprint_evidence(
                self._deps.fingerprint_path(self._deps.fingerprint_dir, composition),
                composition,
            )
            evidence = SimpleNamespace(
                composition=composition,
                elevation=elevation,
                protection=protection,
            )
            assessment = self._deps.assess_achievability(purpose, evidence)
            comparison_horizon = (
                assessment.comparison_horizon_years
                if purpose.has_achievability
                else self._deps.nearest_supported_horizon(
                    purpose.trajectory_horizon_years
                )
            )
            assessments.append(
                {
                    "composition": identity,
                    "status": assessment.status.value,
                    "required_annual_return": assessment.required_annual_return,
                    "comparison_horizon_years": comparison_horizon,
                    "observed_upper_return": assessment.observed_upper_return,
                }
            )
            if (
                not purpose.has_achievability
                or assessment.status == AchievabilityStatus.WITHIN_OBSERVED_TERRAIN
            ):
                qualified.append((composition, evidence))

        global_path = self._deps.output_dir / "global_survivors.csv"
        global_inputs = {
            "global_survivors_sha256": self._deps.sha256_file(global_path),
            "global_checkpoint_stage": "global_frontier",
            "purpose_inputs_sha256": self._deps.purpose_inputs_sha256(),
        }
        achievability_path = (
            self._deps.output_dir / f"achievability_{purpose.name}.csv"
        )
        self._deps.write_rows(
            achievability_path,
            assessments,
            stage="mission_achievability",
            inputs=global_inputs,
            as_of=as_of,
        )

        protected = self._deps.protection_frontier(qualified)
        mission_path = (
            self._deps.output_dir / f"mission_survivors_{purpose.name}.csv"
        )
        self._deps.write_rows(
            mission_path,
            [
                {"composition": self._deps.composition_identity(composition)}
                for composition in protected
            ],
            stage="mission",
            inputs={
                "achievability_sha256": self._deps.sha256_file(achievability_path),
                "purpose_inputs_sha256": self._deps.purpose_inputs_sha256(),
            },
            as_of=as_of,
        )
        self._deps.detail(
            f"MISSION_PURPOSE_COMPLETE purpose={purpose.name} "
            f"assessed={len(identities)} "
            f"achievability={len(qualified) if purpose.has_achievability else 'not_applicable'} "
            f"protection={len(protected)}"
        )
        return purpose.name, len(identities), len(qualified), len(protected)
