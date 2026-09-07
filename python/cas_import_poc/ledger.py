"""Persistence for Lakshya's parser-independent canonical transaction ledger."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from .models import CanonicalTransaction


LEDGER_FIELDS = (
    "transaction_date",
    "event_type",
    "investor",
    "folio",
    "isin",
    "units",
    "amount",
    "price",
    "source_description",
)


def write_ledger(path: Path, transactions: list[CanonicalTransaction]) -> None:
    """Write canonical transactions as a simple, exact CSV ledger."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_FIELDS)
        writer.writeheader()
        for transaction in transactions:
            writer.writerow(
                {
                    "transaction_date": transaction.transaction_date.isoformat(),
                    "event_type": transaction.event_type,
                    "investor": transaction.investor,
                    "folio": transaction.folio,
                    "isin": transaction.isin,
                    "units": _text(transaction.units),
                    "amount": _text(transaction.amount),
                    "price": _text(transaction.price),
                    "source_description": transaction.source_description,
                }
            )


def read_ledger(path: Path) -> list[CanonicalTransaction]:
    """Read a persisted canonical transaction ledger."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != LEDGER_FIELDS:
            raise ValueError("Canonical ledger has an unexpected column layout.")

        return [
            CanonicalTransaction(
                transaction_date=date.fromisoformat(row["transaction_date"]),
                event_type=row["event_type"],
                investor=row["investor"],
                folio=row["folio"],
                isin=row["isin"],
                units=_decimal(row["units"]),
                amount=_decimal(row["amount"]),
                price=_decimal(row["price"]),
                source_description=row["source_description"],
            )
            for row in reader
        ]


def _text(value: Decimal | None) -> str:
    return "" if value is None else str(value)


def _decimal(value: str) -> Decimal | None:
    return None if value == "" else Decimal(value)
