"""Purpose-relative interpretation of observed TEAM Elevation evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Purpose


@dataclass(frozen=True)
class AchievabilityAssessment:
    """A deliberately qualitative MISSION interpretation.

    The assessment does not forecast returns or score a Team. It only places
    the Purpose's required return against the highest observed rolling-return
    terrain available from the Team fingerprint.
    """

    status: str
    required_annual_return: float | None
    comparison_horizon_years: int | None
    observed_upper_return: float | None


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
    team_fingerprint: Any,
    required_return: float | None,
) -> AchievabilityAssessment:
    """Interpret a Purpose requirement against a Team's observed Elevation.

    The gate is intentionally weak and qualitative:

    * ``not_applicable`` — the Purpose has no complete target/horizon;
    * ``insufficient_evidence`` — no supported rolling horizon is available;
    * ``within_observed_terrain`` — the required return does not exceed the
      maximum historically observed return on the comparison horizon;
    * ``beyond_observed_terrain`` — the requirement sits above that observed
      upper terrain.

    This is not a probability, forecast, or promise of future return.
    """
    if required_return is None:
        return AchievabilityAssessment(
            status="not_applicable",
            required_annual_return=None,
            comparison_horizon_years=None,
            observed_upper_return=None,
        )

    horizon = _comparison_horizon(purpose)
    if horizon is None:
        return AchievabilityAssessment(
            status="insufficient_evidence",
            required_annual_return=required_return,
            comparison_horizon_years=None,
            observed_upper_return=None,
        )

    evidence = _rolling_evidence(team_fingerprint.elevation, horizon)
    if evidence is None or evidence.maximum is None:
        return AchievabilityAssessment(
            status="insufficient_evidence",
            required_annual_return=required_return,
            comparison_horizon_years=horizon,
            observed_upper_return=None,
        )

    observed_upper = evidence.maximum
    status = (
        "within_observed_terrain"
        if required_return <= observed_upper
        else "beyond_observed_terrain"
    )

    return AchievabilityAssessment(
        status=status,
        required_annual_return=required_return,
        comparison_horizon_years=horizon,
        observed_upper_return=observed_upper,
    )
