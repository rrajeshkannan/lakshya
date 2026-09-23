"""Atomic persistence helpers for materialized LTS slice artifacts."""

from __future__ import annotations

from pathlib import Path

from .slice_export import write_materialized_slices_csv
from .slice_materialization import MaterializedSlice


def persist_materialized_slices_csv(
    slices: tuple[MaterializedSlice, ...],
    destination: Path,
) -> Path:
    """Write materialized slices atomically and return the destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    write_materialized_slices_csv(slices, temporary)
    temporary.replace(destination)
    return destination


__all__ = ["persist_materialized_slices_csv"]
