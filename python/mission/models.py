"""Minimal MISSION-stage domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from team_analysis.composition import Composition


@dataclass(frozen=True)
class Purpose:
    """A family purpose as seen by MISSION.

    Current capital is observed reality. The remaining fields are optional
    family intentions/requirements and may be revised at a future review.

    ``analytical_horizon_years`` is used only for purposes without a finite
    target/deadline. It provides the analytical horizon for downstream
    trajectory observation without inventing a target corpus.
    """

    name: str
    current_capital: float
    desired_target: Optional[float] = None
    horizon_years: Optional[int] = None
    monthly_contribution: Optional[float] = None
    analytical_horizon_years: Optional[int] = None

    @property
    def has_achievability(self) -> bool:
        """Whether this Purpose has a finite target-based Achievability gate."""
        return self.desired_target is not None and self.monthly_contribution is not None

    @property
    def trajectory_horizon_years(self) -> Optional[int]:
        """Return the Purpose horizon used by Trajectory observation."""
        if self.horizon_years is not None:
            return self.horizon_years
        return self.analytical_horizon_years


@dataclass(frozen=True)
class Mission:
    """A purpose applied to one surviving Composition."""

    purpose: Purpose
    composition: Composition
