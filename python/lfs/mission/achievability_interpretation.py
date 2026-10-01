"""Purpose-relative interpretation of observed Composition Elevation evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .achievability import required_annual_return
from .models import Purpose
from .observation_horizon import nearest_supported_horizon


class AchievabilityStatus(str, Enum):
    """Qualitative MISSION interpretation of a Purpose requirement."""

    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    WITHIN_OBSERVED_TERRAIN = "within_observed_terrain"
    BEYOND_OBSERVED_TERRAIN = "beyond_observed_terrain"


@dataclass(frozen=True)
class AchievabilityAssessment:
    """A deliberately qualitative MISSION interpretation."""

    status: AchievabilityStatus
    required_annual_return: float | None
    comparison_horizon_years: int | None
    observed_upper_return: float | None


def _comparison_horizon(purpose: Purpose) -> int | None:
    """Choose the canonical analytical horizon not beyond the Purpose horizon."""
    if purpose.horizon_years is None:
        return None
    return nearest_supported_horizon(purpose.horizon_years)


def _rolling_evidence(elevation: Any, years: int) -> Any:
    return getattr(elevation, f"rolling_{years}y", None)


def assess_achievability(
    purpose: Purpose,
    composition_fingerprint: Any,
    required_return: float | None = None,
) -> AchievabilityAssessment:
    """Interpret a Purpose requirement against observed Composition Elevation."""
    if required_return is None:
        required_return = required_annual_return(purpose)

    if required_return is None:
        return AchievabilityAssessment(
            status=AchievabilityStatus.NOT_APPLICABLE,
            required_annual_return=None,
            comparison_horizon_years=None,
            observed_upper_return=None,
        )

    horizon = _comparison_horizon(purpose)
    if horizon is None:
        return AchievabilityAssessment(
            status=AchievabilityStatus.INSUFFICIENT_EVIDENCE,
            required_annual_return=required_return,
            comparison_horizon_years=None,
            observed_upper_return=None,
        )

    evidence = _rolling_evidence(composition_fingerprint.elevation, horizon)
    if evidence is None or evidence.maximum is None:
        return AchievabilityAssessment(
            status=AchievabilityStatus.INSUFFICIENT_EVIDENCE,
            required_annual_return=required_return,
            comparison_horizon_years=horizon,
            observed_upper_return=None,
        )

    observed_upper = evidence.maximum
    status = (
        AchievabilityStatus.WITHIN_OBSERVED_TERRAIN
        if required_return <= observed_upper
        else AchievabilityStatus.BEYOND_OBSERVED_TERRAIN
    )

    return AchievabilityAssessment(
        status=status,
        required_annual_return=required_return,
        comparison_horizon_years=horizon,
        observed_upper_return=observed_upper,
    )
