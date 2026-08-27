"""[lakshya] Tests for multidimensional dominance/frontier semantics."""

from lakshya_core.dominance import Dimension, dominates, non_dominated_frontier


UP = Dimension("growth", "up")
DOWN = Dimension("drawdown", "down")


def test_dominance_requires_no_worse_on_every_dimension_and_better_on_one():
    dims = [UP, DOWN]

    assert dominates(
        {"growth": 10, "drawdown": 5},
        {"growth": 9, "drawdown": 6},
        dims,
    )
    assert not dominates(
        {"growth": 10, "drawdown": 7},
        {"growth": 9, "drawdown": 6},
        dims,
    )
    assert not dominates(
        {"growth": 10, "drawdown": 5},
        {"growth": 10, "drawdown": 5},
        dims,
    )


def test_all_objects_can_survive_if_none_is_dominated():
    objects = [
        {"id": "A", "growth": 10, "drawdown": 8},
        {"id": "B", "growth": 8, "drawdown": 10},
        {"id": "C", "growth": 9, "drawdown": 9},
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
    a = {"id": "A", "growth": 10, "drawdown": 5}
    b = {"id": "B", "growth": 8, "drawdown": 10}
    c = {"id": "C", "growth": 9, "drawdown": 9}

    first = {obj["id"] for obj in non_dominated_frontier([a, b, c], dims)}
    second = {obj["id"] for obj in non_dominated_frontier([c, a, b], dims)}

    assert first == second == {"A", "B", "C"}


def test_dominance_is_not_triggered_when_a_dimension_is_missing():
    dims = [UP, DOWN]

    assert not dominates(
        {"growth": 10},
        {"growth": 9, "drawdown": 6},
        dims,
    )


def test_invalid_direction_is_rejected():
    try:
        Dimension("growth", "sideways")
    except ValueError as exc:
        assert "up" in str(exc) and "down" in str(exc)
    else:
        raise AssertionError("Invalid direction should have been rejected")
