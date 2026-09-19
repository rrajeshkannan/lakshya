"""Acquisition transaction projection for LTS.

This module identifies transaction records that increase units in a holding.
It does not construct acquisition lots or interpret tax/holding-period rules.
"""

from __future__ import annotations

from lps.transactions import Transaction
from .position_bridge import LtsPositionId
from .physical_transaction_history import transactions_for_holding


ACQUISITION_EVENT_TYPES = frozenset({"Purchase", "SIP", "Switch In"})


def acquisition_transactions_for_holding(
    transactions: list[Transaction] | tuple[Transaction, ...],
    position_id: LtsPositionId,
) -> tuple[Transaction, ...]:
    """Return unit-acquiring transaction records for a holding.

    Event-type membership is deliberately explicit and narrow. The returned
    objects are the original Transactions; no lots or tax interpretation is
    created here.
    """
    return tuple(
        transaction
        for transaction in transactions_for_holding(transactions, position_id)
        if transaction.event_type in ACQUISITION_EVENT_TYPES
    )


__all__ = ["ACQUISITION_EVENT_TYPES", "acquisition_transactions_for_holding"]
