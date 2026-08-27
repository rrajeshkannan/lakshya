"""TEAM-stage behavioural fingerprint.

[lakshya] TEAM-stage implementation. All behavioural metrics are calculated
from the collective NAV trajectory; constituent metrics are never combined.
The current TeamFingerprint contains only the evidence earned by TEAM so
far: Elevation and Protection. Richer evidence is added only when a
 downstream consumer genuinely earns the need for it.
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
