"""Small, parser-independent CAS import POC domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class CanonicalTransaction:
    """Normalized actual transaction retained by LPS."""

    transaction_date: date
    event_type: str
    investor: str
    folio: str
    isin: str
    units: Optional[Decimal]
    amount: Optional[Decimal]
    price: Optional[Decimal]
    source_description: str


@dataclass(frozen=True)
class PositionKey:
    """Stable ownership identity for the POC."""

    investor: str
    folio: str
    isin: str


@dataclass(frozen=True)
class PositionObservation:
    """Current position observation for one Position."""

    key: PositionKey
    units: Decimal
    nav: Decimal
    market_value: Decimal
    valuation_as_of_date: date


@dataclass(frozen=True)
class ReconciliationResult:
    """Scheme-level unit-balance reconciliation result."""

    opening_units: Decimal
    computed_closing_units: Decimal
    printed_closing_units: Decimal

    @property
    def passed(self) -> bool:
        return self.computed_closing_units == self.printed_closing_units
