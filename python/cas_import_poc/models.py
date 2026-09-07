"""CAS import boundary models and compatibility exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from lps.positions import Position, PositionId


@dataclass(frozen=True)
class Transaction:
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
class ReconciliationResult:
    """Scheme-level unit-balance reconciliation result."""

    opening_units: Decimal
    computed_closing_units: Decimal
    printed_closing_units: Decimal

    @property
    def passed(self) -> bool:
        return self.computed_closing_units == self.printed_closing_units


__all__ = [
    "Transaction",
    "PositionId",
    "Position",
    "ReconciliationResult",
]
