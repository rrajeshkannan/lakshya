"""Derive factual Current State from reconstructed Positions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import Position


@dataclass(frozen=True)
class CurrentState:
    """Current factual units held for one Position."""

    position: Position
    units: Decimal


def derive_current_state(positions: list[Position]) -> list[CurrentState]:
    """Promote reconstructed Position units into explicit Current State.

    Current State is derived from the factual Position reconstruction. Zero-unit
    historical Positions are retained so historical ownership remains visible;
    active CURRENT will later select non-zero states when valuation is added.
    """
    return [
        CurrentState(position=position, units=position.units)
        for position in positions
    ]
