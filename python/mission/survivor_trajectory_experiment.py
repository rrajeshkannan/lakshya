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
from .trajectory_observation import TrajectoryObservation, observe_trajectory


def observe_survivors_for_purpose(
    survivors: Iterable[tuple[Composition, CompositionFingerprint]],
    purpose_horizon_years: float,
) -> dict[str, TrajectoryObservation]:
    """Observe raw Composite-NAV paths for already-surviving Compositions.

    The Purpose contributes only its horizon as a request for the canonical
    analytical horizon. The observation itself uses the same 3Y/5Y/7Y/10Y
    ladder as MISSION's Elevation comparison, selecting the longest supported
    horizon not beyond the Purpose horizon. The Purpose horizon is never
    passed directly to the trajectory observer.

    This function does not inspect target corpus, current capital,
    contributions, or required return, and it performs no scoring, ordering,
    pruning, or interpretation.

    Results use the same canonical value identity as every other pipeline
    stage. This prevents the runner from depending on ``repr(Composition)``
    and avoids object-hash issues because Composition contains a dict.
    """
    supported_years = nearest_supported_horizon(purpose_horizon_years)
    if supported_years is None:
        raise ValueError(
            "Purpose horizon is below the minimum supported analytical horizon."
        )

    observations: dict[str, TrajectoryObservation] = {}
    for composition, fingerprint in survivors:
        identity = composition_identity(composition)
        if identity in observations:
            raise ValueError(f"duplicate Composition identity: {identity}")
        observations[identity] = observe_trajectory(fingerprint.nav, supported_years)

    return observations
