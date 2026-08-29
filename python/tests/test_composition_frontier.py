from __future__ import annotations

from dataclasses import dataclass

from lakshya_core.models import Fund
from team_analysis.composition import Composition
from team_analysis.composition_frontier import global_composition_frontier
from team_analysis.team import Team


@dataclass(frozen=True)
class _Evidence:
    values: dict[str, float]

    def __getitem__(self, key: str) -> float:
        return self.values[key]


@dataclass(frozen=True)
class _Fingerprint:
    composition: Composition
    elevation: dict[int, _Evidence]
    protection: _Evidence


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def _fingerprint(composition: Composition, value: float) -> _Fingerprint:
    metrics = (
        "minimum", "percentile_25", "median", "percentile_75",
        "maximum", "mean", "positive_period_pct",
    )
    elevation = {
        years: _Evidence({metric: value for metric in metrics})
        for years in (3, 5, 7, 10)
    }
    protection_metrics = (
        "median_severity_pct", "percentile_75_severity_pct",
        "percentile_90_severity_pct", "percentile_95_severity_pct",
        "percentile_99_severity_pct", "maximum_severity_pct",
        "pct_days_at_or_above_5", "pct_days_at_or_above_10",
        "pct_days_at_or_above_15", "pct_days_at_or_above_20",
        "pct_days_at_or_above_25", "pct_days_at_or_above_30",
    )
    return _Fingerprint(
        composition=composition,
        elevation=elevation,
        protection=_Evidence({metric: value for metric in protection_metrics}),
    )


def test_composition_frontier_is_global_across_team_provenance():
    """A Composition from one Team can remove a dominated Composition from another."""
    team_a = Team(members=(_fund("A"), _fund("B")))
    team_b = Team(members=(_fund("C"), _fund("D")))
    superior = Composition(team=team_a, weights={"A": 0.95, "B": 0.05})
    dominated = Composition(team=team_b, weights={"C": 0.95, "D": 0.05})

    frontier = global_composition_frontier([
        (superior, _fingerprint(superior, 2.0)),
        (dominated, _fingerprint(dominated, 1.0)),
    ])

    assert frontier == [superior]


def test_composition_frontier_retains_incomparable_compositions():
    team_a = Team(members=(_fund("A"), _fund("B")))
    team_b = Team(members=(_fund("C"), _fund("D")))
    first = Composition(team=team_a, weights={"A": 0.95, "B": 0.05})
    second = Composition(team=team_b, weights={"C": 0.95, "D": 0.05})

    first_values = _fingerprint(first, 2.0)
    second_values = _fingerprint(second, 2.0)
    second_values = _Fingerprint(
        composition=second,
        elevation={
            years: _Evidence({
                metric: (3.0 if metric == "minimum" else 1.0)
                for metric in (
                    "minimum", "percentile_25", "median", "percentile_75",
                    "maximum", "mean", "positive_period_pct",
                )
            })
            for years in (3, 5, 7, 10)
        },
        protection=second_values.protection,
    )

    assert global_composition_frontier([
        (first, first_values),
        (second, second_values),
    ]) == [first, second]
