from __future__ import annotations

from lakshya_core.models import Fund
from team_analysis.composition_generator import generate_compositions
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_three_member_team_generates_complete_five_percent_grid():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))

    compositions = generate_compositions(team)

    assert len(compositions) == 231
    assert all(abs(sum(c.weights.values()) - 1.0) < 1e-9 for c in compositions)
    assert all(all(weight >= 0 for weight in c.weights.values()) for c in compositions)
    assert len({tuple(c.weights[isin] for isin in ("A", "B", "C")) for c in compositions}) == 231


def test_zero_weights_naturally_express_singleton_and_twin_shapes():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))

    compositions = generate_compositions(team)
    weights = {tuple(c.weights[isin] for isin in ("A", "B", "C")) for c in compositions}

    assert (1.0, 0.0, 0.0) in weights
    assert (0.9, 0.1, 0.0) in weights
    assert (0.9, 0.05, 0.05) in weights


def test_two_member_team_generates_twenty_one_compositions():
    team = Team(members=(_fund("A"), _fund("B")))

    assert len(generate_compositions(team)) == 21


def test_generator_supports_custom_grid_step():
    team = Team(members=(_fund("A"), _fund("B")))

    assert len(generate_compositions(team, step_pct=10)) == 11
