"""[lakshya] TEAM non-dominated frontier."""

from __future__ import annotations

from typing import Iterable, Mapping

from lakshya_core.dominance import Dimension, non_dominated_frontier

from .team_comparator import team_comparator_values


def team_frontier(
    fingerprints: Iterable[object],
    dimensions: tuple[Dimension, ...],
) -> list[object]:
    """Return Teams whose collective fingerprints are globally non-dominated."""
    items = list(fingerprints)
    records: list[Mapping[str, object]] = []
    by_id: dict[int, object] = {}

    for index, fingerprint in enumerate(items):
        record = dict(team_comparator_values(fingerprint))
        record["_index"] = index
        records.append(record)
        by_id[index] = fingerprint

    frontier_records = non_dominated_frontier(records, dimensions)
    return [by_id[int(record["_index"])] for record in frontier_records]
