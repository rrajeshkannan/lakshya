"""Reconstruct factual Positions from canonical transaction history."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from cas_import_poc.models import CanonicalTransaction
from cas_import_poc.models import Position, PositionKey


def reconstruct_positions(
    transactions: list[CanonicalTransaction],
) -> list[Position]:
    """Group transactions by Position identity and derive net units held."""
    units_by_key: dict[PositionKey, Decimal] = defaultdict(lambda: Decimal("0"))

    for transaction in transactions:
        key = PositionKey(
            investor=transaction.investor,
            folio=transaction.folio,
            isin=transaction.isin,
        )
        if transaction.units is not None:
            units_by_key[key] += transaction.units

    return [
        Position(key=key, units=units)
        for key, units in sorted(
            units_by_key.items(),
            key=lambda item: (item[0].investor, item[0].folio, item[0].isin),
        )
    ]
