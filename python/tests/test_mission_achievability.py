"""Tests for the MISSION achievability contract."""

from math import isclose

import pytest

from mission.achievability import required_annual_return
from mission.models import Purpose


def test_capital_alone_uses_horizon() -> None:
    purpose = Purpose(name="Retirement", capital=100_000, desired_target=121_000, horizon_years=2)
    required = required_annual_return(purpose)
    assert required is not None
    assert isclose(required, 0.10, rel_tol=1e-9)


def test_monthly_contribution_is_time_distributed() -> None:
    purpose = Purpose(name="Goal", capital=0, desired_target=12_000, horizon_years=1, monthly_contribution=1_000)
    required = required_annual_return(purpose)
    assert required == 0.0


def test_no_target_or_horizon_means_achievability_not_applicable() -> None:
    purpose = Purpose(name="Stitch", capital=326_000)
    assert required_annual_return(purpose) is None


def test_capital_at_or_above_target_needs_no_growth() -> None:
    purpose = Purpose(name="Goal", capital=150_000, desired_target=100_000, horizon_years=5)
    assert required_annual_return(purpose) == 0.0


def test_invalid_horizon_is_rejected() -> None:
    purpose = Purpose(name="Goal", capital=100_000, desired_target=150_000, horizon_years=0)
    with pytest.raises(ValueError, match="horizon_years"):
        required_annual_return(purpose)


def test_negative_contribution_is_rejected() -> None:
    purpose = Purpose(name="Goal", capital=100_000, desired_target=150_000, horizon_years=5, monthly_contribution=-1)
    with pytest.raises(ValueError, match="monthly_contribution"):
        required_annual_return(purpose)
