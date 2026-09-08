"""Accepted Position-to-Purpose attribution owned by LPS."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .positions import Position, PositionId


ATTRIBUTION_FIELDS = ("investor", "folio", "isin", "purpose")


@dataclass(frozen=True)
class PositionPurposeAttribution:
    """Accepted family attribution for one established Position."""

    position_id: PositionId
    purpose: str

    def __post_init__(self) -> None:
        if not self.position_id.investor.strip():
            raise ValueError("Position attribution requires an investor")
        if not self.position_id.folio.strip():
            raise ValueError("Position attribution requires a folio")
        if not self.position_id.isin.strip():
            raise ValueError("Position attribution requires an ISIN")
        if not self.purpose.strip():
            raise ValueError("Position attribution requires a Purpose")


def validate_attributions(
    positions: list[Position],
    attributions: list[PositionPurposeAttribution],
) -> None:
    """Validate an accepted attribution set against established Positions.

    Every attributed Position must exist exactly once. Positions may remain
    unattributed while factual Positions are being reviewed; this function
    therefore does not require complete coverage.
    """
    position_ids = {position.id for position in positions}
    seen: set[PositionId] = set()
    for attribution in attributions:
        position_id = attribution.position_id
        if position_id not in position_ids:
            raise ValueError(
                "Purpose attribution references an unknown Position: "
                f"{position_id!r}"
            )
        if position_id in seen:
            raise ValueError(f"Duplicate Purpose attribution for Position: {position_id!r}")
        seen.add(position_id)


def write_attributions(
    path: Path,
    attributions: list[PositionPurposeAttribution],
) -> None:
    """Persist accepted Position-to-Purpose attributions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        attributions,
        key=lambda item: (
            item.position_id.investor,
            item.position_id.folio,
            item.position_id.isin,
        ),
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ATTRIBUTION_FIELDS)
        writer.writeheader()
        for attribution in ordered:
            writer.writerow(
                {
                    "investor": attribution.position_id.investor,
                    "folio": attribution.position_id.folio,
                    "isin": attribution.position_id.isin,
                    "purpose": attribution.purpose,
                }
            )


def read_attributions(path: Path) -> list[PositionPurposeAttribution]:
    """Read accepted Position-to-Purpose attributions."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != ATTRIBUTION_FIELDS:
            raise ValueError("Purpose attribution file has an unexpected column layout.")

        return [
            PositionPurposeAttribution(
                position_id=PositionId(
                    investor=row["investor"],
                    folio=row["folio"],
                    isin=row["isin"],
                ),
                purpose=row["purpose"],
            )
            for row in reader
        ]


def purpose_by_position(
    attributions: list[PositionPurposeAttribution],
) -> dict[PositionId, str]:
    """Return the accepted one-Purpose-per-Position mapping."""
    result: dict[PositionId, str] = {}
    for attribution in attributions:
        if attribution.position_id in result:
            raise ValueError(
                f"Duplicate Purpose attribution for Position: {attribution.position_id!r}"
            )
        result[attribution.position_id] = attribution.purpose
    return result


__all__ = [
    "ATTRIBUTION_FIELDS",
    "PositionPurposeAttribution",
    "validate_attributions",
    "write_attributions",
    "read_attributions",
    "purpose_by_position",
]
