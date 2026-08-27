"""[lakshya] Tests for the Fund -> TEAM comparator adapter."""

from types import SimpleNamespace

from fund_analysis.fund_comparator import fund_comparator_values
from team_analysis.comparator_surface import fund_team_dimensions


def rolling(seed: float) -> SimpleNamespace:
    return SimpleNamespace(
        minimum=seed,
        percentile_25=seed + 1,
        median=seed + 2,
        percentile_75=seed + 3,
        maximum=seed + 4,
        mean=seed + 5,
        positive_period_pct=seed + 6,
        standard_deviation=999,
        positive_periods=998,
        negative_periods=997,
        latest=996,
    )


def fingerprint():
    elevation = SimpleNamespace(
        rolling_3y=rolling(1),
        rolling_5y=rolling(11),
        rolling_7y=rolling(21),
        rolling_10y=rolling(31),
    )
    protection = SimpleNamespace(
        median_severity_pct=1,
        percentile_75_severity_pct=2,
        percentile_90_severity_pct=3,
        percentile_95_severity_pct=4,
        percentile_99_severity_pct=5,
        maximum_severity_pct=6,
        pct_days_at_or_above_threshold={5: 10, 10: 11, 15: 12, 20: 13, 25: 14, 30: 15},
        days_at_or_above_threshold={5: 100},
        observations=100,
    )
    return SimpleNamespace(elevation=elevation, protection=protection)


def test_adapter_produces_exactly_the_declared_surface():
    values = fund_comparator_values(fingerprint())
    assert set(values) == {dimension.name for dimension in fund_team_dimensions()}
    assert len(values) == 40


def test_adapter_maps_all_elevation_metrics_without_folding():
    values = fund_comparator_values(fingerprint())
    assert values["elevation_3y_minimum"] == 1
    assert values["elevation_3y_median"] == 3
    assert values["elevation_3y_mean"] == 6
    assert values["elevation_10y_positive_period_pct"] == 37


def test_adapter_maps_protection_percentages_not_raw_day_counts():
    values = fund_comparator_values(fingerprint())
    assert values["protection_median_severity_pct"] == 1
    assert values["protection_pct_days_at_or_above_5"] == 10
    assert "protection_days_at_or_above_5" not in values


def test_unavailable_elevation_horizon_remains_unavailable():
    fp = fingerprint()
    fp.elevation.rolling_10y = None

    values = fund_comparator_values(fp)

    # [lakshya] The declared 40-D contract remains intact; unavailable
    # evidence is represented explicitly as None, never omitted or invented.
    assert "elevation_10y_median" in values
    assert values["elevation_10y_median"] is None
