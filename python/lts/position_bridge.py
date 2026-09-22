"""LPS -> LTS Position projection and explicit Slice ownership.

LTS owns a virtual Position identity:

    Investor + Folio + ISIN + Slice

The current LPS contract has no Slice ownership rows, so ``bridge_positions``
continues to provide a conservative one-to-one ``Slice-1`` projection.
``build_owned_positions`` is the explicit ownership boundary for a future
multi-purpose physical holding. It never invents ownership percentages:
callers must supply them and the validator requires each physical holding to
sum to exactly 100%.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from lps.positions import Position


ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
DEFAULT_SLICE = "Slice-1"


@dataclass(frozen=True, eq=False)
class LtsPositionId:
    """Identity of a Position inside the LTS model."""

    investor: str
    folio: str
    isin: str
    slice: str

    def __hash__(self) -> int:
        if self.slice == DEFAULT_SLICE:
            return hash((self.investor, self.folio, self.isin))
        return hash((self.investor, self.folio, self.isin, self.slice))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, LtsPositionId):
            return (
                self.investor,
                self.folio,
                self.isin,
                self.slice,
            ) == (
                other.investor,
                other.folio,
                other.isin,
                other.slice,
            )
        if self.slice != DEFAULT_SLICE:
            return False
        return (
            hasattr(other, "investor")
            and hasattr(other, "folio")
            and hasattr(other, "isin")
            and not hasattr(other, "slice")
            and (self.investor, self.folio, self.isin)
            == (other.investor, other.folio, other.isin)
        )


@dataclass(frozen=True)
class SliceOwnership:
    """One explicit ownership claim for a physical holding.

    ``percentage`` is the share of the physical holding attributed to this
    Slice. The underlying units and market value remain the physical holding's
    observed values on every virtual LTS Position; consumers must apply
    ``percentage`` exactly once when calculating attributed economics.
    """

    investor: str
    folio: str
    isin: str
    slice: str
    purpose: str | None
    percentage: Decimal
    source: str

    @property
    def physical_key(self) -> tuple[str, str, str]:
        return self.investor, self.folio, self.isin

    @property
    def position_id(self) -> LtsPositionId:
        return LtsPositionId(self.investor, self.folio, self.isin, self.slice)


@dataclass(frozen=True)
class LtsPosition:
    """LTS-facing Position with virtual Slice ownership metadata."""

    id: LtsPositionId
    units: Decimal
    nav: Decimal | None = None
    market_value: Decimal | None = None
    purpose: str | None = None
    percentage: Decimal = ONE_HUNDRED
    ownership_source: str = "LEGACY_POSITION_PURPOSE"


def _validate_percentage(percentage: Decimal, identity: object) -> None:
    if not percentage.is_finite() or not ZERO <= percentage <= ONE_HUNDRED:
        raise ValueError(
            "Position percentage must be finite and between 0 and 100: "
            f"{identity} -> {percentage}"
        )


def validate_slice_percentages(positions: list[LtsPosition]) -> None:
    """Validate Slice uniqueness and 100% ownership per physical holding."""
    seen: set[LtsPositionId] = set()
    totals: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: ZERO)

    for position in positions:
        if position.id in seen:
            raise ValueError(f"Duplicate LTS Position identity: {position.id}")
        seen.add(position.id)
        _validate_percentage(position.percentage, position.id)
        physical_key = (position.id.investor, position.id.folio, position.id.isin)
        totals[physical_key] += position.percentage

    invalid = {key: total for key, total in totals.items() if total != ONE_HUNDRED}
    if invalid:
        raise ValueError(
            "Slice percentages must sum to exactly 100% for every "
            f"Investor + Folio + ISIN: {invalid}"
        )


def _physical_key(position: Position) -> tuple[str, str, str]:
    return position.id.investor, position.id.folio, position.id.isin


def build_owned_positions(
    positions: list[Position],
    ownership: list[SliceOwnership],
) -> list[LtsPosition]:
    """Project physical LPS positions using explicit Slice ownership rows.

    Every source physical holding must have ownership rows, every ownership
    row must reference an existing holding, and each physical holding must
    total exactly 100%. The function preserves the observed physical units,
    NAV, and market value and attaches the ownership percentage for one-time
    economic attribution downstream.
    """
    source_by_key = {_physical_key(position): position for position in positions}
    if len(source_by_key) != len(positions):
        raise ValueError("Physical LPS Position identities must be unique.")

    ownership_by_key: dict[tuple[str, str, str], list[SliceOwnership]] = defaultdict(list)
    for row in ownership:
        if not row.source.strip():
            raise ValueError(f"Slice ownership source cannot be blank: {row}")
        _validate_percentage(row.percentage, row.position_id)
        if row.physical_key not in source_by_key:
            raise ValueError(f"Slice ownership references unknown holding: {row.physical_key}")
        ownership_by_key[row.physical_key].append(row)

    missing = sorted(set(source_by_key) - set(ownership_by_key))
    if missing:
        raise ValueError(f"Missing Slice ownership rows for physical holdings: {missing}")

    result: list[LtsPosition] = []
    for physical_key in sorted(source_by_key):
        source = source_by_key[physical_key]
        rows = ownership_by_key[physical_key]
        projected = [
            LtsPosition(
                id=row.position_id,
                units=source.units,
                nav=source.nav,
                market_value=source.market_value,
                purpose=row.purpose,
                percentage=row.percentage,
                ownership_source=row.source,
            )
            for row in rows
        ]
        validate_slice_percentages(projected)
        result.extend(projected)

    validate_slice_percentages(result)
    return result


def bridge_positions(positions: list[Position]) -> list[LtsPosition]:
    """Conservatively project current LPS Positions into Slice-1 at 100%."""
    return [
        LtsPosition(
            id=LtsPositionId(
                investor=position.id.investor,
                folio=position.id.folio,
                isin=position.id.isin,
                slice=DEFAULT_SLICE,
            ),
            units=position.units,
            nav=position.nav,
            market_value=position.market_value,
            purpose=position.purpose,
            ownership_source="LEGACY_POSITION_PURPOSE",
        )
        for position in positions
    ]


__all__ = [
    "DEFAULT_SLICE",
    "LtsPositionId",
    "SliceOwnership",
    "LtsPosition",
    "bridge_positions",
    "build_owned_positions",
    "validate_slice_percentages",
]
