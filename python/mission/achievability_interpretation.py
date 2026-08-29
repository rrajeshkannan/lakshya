"""Purpose-relative interpretation of observed Composition Elevation evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from .achievability import required_annual_return
from .models import Purpose


class AchievabilityStatus(Enum):
    NOT_APPLICABLE = auto()
    INSUFFICIENT_EVIDENCE = auto()
    WITHIN_OBSERVED_TERRAIN = auto()
    BEYOND_OBSERVED_TERRAIN = auto()


@dataclass(frozen=True)
class AchievabilityAssessment:
    """A deliberately qualitative MISSION interpretation.

    The assessment does not forecast returns or score a Composition. It only
    places the Purpose's required return against the highest observed rolling
    return terrain available from the Composition fingerprint.
    """

    status: AchievabilityStatus
    required_annual_return: float | None
    evidence_horizon_years: int | None
    observed_upper_terrain: float | None


def _comparison_horizon(purpose: Purpose) -> int | None:
    """Choose the longest supported observed horizon not beyond the Purpose horizon."""
    if purpose.horizon_years is None:
        return None
    supported = (3, 5, 7, 10)
    eligible = [years for years in supported if years <= purpose.horizon_years]
    return max(eligible) if eligible else None


def _rolling_evidence(elevation: Any, years: int) -> Any:
    return getattr(elevation, f"rolling_{years}y", None)


def assess_achievability(
    purpose: Purpose,
    composition_fingerprint: Any,
) -> AchievabilityAssessment:
    """Interpret a Purpose requirement against observed Composition Elevation.

    The gate is intentionally weak and qualitative:

    * ``NOT_APPLICABLE`` — the Purpose has no complete target/horizon;
    * ``INSUFFICIENT_EVIDENCE`` — no supported rolling horizon is available;
    * ``WITHIN_OBSERVED_TERRAIN`` — the required return does not exceed the
      maximum historically observed return on the comparison horizon;
    * ``BEYOND_OBSERVED_TERRAIN`` — the requirement sits above that observed
      upper terrain.

    This is not a probability, forecast, or promise of future return.
    """
    required_return = required_annual_return(purpose)
    if required_return is None:
        return AchievabilityAssessment(
            status=AchievabilityStatus.NOT_APPLICABLE,
            required_annual_return=None,
            evidence_horizon_years=None,
            observed_upper_terrain=None,
        )

    horizon = _comparison_horizon(purpose)
    if horizon is None:
        return AchievabilityAssessment(
            status=AchievabilityStatus.INSUFFICIENT_EVIDENCE,
            required_annual_return=required_return,
            evidence_horizon_years=None,
            observed_upper_terrain=None,
        )

    evidence = _rolling_evidence(composition_fingerprint.elevation, horizon)
    if evidence is None or evidence.maximum is None:
        return AchievabilityAssessment(
            status=AchievabilityStatus.INSUFFICIENT_EVIDENCE,
            required_annual_return=required_return,
            evidence_horizon_years=horizon,
            observed_upper_terrain=None,
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
        evidence_horizon_years=horizon,
        observed_upper_terrain=observed_upper,
    )
