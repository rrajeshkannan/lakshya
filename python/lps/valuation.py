"""Valuation of LPS Positions at an observation date."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Mapping

from .nav_evidence import NavEvidenceStore
from .positions import Position


def value_position(
    position: Position,
    nav_store: NavEvidenceStore,
    valuation_as_of_date: date,
) -> Position:
    """Return the Position enriched with its applicable NAV and market value."""
    if position.units == 0:
        return position

    _observation_date, nav = nav_store.as_of(valuation_as_of_date)
    nav_decimal = Decimal(str(nav))

    return Position(
        id=position.id,
        units=position.units,
        nav=nav_decimal,
        market_value=position.units * nav_decimal,
    )


def value_positions(
    positions: list[Position],
    nav_stores: Mapping[str, NavEvidenceStore],
    valuation_as_of_date: date,
) -> list[Position]:
    """Value every Position, retaining zero-unit historical Positions."""
    valued = []
    for position in positions:
        if position.units == 0:
            valued.append(position)
            continue

        isin = position.id.isin
        try:
            store = nav_stores[isin]
        except KeyError as exc:
            raise KeyError(f"No NAV evidence store for ISIN {isin}") from exc
        valued.append(value_position(position, store, valuation_as_of_date))

    return valued


def total_market_value(positions: list[Position]) -> Decimal:
    """Return total market value represented by active Positions."""
    return sum(
        (
            position.market_value or Decimal("0")
            for position in positions
            if position.units != 0
        ),
        Decimal("0"),
    )


__all__ = ["value_position", "value_positions", "total_market_value"]
