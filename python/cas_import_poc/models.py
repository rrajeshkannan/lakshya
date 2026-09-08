"""CAS import boundary models and compatibility exports."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from lps.positions import Position, PositionId
from lps.transactions import Transaction


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
