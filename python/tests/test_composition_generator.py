from __future__ import annotations

from lakshya_core.models import Fund
from team_analysis.generate_compositions import generate_compositions
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_three_member_team_generates_complete_positive_five_percent_grid():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))
    compositions = generate_compositions(team)
    assert len(compositions) == 171
    assert all(abs(sum(c.weights.values()) - 1.0) < 1e-9 for c in compositions)
    assert all(all(weight > 0 for weight in c.weights.values()) for c in compositions)
    assert len({tuple(c.weights[isin] for isin in ("A", "B", "C")) for c in compositions}) == 171


def test_positive_weights_exclude_singleton_and_twin_boundary_shapes_from_trio():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))
    compositions = generate_compositions(team)
    weights = {tuple(c.weights[isin] for isin in ("A", "B", "C")) for c in compositions}
    assert (1.0, 0.0, 0.0) not in weights
    assert (0.9, 0.1, 0.0) not in weights
    assert (0.9, 0.05, 0.05) in weights


def test_two_member_team_generates_nineteen_positive_weight_compositions():
    team = Team(members=(_fund("A"), _fund("B")))
    compositions = generate_compositions(team)
    assert len(compositions) == 19
    assert all(0 < c.weights["A"] < 1 and 0 < c.weights["B"] < 1 for c in compositions)


def test_generator_supports_custom_positive_weight_grid_step():
    team = Team(members=(_fund("A"), _fund("B")))
    assert len(generate_compositions(team, step=0.10)) == 9
