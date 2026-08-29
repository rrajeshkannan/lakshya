from __future__ import annotations

from types import SimpleNamespace

from mission.achievability import required_annual_return
from mission.achievability_assessment import (
    AchievabilityStatus,
    assess_achievability,
)
from mission.models import Purpose


def _elevation(*, rolling_3y=None, rolling_5y=None, rolling_7y=None, rolling_10y=None):
    return SimpleNamespace(
        rolling_3y=rolling_3y,
        rolling_5y=rolling_5y,
        rolling_7y=rolling_7y,
        rolling_10y=rolling_10y,
    )


def _fingerprint(elevation):
    return SimpleNamespace(elevation=elevation)


def _purpose(*, horizon_years=10):
    return Purpose(
        name="Test purpose",
        current_capital=500_000,
        desired_target=1_500_000,
        horizon_years=horizon_years,
    )


def test_achievability_uses_composition_evidence_on_nearest_lower_horizon():
    purpose = _purpose(horizon_years=8)
    required = required_annual_return(purpose)
    fingerprint = _fingerprint(
        _elevation(
            rolling_3y=SimpleNamespace(maximum=required - 0.01),
            rolling_5y=SimpleNamespace(maximum=required - 0.01),
            rolling_7y=SimpleNamespace(maximum=required + 0.01),
            rolling_10y=SimpleNamespace(maximum=required + 0.20),
        )
    )

    assessment = assess_achievability(purpose, fingerprint)

    assert assessment.status is AchievabilityStatus.WITHIN_OBSERVED_TERRAIN
    assert assessment.evidence_horizon_years == 7
    assert assessment.observed_upper_terrain == required + 0.01


def test_achievability_rejects_composition_below_required_elevation():
    purpose = _purpose(horizon_years=10)
    required = required_annual_return(purpose)
    fingerprint = _fingerprint(
        _elevation(rolling_10y=SimpleNamespace(maximum=required - 0.01))
    )

    assessment = assess_achievability(purpose, fingerprint)

    assert assessment.status is AchievabilityStatus.BEYOND_OBSERVED_TERRAIN
    assert assessment.evidence_horizon_years == 10
    assert assessment.observed_upper_terrain == required - 0.01


def test_achievability_reports_insufficient_composition_evidence():
    purpose = _purpose(horizon_years=10)
    fingerprint = _fingerprint(_elevation())

    assessment = assess_achievability(purpose, fingerprint)

    assert assessment.status is AchievabilityStatus.INSUFFICIENT_EVIDENCE
    assert assessment.evidence_horizon_years is None
    assert assessment.observed_upper_terrain is None
