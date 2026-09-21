"""Audit utilities for conservation-balanced Purpose transition plans."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .models import TargetFormation
from .position_bridge import LtsPosition, LtsPositionId
from .purpose_transition import PurposeTransitionPlan, TransitionSourceKind

ZERO = Decimal("0")
TOLERANCE = Decimal("0.00000001")


def _position_value(position: LtsPosition) -> Decimal:
    if position.market_value is None:
        raise ValueError(f"Cannot audit unvalued Position {position.id}.")
    value = position.market_value * position.percentage / Decimal("100")
    if not value.is_finite() or value < ZERO:
        raise ValueError(f"Position has invalid active value: {position.id}")
    return value


def audit_transition_mapping(
    positions: list[LtsPosition],
    formation: TargetFormation,
    plan: PurposeTransitionPlan,
) -> None:
    """Validate physical-source and TARGET-destination completeness.

    The audit is deliberately independent of tax and execution mechanics. It
    verifies that each physical position is mapped exactly once in aggregate,
    each TARGET Purpose/ISIN requirement is funded exactly once in aggregate,
    and source provenance and lock annotations remain consistent.
    """
    source_expected: dict[LtsPositionId, Decimal] = {}
    source_purpose: dict[LtsPositionId, str] = {}
    source_isin: dict[LtsPositionId, str] = {}
    for position in positions:
        if position.purpose is None or not position.purpose.strip():
            raise ValueError(f"Position has no Purpose attribution: {position.id}")
        if position.id in source_expected:
            raise ValueError(f"Duplicate physical source position: {position.id}")
        source_expected[position.id] = _position_value(position)
        source_purpose[position.id] = position.purpose
        source_isin[position.id] = position.id.isin

    source_mapped: dict[LtsPositionId, Decimal] = defaultdict(lambda: ZERO)
    for mapping in plan.mappings:
        if mapping.source_position_id not in source_expected:
            raise ValueError(f"Mapping references unknown source position: {mapping.source_position_id}")
        if source_purpose[mapping.source_position_id] != mapping.purpose:
            raise ValueError(f"Mapping changes Purpose ownership: {mapping.source_position_id}")
        if mapping.source_isin != source_isin[mapping.source_position_id]:
            raise ValueError(f"Mapping source ISIN disagrees with source position: {mapping.source_position_id}")
        if not mapping.destination_isin.strip():
            raise ValueError(f"Mapping destination ISIN cannot be blank: {mapping}")
        if not mapping.amount.is_finite() or mapping.amount <= ZERO:
            raise ValueError(f"Mapping amount must be finite and positive: {mapping}")
        if mapping.source_kind is TransitionSourceKind.RETAINED_POSITION and mapping.locked:
            raise ValueError(f"Retained position cannot be marked locked: {mapping}")
        if mapping.source_kind is TransitionSourceKind.LOCKED_REDEMPTION_PROCEEDS and not mapping.locked:
            raise ValueError(f"Locked redemption source must carry locked=True: {mapping}")
        source_mapped[mapping.source_position_id] += mapping.amount

    for source_id, expected in source_expected.items():
        actual = source_mapped.get(source_id, ZERO)
        if abs(actual - expected) > TOLERANCE:
            raise ValueError(
                f"Source position is not fully mapped: {source_id}: expected={expected}, actual={actual}"
            )

    target_expected: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    for row in formation.rows:
        target_expected[(row.purpose, row.isin)] += row.target_value

    target_mapped: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    for mapping in plan.mappings:
        target_mapped[(mapping.purpose, mapping.destination_isin)] += mapping.amount

    keys = set(target_expected) | set(target_mapped)
    for key in keys:
        expected = target_expected.get(key, ZERO)
        actual = target_mapped.get(key, ZERO)
        if abs(actual - expected) > TOLERANCE:
            raise ValueError(
                f"TARGET allocation is not fully funded: {key}: expected={expected}, actual={actual}"
            )

    if not plan.is_balanced:
        raise ValueError("Transition plan balance summaries are inconsistent.")


__all__ = ["audit_transition_mapping"]
