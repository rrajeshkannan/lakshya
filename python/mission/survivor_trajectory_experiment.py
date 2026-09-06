"""Purpose-aware descriptive experiment for surviving Composition trajectories.

This module deliberately remains outside the decision architecture. It uses
only a Purpose horizon plus already-surviving Composition fingerprints, and
returns descriptive trajectory observations without ranking or pruning.
"""

from __future__ import annotations

from collections.abc import Iterable

from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint import CompositionFingerprint

from .observation_horizon import nearest_supported_horizon
from .trajectory_observation import (
    TrajectoryObservation,
    observe_trajectory,
    select_observable_horizon,
)


TRAJECTORY_CONTRACT_VERSION = 4


def observe_survivors_for_purpose(
    survivors: Iterable[tuple[Composition, CompositionFingerprint]],
    purpose_horizon_years: float,
) -> dict[str, TrajectoryObservation]:
    """Observe the richest supported lived path for each survivor.

    The Purpose horizon is only the upper bound for the analytical horizon.
    The nominal analytical lens is the longest canonical 3Y/5Y/7Y/10Y horizon
    that does not exceed the Purpose horizon. For each Composition
    independently, the observation then falls back to the longest lower
    canonical horizon actually supported by that Composition's NAV history.

    A Composition with less than 3Y lived history has no trajectory
    observation, but remains a MISSION survivor; absence of trajectory
    evidence is deliberately not a decision gate.

    The function performs no scoring, ordering, pruning, or interpretation.
    """
    if purpose_horizon_years <= 0:
        raise ValueError("purpose_horizon_years must be positive")

    nominal_horizon = nearest_supported_horizon(purpose_horizon_years)
    if nominal_horizon is None:
        return {}

    observations: dict[str, TrajectoryObservation] = {}
    for composition, fingerprint in survivors:
        identity = composition_identity(composition)
        if identity in observations:
            raise ValueError(f"duplicate Composition identity: {identity}")

        selected_horizon = select_observable_horizon(
            fingerprint.nav,
            nominal_horizon,
        )
        if selected_horizon is None:
            continue

        observations[identity] = observe_trajectory(
            fingerprint.nav,
            selected_horizon,
        )

    return observations
