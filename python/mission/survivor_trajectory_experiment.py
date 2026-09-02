"""Purpose-aware descriptive experiment for surviving Composition trajectories.

This module deliberately remains outside the decision architecture. It uses
only a Purpose horizon plus already-surviving Composition fingerprints, and
returns descriptive trajectory observations without ranking or pruning.
"""

from __future__ import annotations

from collections.abc import Iterable

from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint import CompositionFingerprint

from .trajectory_observation import (
    TrajectoryObservation,
    observe_trajectory,
    select_observable_horizon,
)


TRAJECTORY_CONTRACT_VERSION = 3


def observe_survivors_for_purpose(
    survivors: Iterable[tuple[Composition, CompositionFingerprint]],
    purpose_horizon_years: float,
) -> dict[str, TrajectoryObservation]:
    """Observe the richest supported lived path for each survivor.

    The Purpose horizon is only the upper bound for the analytical horizon.
    For each Composition independently, the function selects the longest
    observable member of the canonical 3Y/5Y/7Y/10Y ladder that does not
    exceed the Purpose horizon. A shorter-lived CURRENT fund therefore uses
    the nearest lower supported trajectory rather than being rejected.

    A Composition with less than 3Y lived history has no trajectory
    observation, but remains a MISSION survivor; absence of trajectory
    evidence is deliberately not a decision gate.

    The function performs no scoring, ordering, pruning, or interpretation.
    """
    if purpose_horizon_years <= 0:
        raise ValueError("purpose_horizon_years must be positive")

    observations: dict[str, TrajectoryObservation] = {}
    for composition, fingerprint in survivors:
        identity = composition_identity(composition)
        if identity in observations:
            raise ValueError(f"duplicate Composition identity: {identity}")

        selected_horizon = select_observable_horizon(
            fingerprint.nav,
            purpose_horizon_years,
        )
        if selected_horizon is None:
            continue

        observations[identity] = observe_trajectory(
            fingerprint.nav,
            selected_horizon,
        )

    return observations
