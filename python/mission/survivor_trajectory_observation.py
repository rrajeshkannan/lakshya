"""Read-only MISSION experiment over already-surviving Compositions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from .trajectory_observation import TrajectoryObservation, observe_trajectory


@dataclass(frozen=True)
class SurvivorTrajectoryObservation:
    """Descriptive trajectory observations for an existing survivor set."""

    horizon_years: int
    observations: Mapping[str, TrajectoryObservation]


def observe_survivor_trajectories(
    survivor_navs: Mapping[str, pd.DataFrame],
    horizon_years: int,
) -> SurvivorTrajectoryObservation:
    """Observe all supplied survivors on one requested supported horizon.

    This function deliberately does not decide which candidates survive. It
    assumes that the supplied mapping is already the output of earlier MISSION
    gates and only preserves comparable Composite-NAV path observations.
    """
    observations = {
        key: observe_trajectory(nav, horizon_years)
        for key, nav in survivor_navs.items()
    }
    return SurvivorTrajectoryObservation(
        horizon_years=horizon_years,
        observations=observations,
    )
