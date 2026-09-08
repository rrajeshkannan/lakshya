"""Minimal MISSION-stage domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from team_analysis.composition import Composition


@dataclass(frozen=True)
class Purpose:
    """A family Purpose as consumed by MISSION.

    ``capital`` is assembled from LPS-valued Positions. The remaining fields
    express family intent: identity, deadline, target, and contribution plan.
    MISSION derives the analytical horizon from ``due``; an open-ended Purpose
    uses the fixed seven-year analytical horizon.
    """

    name: str
    due: Optional[date] = None
    capital: float = 0.0
    desired_target: Optional[float] = None
    monthly_contribution: Optional[float] = None
    horizon_years: Optional[int] = None

    @property
    def has_achievability(self) -> bool:
        """Whether this Purpose has a finite target-based achievability gate."""
        return self.desired_target is not None and self.monthly_contribution is not None and self.horizon_years is not None

    @property
    def trajectory_horizon_years(self) -> int:
        """Return the analytical horizon used by trajectory observation."""
        if self.horizon_years is not None:
            return self.horizon_years
        return 7


@dataclass(frozen=True)
class Mission:
    """A Purpose applied to one surviving Composition."""

    purpose: Purpose
    composition: Composition
