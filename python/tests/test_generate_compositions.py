from __future__ import annotations

from lakshya_core.models import Fund
from team_analysis.generate_compositions import generate_compositions
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_singleton_is_fixed_at_one_hundred_percent():
    team = Team(members=(_fund("A"),))
    compositions = generate_compositions(team)
    assert len(compositions) == 1
    assert compositions[0].weights == {"A": 1.0}


def test_twin_uses_positive_five_percent_grid():
    team = Team(members=(_fund("A"), _fund("B")))
    compositions = generate_compositions(team)
    assert len(compositions) == 19
    assert compositions[0].weights == {"A": 0.05, "B": 0.95}
    assert compositions[-1].weights == {"A": 0.95, "B": 0.05}
    assert all(all(weight > 0 for weight in c.weights.values()) for c in compositions)
    assert all(abs(sum(c.weights.values()) - 1.0) < 1e-9 for c in compositions)


def test_trio_uses_positive_five_percent_grid():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))
    compositions = generate_compositions(team)
    assert len(compositions) == 171
    assert len({tuple(c.weights.values()) for c in compositions}) == 171
    assert all(all(weight > 0 for weight in c.weights.values()) for c in compositions)
    assert all(abs(sum(c.weights.values()) - 1.0) < 1e-9 for c in compositions)


def test_generate_compositions_is_positive_and_complete_on_requested_grid():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))
    compositions = generate_compositions(team, step=0.10)
    assert len(compositions) == 36
    assert len({tuple(c.weights.values()) for c in compositions}) == 36
    assert all(all(weight >= 0.10 for weight in c.weights.values()) for c in compositions)
    assert all(abs(sum(c.weights.values()) - 1.0) < 1e-9 for c in compositions)


def test_generate_compositions_returns_empty_when_grid_cannot_give_every_member_one_unit():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))
    assert generate_compositions(team, step=0.50) == []


def test_generate_compositions_rejects_invalid_step():
    team = Team(members=(_fund("A"), _fund("B")))
    for step in (0.0, -0.05, 1.1, 0.03):
        try:
            generate_compositions(team, step=step)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for step={step}")
