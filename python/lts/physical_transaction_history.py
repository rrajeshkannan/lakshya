"""Factual transaction history projection for LTS constraint analysis.

Transactions belong to the physical Investor + Folio + ISIN holding.
LTS Slices are virtual and therefore do not acquire separate transaction
histories.
"""

from __future__ import annotations

from lps.transactions import Transaction
from .position_bridge import LtsPositionId


def transactions_for_holding(
    transactions: list[Transaction] | tuple[Transaction, ...],
    position_id: LtsPositionId,
) -> tuple[Transaction, ...]:
    """Return factual transactions for the physical holding behind a Slice.

    The Slice component is deliberately ignored. No transaction is attributed
    to an individual Slice.
    """
    matching = [
        transaction
        for transaction in transactions
        if (
            transaction.investor == position_id.investor
            and transaction.folio == position_id.folio
            and transaction.isin == position_id.isin
        )
    ]
    return tuple(
        sorted(
            matching,
            key=lambda transaction: (
                transaction.transaction_date,
                transaction.event_type,
                transaction.source_description,
            ),
        )
    )


__all__ = ["transactions_for_holding"]
