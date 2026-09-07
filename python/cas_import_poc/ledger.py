"""Persistence for Lakshya's family-wide transaction ledger."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from .models import Transaction


TRANSACTION_FIELDS = (
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


def write_ledger(path: Path, transactions: list[Transaction]) -> None:
    """Write the family-wide transaction collection as a simple CSV ledger."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        transactions,
        key=lambda transaction: (
            transaction.transaction_date,
            transaction.investor,
            transaction.folio,
            transaction.isin,
            transaction.event_type,
            transaction.source_description,
        ),
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRANSACTION_FIELDS)
        writer.writeheader()
        for transaction in ordered:
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


def read_ledger(path: Path) -> list[Transaction]:
    """Read the family-wide persisted transaction collection."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != TRANSACTION_FIELDS:
            raise ValueError("Transactions file has an unexpected column layout.")

        return [
            Transaction(
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
