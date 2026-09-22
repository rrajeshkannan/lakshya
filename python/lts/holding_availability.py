"""Reviewer-facing availability of factual holding capital.

This module is analytical only. It does not approve, execute, or persist a
transition. It preserves every remaining acquisition lot and identifies
ELSS-locked lots with their future availability date and retention reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .holding_constraints import HoldingConstraintAnalysis, LotTaxAnalysis
from lps.positions import PositionId

ZERO = Decimal("0")
ELSS_LOCK_IN_REASON = "ELSS_LOCK_IN"


@dataclass(frozen=True)
class LotAvailability:
    """Reviewer-facing availability detail for one remaining lot."""

    acquired_on: date
    units: Decimal
    current_value: Decimal | None
    availability_status: str
    locked_until: date | None
    retention_reason: str | None


@dataclass(frozen=True)
class LockedLotAvailability:
    """Backward-compatible reviewer-facing detail for one locked lot."""

    acquired_on: date
    units: Decimal
    current_value: Decimal | None
    locked_until: date

    @property
    def retention_reason(self) -> str:
        return ELSS_LOCK_IN_REASON


@dataclass(frozen=True)
class HoldingAvailability:
    """Unlocked summary plus complete lot-wise availability evidence."""

    holding_id: PositionId
    as_of: date
    unlocked_units: Decimal
    unlocked_value: Decimal | None
    unlocked_lot_count: int
    locked_lots: tuple[LockedLotAvailability, ...]
    lots: tuple[LotAvailability, ...] = ()

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
    """Summarize availability while retaining every lot as durable evidence.

    A lot without an ELSS lock-in date, or whose lock-in date has passed, is
    treated as available. A currently locked ELSS lot receives the explicit
    retention reason ``ELSS_LOCK_IN``. No other retention or tax policy is
    inferred here.
    """
    unlocked_lots: list[LotTaxAnalysis] = []
    locked_lots: list[LockedLotAvailability] = []
    lot_records: list[LotAvailability] = []

    for lot in analysis.lots:
        locked = _is_locked(lot, analysis.as_of)
        if locked:
            assert lot.elss_locked_until is not None
            locked_lots.append(
                LockedLotAvailability(
                    acquired_on=lot.acquired_on,
                    units=lot.units,
                    current_value=lot.current_value,
                    locked_until=lot.elss_locked_until,
                )
            )
            lot_records.append(
                LotAvailability(
                    acquired_on=lot.acquired_on,
                    units=lot.units,
                    current_value=lot.current_value,
                    availability_status="LOCKED",
                    locked_until=lot.elss_locked_until,
                    retention_reason=ELSS_LOCK_IN_REASON,
                )
            )
        else:
            unlocked_lots.append(lot)
            lot_records.append(
                LotAvailability(
                    acquired_on=lot.acquired_on,
                    units=lot.units,
                    current_value=lot.current_value,
                    availability_status="AVAILABLE",
                    locked_until=None,
                    retention_reason=None,
                )
            )

    return HoldingAvailability(
        holding_id=analysis.holding_id,
        as_of=analysis.as_of,
        unlocked_units=sum((lot.units for lot in unlocked_lots), ZERO),
        unlocked_value=_sum_known_values([lot.current_value for lot in unlocked_lots]),
        unlocked_lot_count=len(unlocked_lots),
        locked_lots=tuple(locked_lots),
        lots=tuple(lot_records),
    )


__all__ = [
    "ELSS_LOCK_IN_REASON",
    "HoldingAvailability",
    "LockedLotAvailability",
    "LotAvailability",
    "summarize_holding_availability",
]
