"""[lakshya] Exact memory-bounded frontier accumulation."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from lakshya_core.dominance import Dimension, dominates


FrontierEvent = Callable[[str, object, object | None], None]


class FrontierAccumulator:
    """Maintain an exact non-dominated frontier while streaming candidates.

    [lakshya] A candidate that is dominated by the current frontier may be
    discarded immediately: transitivity guarantees that no later candidate
    can make it globally non-dominated. A candidate that survives removes
    every frontier member it dominates. This is safe because the retained
    frontier contains every object not dominated by any candidate seen so far.
    """

    def __init__(
        self,
        dimensions: tuple[Dimension, ...],
        *,
        on_event: FrontierEvent | None = None,
    ) -> None:
        self._dimensions = dimensions
        self._frontier: list[tuple[object, Mapping[str, Any]]] = []
        self._on_event = on_event

    def _emit(self, event: str, item: object, related: object | None = None) -> None:
        if self._on_event is not None:
            self._on_event(event, item, related)

    def consider(self, item: object, values: Mapping[str, Any]) -> bool:
        """Consider one candidate; return True if it enters the frontier."""
        dominator = next(
            (
                existing_item
                for existing_item, existing_values in self._frontier
                if dominates(existing_values, values, self._dimensions)
            ),
            None,
        )
        if dominator is not None:
            self._emit("dominated", item, dominator)
            return False

        survivors: list[tuple[object, Mapping[str, Any]]] = []
        for existing_item, existing_values in self._frontier:
            if dominates(values, existing_values, self._dimensions):
                self._emit("evicted", existing_item, item)
            else:
                survivors.append((existing_item, existing_values))

        self._frontier = survivors
        self._frontier.append((item, values))
        self._emit("admitted", item, None)
        return True

    def items(self) -> list[object]:
        """Return the current frontier in insertion order."""
        return [item for item, _ in self._frontier]


def streaming_frontier(
    items: Iterable[tuple[object, Mapping[str, Any]]],
    dimensions: tuple[Dimension, ...],
    *,
    on_event: FrontierEvent | None = None,
) -> list[object]:
    """Compute the exact frontier without retaining dominated candidates."""
    accumulator = FrontierAccumulator(dimensions, on_event=on_event)
    for item, values in items:
        accumulator.consider(item, values)
    return accumulator.items()
