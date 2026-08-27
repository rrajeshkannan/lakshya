"""[lakshya] FUND non-dominated frontier."""

from __future__ import annotations

from typing import Iterable, Mapping

from lakshya_core.dominance import Dimension, non_dominated_frontier

from .fund_comparator import fund_comparator_values


def fund_frontier(
    fingerprints: Iterable[object],
    dimensions: tuple[Dimension, ...],
) -> list[object]:
    """Return admitted Funds whose fingerprints are globally non-dominated.

    [lakshya] This is a thin FUND adapter. The dominance mathematics remains
    in lakshya_core; FUND supplies Fund-specific evidence and identity.
    """
    items = list(fingerprints)
    records: list[Mapping[str, object]] = []
    by_id: dict[int, object] = {}

    for index, fingerprint in enumerate(items):
        values = fund_comparator_values(fingerprint)
        record = dict(values)
        record["_index"] = index
        records.append(record)
        by_id[index] = fingerprint

    frontier_records = non_dominated_frontier(records, dimensions)
    return [by_id[int(record["_index"])] for record in frontier_records]
