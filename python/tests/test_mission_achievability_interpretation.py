"""Tests for the qualitative MISSION achievability interpretation."""

from types import SimpleNamespace

from mission.achievability_interpretation import assess_achievability
from mission.models import Purpose


def fingerprint(maximum: float | None, horizon: int = 5):
    evidence = SimpleNamespace(maximum=maximum)
    elevation = SimpleNamespace(**{f"rolling_{horizon}y": evidence})
    return SimpleNamespace(elevation=elevation)


def test_requirement_within_observed_upper_terrain_is_plausible():
    purpose = Purpose(
        name="Retirement",
        current_capital=100_000,
        desired_target=150_000,
        horizon_years=5,
    )

    result = assess_achievability(purpose, fingerprint(0.12), 0.10)

    assert result.status == "within_observed_terrain"
    assert result.comparison_horizon_years == 5
    assert result.observed_upper_return == 0.12


def test_requirement_beyond_observed_upper_terrain_is_not_called_plausible():
    purpose = Purpose(
        name="Retirement",
        current_capital=100_000,
        desired_target=200_000,
        horizon_years=5,
    )

    result = assess_achievability(purpose, fingerprint(0.10), 0.15)

    assert result.status == "beyond_observed_terrain"


def test_longer_purpose_uses_longest_supported_horizon_not_beyond_it():
    purpose = Purpose(
        name="Retirement",
        current_capital=100_000,
        desired_target=200_000,
        horizon_years=8,
    )

    fp = SimpleNamespace(
        elevation=SimpleNamespace(
            rolling_3y=SimpleNamespace(maximum=0.08),
            rolling_5y=SimpleNamespace(maximum=0.10),
            rolling_7y=SimpleNamespace(maximum=0.12),
            rolling_10y=SimpleNamespace(maximum=0.14),
        )
    )

    result = assess_achievability(purpose, fp, 0.11)

    assert result.status == "within_observed_terrain"
    assert result.comparison_horizon_years == 7
    assert result.observed_upper_return == 0.12


def test_short_purpose_without_supported_observation_is_insufficient():
    purpose = Purpose(
        name="Goal",
        current_capital=100_000,
        desired_target=110_000,
        horizon_years=2,
    )

    result = assess_achievability(purpose, fingerprint(0.12), 0.05)

    assert result.status == "insufficient_evidence"
    assert result.comparison_horizon_years is None


def test_open_ended_purpose_is_not_applicable():
    purpose = Purpose(name="Stitch", current_capital=326_000)

    result = assess_achievability(purpose, fingerprint(0.12), None)

    assert result.status == "not_applicable"
    assert result.required_annual_return is None
