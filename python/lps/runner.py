"""Reconcile the LPS transition manifest and report the position ledger."""

from __future__ import annotations

from decimal import Decimal

from .position_persistence import read_positions
from .positions import Position
from .reconciliation import (
    DEFAULT_MANIFEST_PATH,
    DEFAULT_POSITIONS_PATH,
    DEFAULT_TRANSACTIONS_PATH,
    reconcile,
)
from .transaction_persistence import read_transactions


def _ledger_counts(positions: list[Position]) -> tuple[int, int]:
    holdings = {
        (position.id.investor, position.id.folio, position.id.isin)
        for position in positions
    }
    active_slices = sum(1 for position in positions if position.units > Decimal("0"))
    return len(holdings), active_slices


def main() -> None:
    read_transactions(DEFAULT_TRANSACTIONS_PATH)
    result = reconcile(
        manifest_path=DEFAULT_MANIFEST_PATH,
        transactions_path=DEFAULT_TRANSACTIONS_PATH,
        positions_path=DEFAULT_POSITIONS_PATH,
    )
    positions = read_positions(DEFAULT_POSITIONS_PATH)
    holdings, active_slices = _ledger_counts(positions)
    as_of = result.as_of if result.manifest_present else "unavailable"

    print("LPS reconciliation")
    print("Position ledger")
    print(f"  Holdings: {holdings}")
    print(f"  Active slices: {active_slices}")
    print("Transition orders")
    print(f"  Pending: {result.pending}")
    print(f"  Fulfilled: {result.fulfilled}")
    print(f"Last reconciliation as of: {as_of}")


if __name__ == "__main__":
    main()


__all__ = ["main"]
