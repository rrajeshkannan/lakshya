"""[lakshya] Tests for the FUND non-dominated frontier adapter."""

from types import SimpleNamespace

from fund_analysis.fund_frontier import fund_frontier
from team_analysis.comparator_surface import fund_team_dimensions


def fingerprint(values):
    # [lakshya] Test fixture maps every declared gate dimension independently.
    elevation = {}
    metrics = (
        "minimum", "percentile_25", "median", "percentile_75",
        "maximum", "mean", "positive_period_pct",
    )
    for years in (3, 5, 7, 10):
        fields = {}
        for metric in metrics:
            fields[metric] = values.get(f"elevation_{years}y_{metric}")
        elevation[f"rolling_{years}y"] = SimpleNamespace(**fields)

    protection = SimpleNamespace(
        median_severity_pct=values.get("protection_median_severity_pct"),
        percentile_75_severity_pct=values.get("protection_percentile_75_severity_pct"),
        percentile_90_severity_pct=values.get("protection_percentile_90_severity_pct"),
        percentile_95_severity_pct=values.get("protection_percentile_95_severity_pct"),
        percentile_99_severity_pct=values.get("protection_percentile_99_severity_pct"),
        maximum_severity_pct=values.get("protection_maximum_severity_pct"),
        pct_days_at_or_above_threshold={
            threshold: values.get(f"protection_pct_days_at_or_above_{threshold}")
            for threshold in (5, 10, 15, 20, 25, 30)
        },
    )
    return SimpleNamespace(elevation=SimpleNamespace(**elevation), protection=protection)


def all_values(value):
    return {dimension.name: value for dimension in fund_team_dimensions()}


def test_frontier_keeps_only_globally_non_dominated_funds():
    # A is better on both upward Elevation and downward Protection dimensions.
    a = fingerprint(all_values(10))
    b = fingerprint(all_values(11))
    c = fingerprint(all_values(12))

    assert fund_frontier([a, b, c], fund_team_dimensions()) == [a]


def test_frontier_preserves_all_tradeoff_alternatives():
    a_values = all_values(10)
    b_values = all_values(10)
    # A is better on one upward dimension; B is better on another upward dimension.
    a_values["elevation_3y_minimum"] = 11
    b_values["elevation_3y_median"] = 11
    a = fingerprint(a_values)
    b = fingerprint(b_values)

    assert fund_frontier([a, b], fund_team_dimensions()) == [a, b]


def test_frontier_does_not_prune_when_any_declared_dimension_is_unavailable():
    a_values = all_values(10)
    b_values = all_values(9)
    a_values["elevation_10y_median"] = None
    a = fingerprint(a_values)
    b = fingerprint(b_values)

    assert fund_frontier([a, b], fund_team_dimensions()) == [a, b]
