"""TEAM-stage gate fingerprint.

The TEAM gate uses the same trajectory-derived Elevation and Protection
mathematics as FUND. No constituent metrics are combined: the collective
NAV trajectory is the sole input to the calculations.
"""

from __future__ import annotations

import pandas as pd

from lakshya_core.elevation import calculate_elevation
from lakshya_core.drawdown_severity import calculate_protection

from .team import Team


class TeamFingerprint:
    """TEAM behavioural evidence currently required for TEAM dominance."""

    def __init__(self, team: Team, nav: pd.DataFrame) -> None:
        self.team = team
        self.elevation = calculate_elevation(nav)
        self.protection = calculate_protection(nav)
