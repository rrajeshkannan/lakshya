"""LPS projection of accepted Position capital by Purpose."""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path


POSITION_FIELDS = {
    "investor",
    "folio",
    "isin",
    "units",
    "nav",
    "market_value",
    "purpose",
}


def purpose_capital_from_positions(path: Path) -> dict[str, float]:
    """Aggregate valued Positions into Purpose capital.

    Only established Positions with an accepted Purpose and market value
    contribute. Unattributed Positions remain visible to LPS but are not
    silently assigned to a Purpose.
    """
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or ()) != POSITION_FIELDS:
            raise ValueError("Positions file has an unexpected column layout.")

        result: dict[str, Decimal] = {}
        for row in reader:
            purpose = row["purpose"].strip()
            market_value = row["market_value"].strip()
            if not purpose:
                continue
            if not market_value:
                raise ValueError(
                    f"Position assigned to Purpose {purpose!r} has no market value: "
                    f"{row['investor']}/{row['folio']}/{row['isin']}"
                )
            value = Decimal(market_value)
            if not value.is_finite() or value < 0:
                raise ValueError(f"Invalid market value for Position: {row}")
            result[purpose] = result.get(purpose, Decimal("0")) + value

    return {purpose: float(value) for purpose, value in sorted(result.items())}


__all__ = ["purpose_capital_from_positions"]
