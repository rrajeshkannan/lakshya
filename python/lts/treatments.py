"""LTS transition treatments derived from reconciliation findings."""

from __future__ import annotations

from enum import Enum
from decimal import Decimal

from .models import PositionReconciliation


class TransitionTreatment(str, Enum):
    RETAIN = "RETAIN"
    PARTIALLY_TRANSFORM = "PARTIALLY_TRANSFORM"
    SWITCH = "SWITCH"
    EXIT = "EXIT"
    CREATE = "CREATE"


def classify_position_treatment(
    reconciliation: PositionReconciliation,
    *,
    destination_isin: str | None = None,
) -> TransitionTreatment:
    """Classify the economic treatment of an existing Position.

    This is deliberately not an Action abstraction. SWITCH is selected only
    when an explicit destination ISIN differs from the source ISIN; execution
    mechanics are handled later by constraint/proposal analysis.
    """
    if reconciliation.unmatched_current_value == Decimal("0"):
        return TransitionTreatment.RETAIN
    if reconciliation.matched_value == Decimal("0"):
        if destination_isin and destination_isin != reconciliation.position_id.isin:
            return TransitionTreatment.SWITCH
        return TransitionTreatment.EXIT
    if destination_isin and destination_isin != reconciliation.position_id.isin:
        return TransitionTreatment.SWITCH
    return TransitionTreatment.PARTIALLY_TRANSFORM


__all__ = ["TransitionTreatment", "classify_position_treatment"]
