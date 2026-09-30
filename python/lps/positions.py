"""First-class factual Position model owned by LPS."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .transactions import Transaction


PRIMARY_SLICE = "slice-1"
# LTS still names the primary virtual slice ``Slice-1``. Both names identify
# that same primary slice for set membership with an LTS position id.
_PRIMARY_SLICE_NAMES = frozenset({PRIMARY_SLICE, "Slice-1"})


@dataclass(frozen=True)
class PositionId:
    """Stable identity for a Position: investor|folio|isin|slice."""

    investor: str
    folio: str
    isin: str
    slice: str = PRIMARY_SLICE

    def __post_init__(self) -> None:
        if not self.slice.strip():
            raise ValueError("Position slice is required.")

    def __hash__(self) -> int:
        if self.slice in _PRIMARY_SLICE_NAMES:
            return hash((self.investor, self.folio, self.isin))
        return hash((self.investor, self.folio, self.isin, self.slice))

    @property
    def key(self) -> str:
        """Canonical 4-part identity."""
        return f"{self.investor}|{self.folio}|{self.isin}|{self.slice}"


@dataclass(frozen=True)
class Position:
    """Established factual Position owned by LPS.

    Units are reconstructed from transaction history. NAV and market value
    are valuation observations. Purpose is an accepted human attribution and
    therefore belongs to the established Position state.
    """

    id: PositionId
    units: Decimal
    nav: Decimal | None = None
    market_value: Decimal | None = None
    purpose: str | None = None


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
                item[0].slice,
            ),
        )
    ]


__all__ = ["PRIMARY_SLICE", "PositionId", "Position", "reconstruct_positions"]
