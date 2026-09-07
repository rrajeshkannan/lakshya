"""Factual Position identity and reconstruction owned by LPS."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cas_import_poc.models import CanonicalTransaction


@dataclass(frozen=True)
class PositionKey:
    """Stable ownership identity for a Position."""

    investor: str
    folio: str
    isin: str


@dataclass(frozen=True)
class Position:
    """Factual Position reconstructed from canonical transaction history."""

    key: PositionKey
    units: Decimal


def reconstruct_positions(
    transactions: list[CanonicalTransaction],
) -> list[Position]:
    """Group transactions by Position identity and derive net units held."""
    from collections import defaultdict

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


__all__ = ["PositionKey", "Position", "reconstruct_positions"]
