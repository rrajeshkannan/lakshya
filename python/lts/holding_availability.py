"""Reviewer-facing availability of factual holding capital.

This module is analytical only. It does not approve, execute, or persist a
transition. It groups currently available units and keeps locked ELSS lots
visible individually with their future availability date.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .holding_constraints import HoldingConstraintAnalysis, LotTaxAnalysis
from lps.positions import PositionId

ZERO = Decimal("0")


@dataclass(frozen=True)
class LockedLotAvailability:
    """Reviewer-facing detail for one currently locked lot."""

    acquired_on: date
    units: Decimal
    current_value: Decimal | None
    locked_until: date


@dataclass(frozen=True)
class HoldingAvailability:
    """Unlocked summary plus lot-wise locked exposure for one holding."""

    holding_id: PositionId
    as_of: date
    unlocked_units: Decimal
    unlocked_value: Decimal | None
    unlocked_lot_count: int
    locked_lots: tuple[LockedLotAvailability, ...]

    @property
    def locked_units(self) -> Decimal:
        return sum((lot.units for lot in self.locked_lots), ZERO)

    @property
    def locked_value(self) -> Decimal | None:
        values = [lot.current_value for lot in self.locked_lots]
        if any(value is None for value in values):
            return None
        return sum(values, ZERO)


def _sum_known_values(values: list[Decimal | None]) -> Decimal | None:
    if any(value is None for value in values):
        return None
    return sum(values, ZERO)


def _is_locked(lot: LotTaxAnalysis, as_of: date) -> bool:
    return lot.elss_locked_until is not None and as_of < lot.elss_locked_until


def summarize_holding_availability(
    analysis: HoldingConstraintAnalysis,
) -> HoldingAvailability:
    """Summarize currently unlocked capital and retain locked lots individually.

    A lot without an ELSS lock-in date is treated as unlocked. This function
    consumes already-computed holding analysis and does not infer tax rules.
    """
    unlocked_lots: list[LotTaxAnalysis] = []
    locked_lots: list[LockedLotAvailability] = []

    for lot in analysis.lots:
        if _is_locked(lot, analysis.as_of):
            # The caller should only receive a locked lot when its lock date is
            # present; the guard keeps the type contract explicit.
            assert lot.elss_locked_until is not None
            locked_lots.append(
                LockedLotAvailability(
                    acquired_on=lot.acquired_on,
                    units=lot.units,
                    current_value=lot.current_value,
                    locked_until=lot.elss_locked_until,
                )
            )
        else:
            unlocked_lots.append(lot)

    return HoldingAvailability(
        holding_id=analysis.holding_id,
        as_of=analysis.as_of,
        unlocked_units=sum((lot.units for lot in unlocked_lots), ZERO),
        unlocked_value=_sum_known_values(
            [lot.current_value for lot in unlocked_lots]
        ),
        unlocked_lot_count=len(unlocked_lots),
        locked_lots=tuple(locked_lots),
    )


__all__ = [
    "HoldingAvailability",
    "LockedLotAvailability",
    "summarize_holding_availability",
]
