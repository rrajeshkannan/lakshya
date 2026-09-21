"""Validate and classify persisted LPS positions at the LTS CURRENT boundary."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from lps.positions import Position


@dataclass(frozen=True)
class CurrentInputDiagnostics:
    """Counts produced while classifying persisted Position evidence."""

    total_records: int
    active_records: int
    inactive_records: int
    invalid_active_records: int


@dataclass(frozen=True)
class CurrentInput:
    """Validated active positions plus explicitly excluded inactive records."""

    active_positions: tuple[Position, ...]
    inactive_positions: tuple[Position, ...]
    diagnostics: CurrentInputDiagnostics


def _is_inactive(position: Position) -> bool:
    """Return whether a persisted record represents no currently held units."""
    return position.units == Decimal("0")


def classify_current_positions(positions: list[Position]) -> CurrentInput:
    """Classify persisted LPS positions without changing their factual values.

    Zero-unit records are retained as excluded inactive evidence. Every active
    position must have nonnegative units, a market value, and accepted Purpose
    attribution. No tax, transaction, or target logic is applied here.
    """
    active: list[Position] = []
    inactive: list[Position] = []

    for position in positions:
        if _is_inactive(position):
            inactive.append(position)
            continue

        if position.units < 0:
            raise ValueError(f"Active Position has negative units: {position.id}")
        if position.market_value is None:
            raise ValueError(f"Active Position has no market value: {position.id}")
        if position.market_value < 0:
            raise ValueError(f"Active Position has negative market value: {position.id}")
        if not position.purpose or not position.purpose.strip():
            raise ValueError(f"Active Position has no Purpose attribution: {position.id}")

        active.append(position)

    diagnostics = CurrentInputDiagnostics(
        total_records=len(positions),
        active_records=len(active),
        inactive_records=len(inactive),
        invalid_active_records=0,
    )
    return CurrentInput(
        active_positions=tuple(active),
        inactive_positions=tuple(inactive),
        diagnostics=diagnostics,
    )


__all__ = [
    "CurrentInput",
    "CurrentInputDiagnostics",
    "classify_current_positions",
]
