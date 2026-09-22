"""Convenience execution path that exposes conservation-balanced virtual slices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .runner import LtsRunResult, run_lts_transition
from .slice_materialization import MaterializedSlice, materialize_transition_slices


@dataclass(frozen=True)
class MaterializedLtsRunResult:
    """LTS result together with its outcome-specific virtual slices."""

    result: LtsRunResult
    slices: tuple[MaterializedSlice, ...]


def run_lts_transition_materialized(
    *,
    purposes_path: Path,
    positions_path: Path,
    transactions_path: Path,
    nav_root: Path,
    purpose_summaries_path: Path,
    fund_scope_path: Path,
    as_of: date | None = None,
) -> MaterializedLtsRunResult:
    """Run LTS and materialize every source mapping into auditable slices.

    The existing runner remains backward-compatible. This explicit entry point
    prevents callers from accidentally treating the unsplit Slice-1 bridge as
    the final ownership representation.
    """
    result = run_lts_transition(
        purposes_path=purposes_path,
        positions_path=positions_path,
        transactions_path=transactions_path,
        nav_root=nav_root,
        purpose_summaries_path=purpose_summaries_path,
        fund_scope_path=fund_scope_path,
        as_of=as_of,
    )
    slices = materialize_transition_slices(list(result.positions), result.plan)
    return MaterializedLtsRunResult(result=result, slices=slices)


__all__ = ["MaterializedLtsRunResult", "run_lts_transition_materialized"]
