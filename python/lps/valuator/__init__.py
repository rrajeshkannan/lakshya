"""Reprice LPS positions from cached NAV evidence.

Market value is units times the latest stored NAV on or before the
requested date. The valuator does not fetch NAV and does not settle orders.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from lps.nav_evidence import NavEvidenceStore
from lps.position_persistence import read_positions, write_positions
from lps.positions import Position
from lps.valuation import value_positions


def reprice_positions(
    positions: list[Position],
    *,
    as_of: date,
    nav_dir: Path,
) -> list[Position]:
    """Return positions priced at ``as_of`` from ``nav_dir``."""
    active_isins = list(
        dict.fromkeys(position.id.isin for position in positions if position.units != 0)
    )
    stores = {
        isin: NavEvidenceStore(Path(nav_dir) / f"{isin}.json")
        for isin in active_isins
    }
    return value_positions(positions, stores, as_of)


def reprice_position_file(
    path: Path,
    *,
    as_of: date,
    nav_dir: Path,
) -> list[Position]:
    """Read, reprice, and write the position book."""
    priced = reprice_positions(read_positions(path), as_of=as_of, nav_dir=nav_dir)
    write_positions(path, priced)
    return priced


__all__ = ["reprice_positions", "reprice_position_file"]
