"""[lakshya] Exact memory-bounded frontier accumulation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from lakshya_core.dominance import Dimension, dominates


class FrontierAccumulator:
    """Maintain an exact non-dominated frontier while streaming candidates.

    [lakshya] A candidate that is dominated by the current frontier may be
    discarded immediately: transitivity guarantees that no later candidate
    can make it globally non-dominated. A candidate that survives removes
    every frontier member it dominates. This is safe because the retained
    frontier contains every object not dominated by any candidate seen so far.
    """

    def __init__(self, dimensions: tuple[Dimension, ...]) -> None:
        self._dimensions = dimensions
        self._frontier: list[tuple[object, Mapping[str, Any]]] = []

    def consider(self, item: object, values: Mapping[str, Any]) -> bool:
        """Consider one candidate; return True if it enters the frontier."""
        if any(
            dominates(existing_values, values, self._dimensions)
            for _, existing_values in self._frontier
        ):
            return False

        self._frontier = [
            (existing_item, existing_values)
            for existing_item, existing_values in self._frontier
            if not dominates(values, existing_values, self._dimensions)
        ]
        self._frontier.append((item, values))
        return True

    def items(self) -> list[object]:
        """Return the current frontier in insertion order."""
        return [item for item, _ in self._frontier]


def streaming_frontier(
    items: Iterable[tuple[object, Mapping[str, Any]]],
    dimensions: tuple[Dimension, ...],
) -> list[object]:
    """Compute the exact frontier without retaining dominated candidates."""
    accumulator = FrontierAccumulator(dimensions)
    for item, values in items:
        accumulator.consider(item, values)
    return accumulator.items()
