"""First-class factual Position model owned by LPS."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cas_import_poc.models import Transaction


@dataclass(frozen=True)
class PositionId:
    """Stable identity for a Position."""

    investor: str
    folio: str
    isin: str


@dataclass(frozen=True)
class Position:
    """Factual Position reconstructed from transaction history.

    NAV and market value are populated when the Position is valued for an
    LPS review run. A Position reconstructed directly from transactions has
    those derived valuation fields unset.
    """

    id: PositionId
    units: Decimal
    nav: Decimal | None = None
    market_value: Decimal | None = None


def reconstruct_positions(
    transactions: list[Transaction],
) -> list[Position]:
    """Group transactions by Position identity and derive net units held."""
    from collections import defaultdict

    units_by_id: dict[PositionId, Decimal] = defaultdict(lambda: Decimal("0"))

    for transaction in transactions:
        position_id = PositionId(
            investor=transaction.investor,
            folio=transaction.folio,
            isin=transaction.isin,
        )
        if transaction.units is not None:
            units_by_id[position_id] += transaction.units

    return [
        Position(id=position_id, units=units)
        for position_id, units in sorted(
            units_by_id.items(),
            key=lambda item: (
                item[0].investor,
                item[0].folio,
                item[0].isin,
            ),
        )
    ]


__all__ = ["PositionId", "Position", "reconstruct_positions"]
