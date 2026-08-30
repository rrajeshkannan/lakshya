from __future__ import annotations

from mission.protection_pareto import protection_only_frontier
from team_analysis.comparator_surface import protection_dimensions


PROTECTION_NAMES = tuple(dimension.name for dimension in protection_dimensions())


def _candidate(name: str, **overrides: float):
    values = {metric: 10.0 for metric in PROTECTION_NAMES}
    values.update(overrides)
    return {"name": name, **values}


def test_protection_only_frontier_removes_clear_protection_dominator():
    superior = _candidate(
        "A",
        protection_maximum_severity_pct=20.0,
        protection_percentile_99_severity_pct=20.0,
    )
    dominated = _candidate(
        "B",
        protection_maximum_severity_pct=25.0,
        protection_percentile_99_severity_pct=25.0,
    )

    frontier = protection_only_frontier([(superior, superior), (dominated, dominated)])

    assert [candidate["name"] for candidate in frontier] == ["A"]


def test_protection_only_frontier_retains_incomparable_candidates():
    a = _candidate(
        "A",
        protection_maximum_severity_pct=20.0,
        protection_percentile_99_severity_pct=30.0,
    )
    b = _candidate(
        "B",
        protection_maximum_severity_pct=30.0,
        protection_percentile_99_severity_pct=20.0,
    )

    frontier = protection_only_frontier([(a, a), (b, b)])

    assert [candidate["name"] for candidate in frontier] == ["A", "B"]


def test_zero_is_observed_protection_evidence():
    a = _candidate("A", protection_pct_days_at_or_above_30=0.0)
    b = _candidate("B", protection_pct_days_at_or_above_30=1.0)

    # Other dimensions are tied, so the observed zero can participate in
    # Protection dominance.
    frontier = protection_only_frontier([(a, a), (b, b)])

    assert [candidate["name"] for candidate in frontier] == ["A"]


def test_unavailable_protection_evidence_prevents_dominance():
    a = _candidate("A", protection_pct_days_at_or_above_30=None)
    b = _candidate("B", protection_pct_days_at_or_above_30=1.0)

    frontier = protection_only_frontier([(a, a), (b, b)])

    assert [candidate["name"] for candidate in frontier] == ["A", "B"]
