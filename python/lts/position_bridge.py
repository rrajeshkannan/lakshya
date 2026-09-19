"""Temporary LPS -> LTS Position compatibility bridge.

LPS currently exposes the pre-Slice Position contract. LTS is moving toward
its own Position semantics:

    Investor + Folio + ISIN + Slice

This bridge projects each current LPS Position into the simplest valid
Slice-based representation: Slice-1 at 100%. It is transient and is not
authoritative LPS state. The bridge can be removed once LPS adopts the
Slice-based Position contract natively.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from lps.positions import Position


ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")


@dataclass(frozen=True)
class LtsPositionId:
    """Identity of a Position inside the LTS model."""

    investor: str
    folio: str
    isin: str
    slice: str


@dataclass(frozen=True)
class LtsPosition:
    """LTS-facing Position projected from current LPS state."""

    id: LtsPositionId
    units: Decimal
    nav: Decimal | None = None
    market_value: Decimal | None = None
    purpose: str | None = None
    percentage: Decimal = Decimal("100")


def validate_slice_percentages(positions: list[LtsPosition]) -> None:
    """Validate the virtual Slice contract for each physical holding.

    A physical Investor + Folio + ISIN may be represented by multiple virtual
    LTS Positions, but their percentages must sum to exactly 100%. Each Slice
    identity must also be unique.
    """
    seen: set[LtsPositionId] = set()
    totals: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: ZERO)

    for position in positions:
        if position.id in seen:
            raise ValueError(f"Duplicate LTS Position identity: {position.id}")
        seen.add(position.id)

        if not position.percentage.is_finite() or not ZERO <= position.percentage <= ONE_HUNDRED:
            raise ValueError(
                f"Position percentage must be finite and between 0 and 100: "
                f"{position.id} -> {position.percentage}"
            )

        physical_key = (position.id.investor, position.id.folio, position.id.isin)
        totals[physical_key] += position.percentage

    invalid = {key: total for key, total in totals.items() if total != ONE_HUNDRED}
    if invalid:
        raise ValueError(
            "Slice percentages must sum to exactly 100% for every "
            f"Investor + Folio + ISIN: {invalid}"
        )


def bridge_positions(positions: list[Position]) -> list[LtsPosition]:
    """Project current LPS Positions into the Slice-based LTS model.

    Every legacy LPS Position becomes one Slice-1 carrying 100% of its
    economic value. No LPS state is changed.
    """
    return [
        LtsPosition(
            id=LtsPositionId(
                investor=position.id.investor,
                folio=position.id.folio,
                isin=position.id.isin,
                slice="Slice-1",
            ),
            units=position.units,
            nav=position.nav,
            market_value=position.market_value,
            purpose=position.purpose,
        )
        for position in positions
    ]


__all__ = ["LtsPositionId", "LtsPosition", "bridge_positions", "validate_slice_percentages"]
