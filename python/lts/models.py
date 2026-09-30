"""First LTS analytical models.

These objects are transient run artefacts. They do not become LPS state.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


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


class TransitionDisposition(str, Enum):
    """Whether a cascade slice stays in place or is sold."""

    RETAIN = "RETAIN"
    REDEEM = "REDEEM"


__all__ = [
    "FormationIntentRow",
    "TargetFormation",
    "TransitionDisposition",
]
