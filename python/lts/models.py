"""First LTS analytical models.

These objects are transient run artefacts. They do not become LPS state.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from lps.positions import PositionId


@dataclass(frozen=True)
class FormationIntentRow:
    """One Purpose-to-Composition allocation supplied by LFS.

    target_capital is the committed capital for the Purpose at the TARGET
    boundary. LTS does not derive or alter that Purpose capital.
    target_weight is the selected Composition weight for the ISIN.
    """

    purpose: str
    isin: str
    target_capital: Decimal
    target_weight: Decimal

    @property
    def target_value(self) -> Decimal:
        return self.target_capital * self.target_weight


@dataclass(frozen=True)
class TargetFormation:
    """Economic TARGET formation consumed by LTS."""

    rows: tuple[FormationIntentRow, ...]


@dataclass(frozen=True)
class EconomicReconciliation:
    """CURRENT-to-TARGET economic reconciliation at Purpose × ISIN grain."""

    purpose: str
    isin: str
    current_value: Decimal
    target_value: Decimal
    matched_value: Decimal
    current_excess: Decimal
    target_gap: Decimal


@dataclass(frozen=True)
class PositionReconciliation:
    """How one factual Position contributes to economic TARGET."""

    position_id: PositionId
    target_purpose: str
    target_isin: str
    current_value: Decimal
    matched_value: Decimal
    unmatched_current_value: Decimal


__all__ = [
    "EconomicReconciliation", "FormationIntentRow", "PositionReconciliation",
    "TargetFormation",
]
