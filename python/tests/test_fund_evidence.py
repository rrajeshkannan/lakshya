import pandas as pd
import pytest

from lakshya_core.drawdown_severity import calculate_protection
from lakshya_core.elevation import calculate_elevation
from lakshya_core.models import ElevationEvidence
from lakshya_core.rolling_returns import RollingReturnEvidence, calculate_rolling_cagr


def test_elevation_can_have_missing_long_horizon_evidence():
    rolling_3y = RollingReturnEvidence(
        years=3, observations=100, minimum=-5.0, percentile_25=8.0,
        median=12.0, percentile_75=16.0, maximum=25.0, mean=12.5,
        standard_deviation=5.0, positive_periods=95, negative_periods=5,
        positive_period_pct=95.0, latest=14.0,
    )
    elevation = ElevationEvidence(
        rolling_3y=rolling_3y, rolling_5y=None, rolling_7y=None, rolling_10y=None,
    )
    assert elevation.rolling_3y is not None
    assert elevation.rolling_5y is None
    assert elevation.rolling_7y is None
    assert elevation.rolling_10y is None


def test_elevation_preserves_horizon_evidence_state():
    dates = pd.date_range("2020-01-01", periods=1500, freq="D")
    nav = pd.DataFrame({"date": dates, "nav": range(100, 1600)})
    elevation = calculate_elevation(nav)
    assert elevation.rolling_3y is not None
    assert elevation.rolling_5y is None
    assert elevation.rolling_7y is None
    assert elevation.rolling_10y is None


def test_protection_measures_severity_from_funds_own_high_water_mark():
    nav = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]),
        "nav": [100.0, 90.0, 80.0, 90.0],
    })
    protection = calculate_protection(nav)
    assert protection.observations == 4
    assert protection.median_severity_pct == pytest.approx(10.0)
    assert protection.maximum_severity_pct == pytest.approx(20.0)
    assert protection.days_at_or_above_threshold[5] == 3
    assert protection.days_at_or_above_threshold[10] == 3
    assert protection.days_at_or_above_threshold[15] == 1
    assert protection.days_at_or_above_threshold[20] == 1


def test_rolling_cagr_uses_latest_nav_on_or_before_lookback_date():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-03", "2025-01-02"]),
        "nav": [100.0, 110.0, 121.0],
    })
    evidence = calculate_rolling_cagr(df, 5)
    expected = (121.0 / 100.0) ** (1 / 5) - 1
    assert evidence.latest == pytest.approx(expected)
