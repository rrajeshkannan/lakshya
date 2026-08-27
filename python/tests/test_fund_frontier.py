"""[lakshya] Tests for the FUND non-dominated frontier adapter."""

from types import SimpleNamespace

from fund_analysis.fund_frontier import fund_frontier
from team_analysis.comparator_surface import fund_team_dimensions


def fingerprint(values):
    # [lakshya] Test fixture deliberately exposes only the 40 gate dimensions.
    elevation = {}
    for years in (3, 5, 7, 10):
        seed = values.get(f"elevation_{years}y_median", 0)
        elevation[f"rolling_{years}y"] = SimpleNamespace(
            minimum=seed,
            percentile_25=seed,
            median=seed,
            percentile_75=seed,
            maximum=seed,
            mean=seed,
            positive_period_pct=seed,
        )

    protection = SimpleNamespace(
        median_severity_pct=values.get("protection_median_severity_pct", 0),
        percentile_75_severity_pct=values.get("protection_percentile_75_severity_pct", 0),
        percentile_90_severity_pct=values.get("protection_percentile_90_severity_pct", 0),
        percentile_95_severity_pct=values.get("protection_percentile_95_severity_pct", 0),
        percentile_99_severity_pct=values.get("protection_percentile_99_severity_pct", 0),
        maximum_severity_pct=values.get("protection_maximum_severity_pct", 0),
        pct_days_at_or_above_threshold={
            threshold: values.get(f"protection_pct_days_at_or_above_{threshold}", 0)
            for threshold in (5, 10, 15, 20, 25, 30)
        },
    )
    return SimpleNamespace(elevation=SimpleNamespace(**elevation), protection=protection)


def all_values(value):
    return {dimension.name: value for dimension in fund_team_dimensions()}


def test_frontier_keeps_only_globally_non_dominated_funds():
    a = fingerprint(all_values(10))
    b = fingerprint(all_values(9))
    c = fingerprint(all_values(8))

    assert fund_frontier([a, b, c], fund_team_dimensions()) == [a]


def test_frontier_preserves_all_tradeoff_alternatives():
    a_values = all_values(10)
    b_values = all_values(10)
    # A better on the first dimension, B better on the second.
    a_values["elevation_3y_minimum"] = 11
    b_values["elevation_3y_median"] = 11
    a = fingerprint(a_values)
    b = fingerprint(b_values)

    assert fund_frontier([a, b], fund_team_dimensions()) == [a, b]


def test_frontier_does_not_prune_when_any_declared_dimension_is_unavailable():
    a_values = all_values(10)
    b_values = all_values(9)
    del a_values["elevation_10y_median"]
    a = fingerprint(a_values)
    b = fingerprint(b_values)

    assert fund_frontier([a, b], fund_team_dimensions()) == [a, b]
