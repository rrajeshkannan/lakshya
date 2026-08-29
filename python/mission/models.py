"""Minimal MISSION-stage domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Purpose:
    """A family purpose as seen by MISSION.

    Current capital is observed reality. The remaining fields are optional
    family intentions/requirements and may be revised at a future review.
    """

    name: str
    current_capital: float
    desired_target: Optional[float] = None
    horizon_years: Optional[int] = None
    monthly_contribution: Optional[float] = None
