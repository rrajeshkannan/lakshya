from __future__ import annotations

from lakshya_core.models import Fund
from team_analysis.generate_compositions import generate_compositions
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_generate_compositions_uses_five_percent_grid_by_default():
    team = Team(members=(_fund("A"), _fund("B")))

    compositions = generate_compositions(team)

    assert len(compositions) == 21
    assert compositions[0].weights == {"A": 0.0, "B": 1.0}
    assert compositions[-1].weights == {"A": 1.0, "B": 0.0}
    assert {weight for c in compositions for weight in c.weights.values()} <= {
        0.0,
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.35,
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90,
        0.95,
        1.0,
    }


def test_generate_compositions_includes_five_percent_perturbations():
    team = Team(members=(_fund("A"), _fund("B")))

    compositions = generate_compositions(team)

    assert {0.95, 0.05} in [set(c.weights.values()) for c in compositions]


def test_generate_compositions_is_complete_on_the_requested_grid():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))

    compositions = generate_compositions(team, step=0.10)

    assert len(compositions) == 66
    assert len({tuple(c.weights.values()) for c in compositions}) == 66
    assert all(abs(sum(c.weights.values()) - 1.0) < 1e-9 for c in compositions)


def test_generate_compositions_rejects_invalid_step():
    team = Team(members=(_fund("A"), _fund("B")))

    for step in (0.0, -0.05, 1.1, 0.03):
        try:
            generate_compositions(team, step=step)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for step={step}")
