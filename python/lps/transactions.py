"""First-class factual Transaction model owned by LPS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Transaction:
    """Normalized transaction retained by LPS as source-derived evidence."""

    transaction_date: date
    event_type: str
    investor: str
    folio: str
    isin: str
    units: Decimal | None
    amount: Decimal | None
    price: Decimal | None
    source_description: str


__all__ = ["Transaction"]
