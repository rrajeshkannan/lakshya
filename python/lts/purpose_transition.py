"""Purpose-owned pre-tax CURRENT -> TARGET transition planning.

This module is analytical only. It preserves LFS Formation Intent, keeps
capital owned by its Purpose, and separates immediately actionable excess
from excess that is currently locked. It does not calculate tax, execute
transactions, or mutate LPS state.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .formation_intent import TargetFormation
from .position_bridge import LtsPosition, LtsPositionId, validate_slice_percentages
from .purpose_allocation import validate_purpose_target_allocation

ZERO = Decimal("0")


class TransitionDisposition(str, Enum):
    RETAIN = "RETAIN"
    REDEEM = "REDEEM"
    REDEEM_LOCKED = "REDEEM_LOCKED"
    INVEST = "INVEST"


@dataclass(frozen=True)
class PurposeTransitionRow:
    """One Purpose-owned source or destination transition requirement."""

    purpose: str
    source_position_id: LtsPositionId | None
    source_isin: str | None
    destination_isin: str
    disposition: TransitionDisposition
    amount: Decimal
    locked: bool = False


@dataclass(frozen=True)
class PurposeTransitionPlan:
    """Pre-tax transition requirements, grouped by Purpose."""

    rows: tuple[PurposeTransitionRow, ...]

    @property
    def total_amount(self) -> Decimal:
        return sum((row.amount for row in self.rows), ZERO)


def build_purpose_transition_plan(
    positions: list[LtsPosition],
    formation: TargetFormation,
    *,
    locked_position_ids: set[LtsPositionId] | None = None,
) -> PurposeTransitionPlan:
    """Build a deterministic Purpose-owned pre-tax transition plan.

    For each Purpose and ISIN, existing capital is retained up to the target
    amount. Excess in selected or non-selected ISINs becomes redemption
    capacity. A locked source position is classified as REDEEM_LOCKED rather
    than silently treated as immediately actionable. Target gaps become
    INVEST rows owned by the same Purpose.

    The function intentionally does not estimate tax, choose tax treatment,
    or create broker/AMC transaction instructions.
    """
    validate_slice_percentages(positions)
    validate_purpose_target_allocation(formation)
    locked = locked_position_ids or set()

    target: dict[tuple[str, str], Decimal] = {}
    for row in formation.rows:
        target[(row.purpose, row.isin)] = target.get((row.purpose, row.isin), ZERO) + row.target_value

    current: dict[tuple[str, str], Decimal] = {}
    for position in positions:
        if position.purpose is None:
            continue
        if position.market_value is None:
            raise ValueError(f"Cannot plan transition for unvalued Position {position.id}.")
        if position.market_value < ZERO:
            raise ValueError(f"Position market value cannot be negative: {position.id}.")
        value = position.market_value * position.percentage / Decimal("100")
        key = (position.purpose, position.id.isin)
        current[key] = current.get(key, ZERO) + value

    matched_remaining = {key: min(value, target.get(key, ZERO)) for key, value in current.items()}
    rows: list[PurposeTransitionRow] = []

    for position in sorted(positions, key=lambda item: (item.purpose or "", item.id.investor, item.id.folio, item.id.isin, item.id.slice)):
        if position.purpose is None:
            continue
        value = position.market_value * position.percentage / Decimal("100") if position.market_value is not None else ZERO
        key = (position.purpose, position.id.isin)
        retain = min(value, matched_remaining.get(key, ZERO))
        matched_remaining[key] = matched_remaining.get(key, ZERO) - retain
        excess = value - retain
        if retain > ZERO:
            rows.append(PurposeTransitionRow(
                purpose=position.purpose,
                source_position_id=position.id,
                source_isin=position.id.isin,
                destination_isin=position.id.isin,
                disposition=TransitionDisposition.RETAIN,
                amount=retain,
            ))
        if excess > ZERO:
            is_locked = position.id in locked
            rows.append(PurposeTransitionRow(
                purpose=position.purpose,
                source_position_id=position.id,
                source_isin=position.id.isin,
                destination_isin=position.id.isin,
                disposition=(TransitionDisposition.REDEEM_LOCKED if is_locked else TransitionDisposition.REDEEM),
                amount=excess,
                locked=is_locked,
            ))

    keys = sorted(set(target) | set(current))
    for purpose, isin in keys:
        gap = target.get((purpose, isin), ZERO) - min(current.get((purpose, isin), ZERO), target.get((purpose, isin), ZERO))
        if gap > ZERO:
            rows.append(PurposeTransitionRow(
                purpose=purpose,
                source_position_id=None,
                source_isin=None,
                destination_isin=isin,
                disposition=TransitionDisposition.INVEST,
                amount=gap,
            ))

    return PurposeTransitionPlan(rows=tuple(rows))


__all__ = [
    "PurposeTransitionPlan",
    "PurposeTransitionRow",
    "TransitionDisposition",
    "build_purpose_transition_plan",
]
