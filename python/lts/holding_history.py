"""Holding history derived from LTS transaction evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from lps.transactions import Transaction
from .position_bridge import LtsPositionId
from .physical_transaction_history import transactions_for_holding


@dataclass(frozen=True)
class HoldingHistory:
    """Minimal historical facts about one holding."""

    transaction_count: int
    first_transaction_date: date | None
    last_transaction_date: date | None


def holding_history(
    transactions: list[Transaction] | tuple[Transaction, ...],
    position_id: LtsPositionId,
) -> HoldingHistory:
    """Summarize transaction dates for the holding behind a Slice.

    This is descriptive evidence only. It does not interpret transaction
    dates as acquisition dates, holding periods, tax lots, or constraints.
    """
    history = transactions_for_holding(transactions, position_id)

    return HoldingHistory(
        transaction_count=len(history),
        first_transaction_date=history[0].transaction_date if history else None,
        last_transaction_date=history[-1].transaction_date if history else None,
    )


__all__ = ["HoldingHistory", "holding_history"]
