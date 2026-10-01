"""Experimental MISSION Protection-only weak Pareto pruning."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from lakshya_core.dominance import Dimension, non_dominated_frontier

from team_analysis.comparator_surface import protection_dimensions


def protection_only_frontier(
    candidates: Iterable[tuple[object, Mapping[str, Any]]],
    dimensions: tuple[Dimension, ...] | None = None,
) -> list[object]:
    """Return candidates non-dominated on Protection evidence alone.

    This is a MISSION-stage experiment applied after Purpose/Elevation
    qualification. It deliberately uses the complete declared Protection
    surface rather than the provisional lexicographic ladder.

    Dominance remains conservative: the shared generic dominance primitive
    refuses to establish dominance when any declared Protection dimension is
    unavailable for either candidate.
    """
    items = list(candidates)
    dims = protection_dimensions() if dimensions is None else dimensions
    records: list[Mapping[str, Any]] = []
    by_index: dict[int, object] = {}

    for index, (candidate, values) in enumerate(items):
        record = dict(values)
        record["_index"] = index
        records.append(record)
        by_index[index] = candidate

    frontier_records = non_dominated_frontier(records, dims)
    return [by_index[int(record["_index"])] for record in frontier_records]
