"""Purpose-level reporting for conservation-balanced transition plans."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import TargetFormation
from .position_bridge import LtsPosition
from .purpose_transition import (
    PurposeTransitionPlan,
    TransitionSourceKind,
)

ZERO = Decimal("0")
TOLERANCE = Decimal("0.00000001")


@dataclass(frozen=True)
class PurposeTransitionReport:
    """Human-readable, Purpose-level summary of a transition plan."""

    purpose: str
    current_amount: Decimal
    target_amount: Decimal
    retained_amount: Decimal
    redemption_amount: Decimal
    locked_redemption_amount: Decimal
    investment_by_destination: tuple[tuple[str, Decimal], ...]
    is_balanced: bool


def build_purpose_transition_report(
    positions: list[LtsPosition],
    formation: TargetFormation,
    plan: PurposeTransitionPlan,
) -> tuple[PurposeTransitionReport, ...]:
    """Aggregate a validated transition plan into deterministic Purpose reports.

    This is reporting only: it does not recalculate tax, execute transactions,
    or alter the transition plan.
    """
    current_by_purpose: dict[str, Decimal] = {}
    for position in positions:
        if position.purpose is None:
            raise ValueError(f"Position has no Purpose attribution: {position.id}")
        if position.market_value is None:
            raise ValueError(f"Cannot report unvalued Position {position.id}.")
        amount = position.market_value * position.percentage / Decimal("100")
        current_by_purpose[position.purpose] = (
            current_by_purpose.get(position.purpose, ZERO) + amount
        )

    target_by_purpose: dict[str, Decimal] = {}
    for row in formation.rows:
        target_by_purpose[row.purpose] = target_by_purpose.get(row.purpose, ZERO) + row.target_value

    retained: dict[str, Decimal] = {}
    redemption: dict[str, Decimal] = {}
    locked_redemption: dict[str, Decimal] = {}
    destinations: dict[str, dict[str, Decimal]] = {}

    for mapping in plan.mappings:
        purpose = mapping.purpose
        if mapping.source_kind is TransitionSourceKind.RETAINED_POSITION:
            retained[purpose] = retained.get(purpose, ZERO) + mapping.amount
        elif mapping.source_kind is TransitionSourceKind.REDEMPTION_PROCEEDS:
            redemption[purpose] = redemption.get(purpose, ZERO) + mapping.amount
        elif mapping.source_kind is TransitionSourceKind.LOCKED_REDEMPTION_PROCEEDS:
            locked_redemption[purpose] = locked_redemption.get(purpose, ZERO) + mapping.amount

        by_destination = destinations.setdefault(purpose, {})
        by_destination[mapping.destination_isin] = (
            by_destination.get(mapping.destination_isin, ZERO) + mapping.amount
        )

    purposes = sorted(set(current_by_purpose) | set(target_by_purpose))
    reports: list[PurposeTransitionReport] = []
    for purpose in purposes:
        current_amount = current_by_purpose.get(purpose, ZERO)
        target_amount = target_by_purpose.get(purpose, ZERO)
        destination_rows = tuple(sorted(destinations.get(purpose, {}).items()))
        mapped_destination_amount = sum((amount for _, amount in destination_rows), ZERO)
        retained_amount = retained.get(purpose, ZERO)
        redemption_amount = redemption.get(purpose, ZERO)
        locked_amount = locked_redemption.get(purpose, ZERO)
        is_balanced = (
            abs(current_amount - target_amount) <= TOLERANCE
            and abs(mapped_destination_amount - target_amount) <= TOLERANCE
            and abs(retained_amount + redemption_amount + locked_amount - current_amount) <= TOLERANCE
        )
        reports.append(PurposeTransitionReport(
            purpose=purpose,
            current_amount=current_amount,
            target_amount=target_amount,
            retained_amount=retained_amount,
            redemption_amount=redemption_amount,
            locked_redemption_amount=locked_amount,
            investment_by_destination=destination_rows,
            is_balanced=is_balanced,
        ))

    return tuple(reports)


__all__ = ["PurposeTransitionReport", "build_purpose_transition_report"]
