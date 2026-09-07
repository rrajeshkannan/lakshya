"""Valuation of active LPS Positions at an observation date."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from .current_state import CurrentState
from .nav_evidence import NavEvidenceStore


@dataclass(frozen=True)
class PositionValuation:
    """Market-value snapshot for one active Position."""

    current_state: CurrentState
    valuation_as_of_date: date
    nav_observation_date: date
    nav: Decimal
    market_value: Decimal


def value_position(
    current_state: CurrentState,
    nav_store: NavEvidenceStore,
    valuation_as_of_date: date,
) -> PositionValuation | None:
    """Value one Position using the applicable NAV on or before the date.

    Zero-unit historical Positions are retained in Current State but are not
    part of active CURRENT, so they return no valuation.
    """
    units = current_state.position.units
    if units == 0:
        return None

    observation_date, nav = nav_store.as_of(valuation_as_of_date)
    nav_decimal = Decimal(str(nav))

    return PositionValuation(
        current_state=current_state,
        valuation_as_of_date=valuation_as_of_date,
        nav_observation_date=observation_date.date(),
        nav=nav_decimal,
        market_value=units * nav_decimal,
    )


def build_current(
    current_states: list[CurrentState],
    nav_stores: Mapping[str, NavEvidenceStore],
    valuation_as_of_date: date,
) -> list[PositionValuation]:
    """Build the active CURRENT valuation snapshot for all Positions."""
    valuations = []

    for state in current_states:
        if state.position.units == 0:
            continue

        isin = state.position.key.isin
        try:
            store = nav_stores[isin]
        except KeyError as exc:
            raise KeyError(f"No NAV evidence store for ISIN {isin}") from exc

        valuation = value_position(state, store, valuation_as_of_date)
        if valuation is not None:
            valuations.append(valuation)

    return valuations


def current_total(valuations: list[PositionValuation]) -> Decimal:
    """Return total market value represented by an active CURRENT snapshot."""
    return sum(
        (valuation.market_value for valuation in valuations),
        Decimal("0"),
    )
