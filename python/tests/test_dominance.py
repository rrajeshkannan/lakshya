"""[lakshya] Tests for multidimensional dominance/frontier semantics."""

import pytest

from lakshya_core.dominance import Dimension, dominates, non_dominated_frontier
from team_analysis.comparator_surface import fund_team_dimensions


UP = Dimension("growth", "up")
DOWN = Dimension("drawdown", "down")


def test_dominance_requires_no_worse_on_every_dimension_and_better_on_one():
    dims = [UP, DOWN]

    assert dominates({"growth": 10, "drawdown": 5}, {"growth": 9, "drawdown": 6}, dims)
    assert not dominates({"growth": 10, "drawdown": 7}, {"growth": 9, "drawdown": 6}, dims)
    assert not dominates({"growth": 10, "drawdown": 5}, {"growth": 10, "drawdown": 5}, dims)


def test_all_objects_can_survive_if_none_is_dominated():
    # Higher growth is better; lower drawdown is better. Each object trades
    # one dimension for the other, so none dominates another.
    objects = [
        {"id": "A", "growth": 10, "drawdown": 10},
        {"id": "B", "growth": 9, "drawdown": 9},
        {"id": "C", "growth": 8, "drawdown": 8},
    ]
    frontier = non_dominated_frontier(objects, [UP, DOWN])
    assert [obj["id"] for obj in frontier] == ["A", "B", "C"]


def test_multiple_objects_can_be_removed():
    objects = [
        {"id": "A", "growth": 10, "drawdown": 5},
        {"id": "B", "growth": 9, "drawdown": 6},
        {"id": "C", "growth": 8, "drawdown": 7},
        {"id": "D", "growth": 7, "drawdown": 8},
    ]
    frontier = non_dominated_frontier(objects, [UP, DOWN])
    assert [obj["id"] for obj in frontier] == ["A"]


def test_frontier_is_independent_of_candidate_order():
    dims = [UP, DOWN]
    objects = [
        {"id": "A", "growth": 10, "drawdown": 10},
        {"id": "B", "growth": 9, "drawdown": 9},
        {"id": "C", "growth": 8, "drawdown": 8},
    ]
    first = {obj["id"] for obj in non_dominated_frontier(objects, dims)}
    second = {obj["id"] for obj in non_dominated_frontier(list(reversed(objects)), dims)}
    assert first == second == {"A", "B", "C"}


@pytest.mark.parametrize("dimension", fund_team_dimensions(), ids=lambda d: d.name)
def test_every_declared_gate_dimension_requires_availability(dimension):
    """Every one of the 40 dimensions is protected from unknown-as-comparable."""
    other_dimensions = [d for d in fund_team_dimensions() if d.name != dimension.name]
    a = {d.name: 10.0 for d in fund_team_dimensions()}
    b = {d.name: 9.0 for d in fund_team_dimensions()}

    del a[dimension.name]
    assert not dominates(a, b, other_dimensions + [dimension])
    assert not dominates(b, a, other_dimensions + [dimension])


def test_multiple_missing_dimensions_still_prevent_dominance():
    dims = fund_team_dimensions()
    a = {d.name: 10.0 for d in dims}
    b = {d.name: 9.0 for d in dims}
    del a[dims[0].name]
    del b[dims[-1].name]

    assert not dominates(a, b, dims)
    assert not dominates(b, a, dims)


def test_no_dimensions_means_no_dominance():
    assert not dominates({"x": 10}, {"x": 1}, [])


def test_invalid_direction_is_rejected():
    with pytest.raises(ValueError):
        Dimension("growth", "sideways")
