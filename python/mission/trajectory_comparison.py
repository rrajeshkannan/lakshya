"""Experimental comparison of surviving Composite-NAV trajectories.

This module is descriptive only. It does not rank, prune, score, or interpret
candidate Compositions. It compares observed trajectories over a common
elapsed-time horizon so MISSION can later test whether path behaviour adds
Purpose-relevant information beyond horizon-level outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from .trajectory_observation import TrajectoryObservation, observe_trajectory


@dataclass(frozen=True)
class TrajectoryComparison:
    """Two trajectories observed over the same requested horizon."""

    horizon_years: int
    left: TrajectoryObservation
    right: TrajectoryObservation


def compare_trajectories(
    left_nav: pd.DataFrame,
    right_nav: pd.DataFrame,
    years: int,
) -> TrajectoryComparison:
    """Compare two Composite-NAV paths over one equivalent elapsed horizon.

    Each trajectory is independently anchored using the existing rolling-time
    convention. The function requires the requested horizon to be observable
    for both candidates. It deliberately performs no scoring or judgement.
    """
    left = observe_trajectory(left_nav, years)
    right = observe_trajectory(right_nav, years)
    return TrajectoryComparison(horizon_years=years, left=left, right=right)


def compare_survivor_trajectories(
    survivor_navs: Mapping[str, pd.DataFrame],
    years: int,
) -> dict[str, TrajectoryObservation]:
    """Observe each surviving Composition on the requested common horizon.

    The returned mapping preserves each candidate's complete observed path.
    Candidates without sufficient history raise explicitly rather than being
    silently excluded or assigned a negative interpretation.
    """
    return {
        key: observe_trajectory(nav, years)
        for key, nav in survivor_navs.items()
    }
