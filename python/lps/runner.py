"""Reprice the LPS book at an as-of date, then reconcile transition orders."""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path

from lps.nav_engine import ensure_nav_coverage
from lps.position_persistence import read_positions
from lps.positions import Position
from lps.reconciliation import (
    DEFAULT_MANIFEST_PATH,
    DEFAULT_POSITIONS_PATH,
    DEFAULT_TRANSACTIONS_PATH,
    reconcile,
)
from lps.transaction_persistence import read_transactions
from lps.valuator import reprice_position_file

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
NAV_DIR = DATA_ROOT / "nav"
SETTLEMENT_MAPPING_PATH = DATA_ROOT / "lps" / "settlement_mapping.csv"


def _ledger_counts(positions: list[Position]) -> tuple[int, int]:
    holdings = {
        (position.id.investor, position.id.folio, position.id.isin)
        for position in positions
    }
    active_slices = sum(1 for position in positions if position.units > Decimal("0"))
    return len(holdings), active_slices


def run(as_of: date) -> None:
    """Fetch NAV coverage, reprice the book, then reconcile settlements."""
    read_transactions(DEFAULT_TRANSACTIONS_PATH)
    current = read_positions(DEFAULT_POSITIONS_PATH)
    isins = list(
        dict.fromkeys(position.id.isin for position in current if position.units != 0)
    )
    ensure_nav_coverage(as_of=as_of, isins=isins, data_root=DATA_ROOT)
    reprice_position_file(DEFAULT_POSITIONS_PATH, as_of=as_of, nav_dir=NAV_DIR)
    result = reconcile(
        manifest_path=DEFAULT_MANIFEST_PATH,
        transactions_path=DEFAULT_TRANSACTIONS_PATH,
        positions_path=DEFAULT_POSITIONS_PATH,
        settlement_mapping_path=SETTLEMENT_MAPPING_PATH,
    )
    positions = read_positions(DEFAULT_POSITIONS_PATH)
    holdings, active_slices = _ledger_counts(positions)
    book = sum(
        (position.market_value or Decimal("0") for position in positions if position.units != 0),
        Decimal("0"),
    )

    print("LPS valuation and reconciliation")
    print(f"Valuation as of: {as_of.isoformat()}")
    print("Position ledger")
    print(f"  Holdings: {holdings}")
    print(f"  Active slices: {active_slices}")
    print(f"  Market value: {book}")
    print("Transition orders")
    print(f"  Pending: {result.pending}")
    print(f"  Fulfilled: {result.fulfilled}")
    print(f"  Settled: {result.settled}")
    print(f"Last reconciliation as of: {result.as_of if result.manifest_present else 'unavailable'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    run(args.as_of)


if __name__ == "__main__":
    main()


__all__ = ["main", "run"]
