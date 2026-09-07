"""Build the LPS CURRENT valuation snapshot from persisted family evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from cas_import_poc.ledger import read_ledger
from lps.current_state import CurrentState, derive_current_state
from lps.nav_evidence import NavEvidenceStore
from lps.positions import reconstruct_positions
from lps.valuation import PositionValuation, build_current, current_total


@dataclass(frozen=True)
class CurrentSnapshot:
    """LPS valuation snapshot for one investor at one as-of date."""

    investor: str
    transaction_through_date: date
    valuation_as_of_date: date
    current_states: tuple[CurrentState, ...]
    valuations: tuple[PositionValuation, ...]
    total_market_value: Decimal


def build_current_snapshot(
    *,
    investor: str,
    ledger_path: Path,
    nav_root: Path,
    valuation_as_of_date: date,
) -> CurrentSnapshot:
    """Build CURRENT from the persisted canonical ledger and NAV evidence."""
    transactions = read_ledger(ledger_path)
    if not transactions:
        raise ValueError("Canonical ledger contains no transactions.")

    investors = {transaction.investor for transaction in transactions}
    if investors != {investor}:
        raise ValueError(
            f"Canonical ledger investor mismatch: expected {investor!r}, "
            f"found {sorted(investors)!r}."
        )

    transaction_through_date = max(
        transaction.transaction_date for transaction in transactions
    )

    positions = reconstruct_positions(transactions)
    current_states = derive_current_state(positions)

    isins = {state.position.key.isin for state in current_states if state.units != 0}
    nav_stores = {
        isin: NavEvidenceStore(nav_root / f"{isin}.json")
        for isin in isins
    }
    valuations = build_current(
        current_states,
        nav_stores,
        valuation_as_of_date,
    )

    return CurrentSnapshot(
        investor=investor,
        transaction_through_date=transaction_through_date,
        valuation_as_of_date=valuation_as_of_date,
        current_states=tuple(current_states),
        valuations=tuple(valuations),
        total_market_value=current_total(valuations),
    )


__all__ = ["CurrentSnapshot", "build_current_snapshot"]
