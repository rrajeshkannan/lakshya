"""MISSION-stage vocabulary and boundary contract.

Mission describes what a surviving Composition is being asked to accomplish.
It intentionally contains no behavioural scoring or optimisation logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from team_analysis.composition import Composition


@dataclass(frozen=True)
class Goal:
    """Purpose-level requirement presented to the Mission stage."""

    name: str
    horizon_years: int
    target_corpus: Optional[float] = None


@dataclass(frozen=True)
class Purpose:
    """The family purpose that a Mission evaluates against."""

    name: str
    goals: tuple[Goal, ...]


@dataclass(frozen=True)
class Mission:
    """A purpose applied to one surviving Composition."""

    purpose: Purpose
    composition: Composition
