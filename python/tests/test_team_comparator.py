"""[lakshya] Tests for Team comparator evidence."""

from types import SimpleNamespace

from team_analysis.comparator_surface import fund_team_dimensions
from team_analysis.team_comparator import team_comparator_values


def make_fingerprint():
    def rolling(seed):
        return SimpleNamespace(
            minimum=seed, percentile_25=seed + 1, median=seed + 2,
            percentile_75=seed + 3, maximum=seed + 4, mean=seed + 5,
            positive_period_pct=seed + 6,
        )

    elevation = SimpleNamespace(
        rolling_3y=rolling(1), rolling_5y=rolling(11),
        rolling_7y=rolling(21), rolling_10y=rolling(31),
    )
    protection = SimpleNamespace(
        median_severity_pct=1, percentile_75_severity_pct=2,
        percentile_90_severity_pct=3, percentile_95_severity_pct=4,
        percentile_99_severity_pct=5, maximum_severity_pct=6,
        pct_days_at_or_above_threshold={5: 10, 10: 11, 15: 12, 20: 13, 25: 14, 30: 15},
    )
    return SimpleNamespace(elevation=elevation, protection=protection)


def test_team_adapter_has_exactly_the_declared_40_dimensions():
    values = team_comparator_values(make_fingerprint())
    assert set(values) == {d.name for d in fund_team_dimensions()}
    assert len(values) == 40


def test_team_adapter_reads_collective_fingerprint_without_constituent_metrics():
    values = team_comparator_values(make_fingerprint())
    assert values["elevation_3y_median"] == 3
    assert values["protection_percentile_99_severity_pct"] == 5
    assert values["protection_pct_days_at_or_above_30"] == 15
