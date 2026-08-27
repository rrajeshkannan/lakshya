"""[lakshya] Tests for exact streaming frontier semantics."""

from lakshya_core.dominance import Dimension
from team_analysis.streaming_frontier import FrontierAccumulator, streaming_frontier

UP = Dimension("x", "up")
DOWN = Dimension("y", "down")


def test_dominated_candidate_can_be_discarded_immediately():
    a = object()
    b = object()
    accumulator = FrontierAccumulator((UP,))

    assert accumulator.consider(a, {"x": 10})
    assert not accumulator.consider(b, {"x": 9})
    assert accumulator.items() == [a]


def test_incoming_candidate_can_remove_multiple_frontier_members():
    a, b, c = object(), object(), object()
    accumulator = FrontierAccumulator((UP, DOWN))

    assert accumulator.consider(a, {"x": 10, "y": 10})
    assert accumulator.consider(b, {"x": 9, "y": 9})
    assert accumulator.consider(c, {"x": 11, "y": 8})
    assert accumulator.items() == [c]


def test_tradeoffs_remain_on_frontier():
    a, b = object(), object()
    result = streaming_frontier(
        [(a, {"x": 10, "y": 8}), (b, {"x": 8, "y": 10})],
        (UP, DOWN),
    )
    assert result == [a, b]


def test_the_classic_basket_trap_is_safe():
    a, c, d = object(), object(), object()
    accumulator = FrontierAccumulator((UP, DOWN))

    # A and C are initially incomparable. D dominates A, but not C.
    accumulator.consider(a, {"x": 10, "y": 10})
    accumulator.consider(c, {"x": 12, "y": 8})
    accumulator.consider(d, {"x": 11, "y": 9})

    assert accumulator.items() == [c, d]
