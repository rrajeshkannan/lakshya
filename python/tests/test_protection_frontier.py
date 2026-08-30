from __future__ import annotations

from dataclasses import dataclass

from lakshya_core.models import Fund
from team_analysis.composition import Composition
from team_analysis.protection_frontier import protection_frontier
from team_analysis.team import Team


@dataclass(frozen=True)
class _Evidence:
    values: dict[str, float | None]

    def __getitem__(self, key: str) -> float | None:
        return self.values[key]


@dataclass(frozen=True)
class _Fingerprint:
    composition: Composition
    elevation: object
    protection: _Evidence


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def _fingerprint(
    composition: Composition,
    protection: dict[str, float | None],
) -> _Fingerprint:
    return _Fingerprint(composition=composition, elevation={}, protection=_Evidence(protection))


def _protection(**overrides: float | None) -> dict[str, float | None]:
    metrics = (
        "median_severity_pct", "percentile_75_severity_pct",
        "percentile_90_severity_pct", "percentile_95_severity_pct",
        "percentile_99_severity_pct", "maximum_severity_pct",
        "pct_days_at_or_above_5", "pct_days_at_or_above_10",
        "pct_days_at_or_above_15", "pct_days_at_or_above_20",
        "pct_days_at_or_above_25", "pct_days_at_or_above_30",
    )
    values = {metric: 10.0 for metric in metrics}
    values.update(overrides)
    return values


def _compositions() -> tuple[Composition, Composition, Composition]:
    teams = [
        Team(members=(_fund(f"A{i}"), _fund(f"B{i}")))
        for i in range(3)
    ]
    return tuple(
        Composition(team=team, weights={f"A{i}": 0.95, f"B{i}": 0.05})
        for i, team in enumerate(teams)
    )


def test_protection_frontier_prunes_protection_dominated_composition():
    first, second, _ = _compositions()
    frontier = protection_frontier([
        (first, _fingerprint(first, _protection(maximum_severity_pct=10.0))),
        (second, _fingerprint(second, _protection(maximum_severity_pct=20.0))),
    ])

    assert frontier == [first]


def test_protection_frontier_retains_incomparable_compositions():
    first, second, _ = _compositions()
    frontier = protection_frontier([
        (first, _fingerprint(first, _protection(maximum_severity_pct=10.0, percentile_99_severity_pct=20.0))),
        (second, _fingerprint(second, _protection(maximum_severity_pct=20.0, percentile_99_severity_pct=10.0))),
    ])

    assert len(frontier) == 2
    assert any(candidate is first for candidate in frontier)
    assert any(candidate is second for candidate in frontier)


def test_protection_frontier_treats_unavailable_evidence_as_unknown():
    first, second, _ = _compositions()
    frontier = protection_frontier([
        (first, _fingerprint(first, _protection(pct_days_at_or_above_30=0.0))),
        (second, _fingerprint(second, _protection(pct_days_at_or_above_30=None))),
    ])

    assert len(frontier) == 2
    assert any(candidate is first for candidate in frontier)
    assert any(candidate is second for candidate in frontier)
