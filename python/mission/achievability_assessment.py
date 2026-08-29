"""Purpose-relative achievability interpretation for MISSION.

This module deliberately separates a Purpose's required return from the
historical Team evidence used to interpret that requirement.

The result is qualitative. Historical evidence is not treated as a forecast.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .achievability import required_annual_return
from .models import Purpose


class AchievabilityStatus(str, Enum):
    """Qualitative MISSION interpretation of a Purpose requirement."""

    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    WITHIN_OBSERVED_TERRAIN = "within_observed_terrain"
    BEYOND_OBSERVED_TERRAIN = "beyond_observed_terrain"


@dataclass(frozen=True)
class AchievabilityAssessment:
    """Purpose-relative interpretation of a Team's historical elevation."""

    status: AchievabilityStatus
    required_annual_return: float | None
    evidence_horizon_years: int | None
    observed_upper_terrain: float | None


def _supported_elevation(purpose_horizon: int, elevation: Any):
    """Return the longest available rolling evidence not exceeding the horizon."""
    for years in (10, 7, 5, 3):
        if years > purpose_horizon:
            continue
        evidence = getattr(elevation, f"rolling_{years}y")
        if evidence is not None:
            return years, evidence
    return None, None


def assess_achievability(purpose: Purpose, team_fingerprint: Any) -> AchievabilityAssessment:
    """Interpret a Purpose requirement against observed Team elevation terrain.

    The Team's maximum observed rolling CAGR on the longest supported horizon
    not exceeding the Purpose horizon is used as the upper observed terrain.
    This is a historical observation, not a forecast or probability estimate.
    """
    required = required_annual_return(purpose)

    if required is None:
        return AchievabilityAssessment(
            status=AchievabilityStatus.NOT_APPLICABLE,
            required_annual_return=None,
            evidence_horizon_years=None,
            observed_upper_terrain=None,
        )

    evidence_horizon, evidence = _supported_elevation(
        purpose.horizon_years, team_fingerprint.elevation
    )
    if evidence is None:
        return AchievabilityAssessment(
            status=AchievabilityStatus.INSUFFICIENT_EVIDENCE,
            required_annual_return=required,
            evidence_horizon_years=None,
            observed_upper_terrain=None,
        )

    upper_terrain = evidence.maximum
    status = (
        AchievabilityStatus.WITHIN_OBSERVED_TERRAIN
        if required <= upper_terrain
        else AchievabilityStatus.BEYOND_OBSERVED_TERRAIN
    )

    return AchievabilityAssessment(
        status=status,
        required_annual_return=required,
        evidence_horizon_years=evidence_horizon,
        observed_upper_terrain=upper_terrain,
    )
