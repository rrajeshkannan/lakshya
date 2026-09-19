"""LTS economic and Position reconciliation.

This module deliberately stops before tax, transaction mechanics, and
proposal construction. It answers only what CURRENT already satisfies of
TARGET and which factual Positions supply that matched capital.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from lps.positions import Position

from .models import EconomicReconciliation, FormationIntentRow, PositionReconciliation, TargetFormation

ZERO = Decimal("0")


def _active_value(position: Position) -> Decimal:
    """Return an established Position's observed market value.

    Missing valuation is unknown, not zero. LTS cannot reconcile an unvalued
    Position economically, so fail explicitly rather than silently treating
    it as having no value.
    """
    if position.units == 0:
        return ZERO
    if position.market_value is None:
        raise ValueError(
            "Cannot perform economic reconciliation for unvalued Position "
            f"{position.id}."
        )
    return position.market_value


def reconcile_economically(
    positions: list[Position],
    formation_intent: TargetFormation | list[FormationIntentRow],
) -> list[EconomicReconciliation]:
    """Reconcile established Purpose-attributed capital against TARGET.

    Matching is performed independently for each Purpose × ISIN pair. A
    Position contributes only to its accepted current Purpose; changing that
    attribution is a separate transition concern.
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
    positions: list[Position],
    economic: list[EconomicReconciliation],
) -> list[PositionReconciliation]:
    """Allocate matched economic capital back to factual Positions.

    This allocation is analytical only. It never splits or mutates an LPS
    Position. Positions are consumed deterministically in identity order.
    """
    remaining = {(row.purpose, row.isin): row.matched_value for row in economic}
    result = []

    for position in sorted(
        positions, key=lambda p: (p.id.investor, p.id.folio, p.id.isin)
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
