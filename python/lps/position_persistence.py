"""Persistence for LPS Positions."""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from .positions import PRIMARY_SLICE, Position, PositionId


LEGACY_POSITION_FIELDS = (
    "investor",
    "folio",
    "isin",
    "units",
    "nav",
    "market_value",
    "purpose",
)
POSITION_FIELDS = (
    "investor",
    "folio",
    "isin",
    "slice",
    "units",
    "nav",
    "market_value",
    "purpose",
)


def write_positions(path: Path, positions: list[Position]) -> None:
    """Write the complete Position collection as a simple CSV state file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=POSITION_FIELDS)
        writer.writeheader()
        for position in positions:
            writer.writerow(
                {
                    "investor": position.id.investor,
                    "folio": position.id.folio,
                    "isin": position.id.isin,
                    "slice": position.id.slice,
                    "units": str(position.units),
                    "nav": _text(position.nav),
                    "market_value": _text(position.market_value),
                    "purpose": _text(position.purpose),
                }
            )


def read_positions(path: Path) -> list[Position]:
    """Read a persisted Position collection."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        if fieldnames == POSITION_FIELDS:
            has_slice = True
        elif fieldnames == LEGACY_POSITION_FIELDS:
            has_slice = False
        else:
            raise ValueError("Positions file has an unexpected column layout.")

        positions: list[Position] = []
        for row in reader:
            slice_name = row["slice"].strip() if has_slice else PRIMARY_SLICE
            if not slice_name:
                raise ValueError(
                    "Position slice is required: "
                    f"{row['investor']}|{row['folio']}|{row['isin']}"
                )
            positions.append(
                Position(
                    id=PositionId(
                        investor=row["investor"],
                        folio=row["folio"],
                        isin=row["isin"],
                        slice=slice_name,
                    ),
                    units=Decimal(row["units"]),
                    nav=_decimal(row["nav"]),
                    market_value=_decimal(row["market_value"]),
                    purpose=row["purpose"] or None,
                )
            )
        return positions


def _text(value: Decimal | str | None) -> str:
    return "" if value is None else str(value)


def _decimal(value: str) -> Decimal | None:
    return None if value == "" else Decimal(value)


__all__ = [
    "LEGACY_POSITION_FIELDS",
    "POSITION_FIELDS",
    "write_positions",
    "read_positions",
]
