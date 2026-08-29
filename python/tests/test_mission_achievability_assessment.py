from types import SimpleNamespace

from lakshya_core.rolling_returns import RollingReturnEvidence
from mission.achievability_interpretation import AchievabilityStatus, assess_achievability
from mission.achievability import required_annual_return
from mission.models import Purpose


def evidence(years: int, maximum: float) -> RollingReturnEvidence:
    return RollingReturnEvidence(
        years=years,
        observations=10,
        minimum=-0.10,
        percentile_25=0.02,
        median=0.08,
        percentile_75=0.12,
        maximum=maximum,
        mean=0.08,
        standard_deviation=0.10,
        positive_periods=8,
        negative_periods=2,
        positive_period_pct=80.0,
        latest=0.09,
    )


def fingerprint(*, rolling_3y=None, rolling_5y=None, rolling_7y=None, rolling_10y=None):
    return SimpleNamespace(
        elevation=SimpleNamespace(
            rolling_3y=rolling_3y,
            rolling_5y=rolling_5y,
            rolling_7y=rolling_7y,
            rolling_10y=rolling_10y,
        )
    )


def test_requirement_within_observed_terrain():
    purpose = Purpose("Retirement", 100.0, desired_target=120.0, horizon_years=10)
    required = required_annual_return(purpose)
    fp = fingerprint(rolling_10y=evidence(10, required))

    assessment = assess_achievability(purpose, fp, required)

    assert assessment.status == "within_observed_terrain"
    assert assessment.comparison_horizon_years == 10
    assert assessment.observed_upper_return == required


def test_requirement_beyond_observed_terrain():
    purpose = Purpose("Retirement", 100.0, desired_target=300.0, horizon_years=10)
    required = required_annual_return(purpose)
    fp = fingerprint(rolling_10y=evidence(10, required - 0.01))

    assessment = assess_achievability(purpose, fp, required)

    assert assessment.status == "beyond_observed_terrain"


def test_uses_longest_supported_horizon_not_exceeding_purpose_horizon():
    purpose = Purpose("Retirement", 100.0, desired_target=120.0, horizon_years=8)
    required = required_annual_return(purpose)
    fp = fingerprint(
        rolling_7y=evidence(7, required),
        rolling_10y=evidence(10, required + 0.10),
    )

    assessment = assess_achievability(purpose, fp, required)

    assert assessment.comparison_horizon_years == 7
    assert assessment.observed_upper_return == required


def test_returns_insufficient_evidence_when_no_supported_horizon_exists():
    purpose = Purpose("Retirement", 100.0, desired_target=120.0, horizon_years=2)
    required = required_annual_return(purpose)
    fp = fingerprint()

    assessment = assess_achievability(purpose, fp, required)

    assert assessment.status == "insufficient_evidence"
    assert assessment.required_annual_return == required


def test_open_ended_purpose_is_not_applicable():
    purpose = Purpose("Stitch", 100.0)
    fp = fingerprint(rolling_10y=evidence(10, 0.10))

    assessment = assess_achievability(purpose, fp, required_annual_return(purpose))

    assert assessment.status == "not_applicable"
    assert assessment.required_annual_return is None
