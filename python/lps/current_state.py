"""Derive factual Current State from reconstructed Positions."""

from __future__ import annotations

from dataclasses import dataclass

from lps.positions import Position


@dataclass(frozen=True)
class CurrentState:
    """Current factual state for one Position."""

    position: Position


def derive_current_state(positions: list[Position]) -> list[CurrentState]:
    """Promote reconstructed Positions into explicit Current State."""
    return [CurrentState(position=position) for position in positions]
