"""LTS economic and Position reconciliation.

This module deliberately stops before tax, transaction mechanics, and
proposal construction. It answers only what CURRENT already satisfies of
TARGET and which LTS Positions supply that matched capital.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .models import EconomicReconciliation, FormationIntentRow, PositionReconciliation, TargetFormation
from .position_bridge import LtsPosition

ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")


def _active_value(position: LtsPosition) -> Decimal:
    """Return this LTS Position's Purpose-attributed observed value.

    The bridge currently gives every legacy Position 100%. Future Slice-based
    LPS state may partition a physical Investor + Folio + ISIN across several
    LTS Positions, so the percentage is applied here rather than changing
    the underlying observed market value.
    """
    if not position.percentage.is_finite() or not ZERO <= position.percentage <= ONE_HUNDRED:
        raise ValueError(
            f"Position percentage must be finite and between 0 and 100: "
            f"{position.id} -> {position.percentage}"
        )
    if position.units == 0:
        return ZERO
    if position.market_value is None:
        raise ValueError(
            "Cannot perform economic reconciliation for unvalued Position "
            f"{position.id}."
        )
    return position.market_value * position.percentage / ONE_HUNDRED


def reconcile_economically(
    positions: list[LtsPosition],
    formation_intent: TargetFormation | list[FormationIntentRow],
) -> list[EconomicReconciliation]:
    """Reconcile Purpose-attributed capital against TARGET.

    Matching is performed independently for each Purpose × ISIN pair. Each
    LTS Position contributes only to its accepted Purpose.
    """
    current: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    for position in positions:
        if position.purpose is None:
            continue
        current[(position.purpose, position.id.isin)] += _active_value(position)

    target: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    rows = formation_intent.rows if isinstance(formation_intent, TargetFormation) else formation_intent
    for row in rows:
        if not row.target_capital.is_finite() or row.target_capital < ZERO:
            raise ValueError("Target capital must be finite and non-negative.")
        if not row.target_weight.is_finite() or row.target_weight < ZERO:
            raise ValueError("Target weight must be finite and non-negative.")
        target[(row.purpose, row.isin)] += row.target_value

    keys = sorted(set(current) | set(target))
    result = []
    for purpose, isin in keys:
        current_value = current[(purpose, isin)]
        target_value = target[(purpose, isin)]
        matched = min(current_value, target_value)
        result.append(EconomicReconciliation(
            purpose=purpose, isin=isin,
            current_value=current_value, target_value=target_value,
            matched_value=matched,
            current_excess=current_value - matched,
            target_gap=target_value - matched,
        ))
    return result


def reconcile_positions(
    positions: list[LtsPosition],
    economic: list[EconomicReconciliation],
) -> list[PositionReconciliation]:
    """Allocate matched economic capital back to LTS Positions.

    This allocation is analytical only. It never mutates the bridge or LPS
    state. Positions are consumed deterministically in identity order.
    """
    remaining: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    for row in economic:
        if row.matched_value < ZERO:
            raise ValueError("Matched economic value cannot be negative.")
        remaining[(row.purpose, row.isin)] += row.matched_value

    result = []

    for position in sorted(
        positions,
        key=lambda p: (p.id.investor, p.id.folio, p.id.isin, p.id.slice),
    ):
        if position.purpose is None:
            continue
        value = _active_value(position)
        key = (position.purpose, position.id.isin)
        available = remaining.get(key, ZERO)
        matched = min(value, available)
        remaining[key] = available - matched
        result.append(PositionReconciliation(
            position_id=position.id,
            target_purpose=position.purpose,
            target_isin=position.id.isin,
            current_value=value,
            matched_value=matched,
            unmatched_current_value=value - matched,
        ))

    if any(value != ZERO for value in remaining.values()):
        raise AssertionError("Position reconciliation failed to consume matched capital.")
    return result


__all__ = ["reconcile_economically", "reconcile_positions"]
