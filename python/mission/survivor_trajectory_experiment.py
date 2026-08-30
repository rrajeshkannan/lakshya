"""Purpose-aware descriptive experiment for surviving Composition trajectories.

This module deliberately remains outside the decision architecture. It uses
only a Purpose horizon plus already-surviving Composition fingerprints, and
returns descriptive trajectory observations without ranking or pruning.
"""

from __future__ import annotations

from collections.abc import Iterable

from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition import Composition

from .trajectory_observation import TrajectoryObservation, observe_trajectory


def observe_survivors_for_purpose(
    survivors: Iterable[tuple[Composition, CompositionFingerprint]],
    purpose_horizon_years: float,
) -> dict[str, TrajectoryObservation]:
    """Observe raw Composite-NAV paths for already-surviving Compositions.

    The Purpose contributes only its horizon. The function does not inspect
    target corpus, current capital, contributions, or required return, and
    it performs no scoring, ordering, pruning, or interpretation.

    A non-integral horizon is supported by requiring an integer observed
    horizon not exceeding the Purpose horizon. This keeps the observation on
    whole-year rolling windows while never exceeding the Purpose horizon.

    Results are keyed by a stable textual Composition identity rather than
    by the Composition object itself, because Composition is intentionally
    mutable and therefore unhashable.
    """
    if purpose_horizon_years <= 0:
        raise ValueError("purpose_horizon_years must be positive")

    supported_years = int(purpose_horizon_years)
    if supported_years <= 0:
        raise ValueError("purpose horizon must support at least one full year")

    observations: dict[str, TrajectoryObservation] = {}
    for composition, fingerprint in survivors:
        identity = repr(composition)
        if identity in observations:
            raise ValueError(f"duplicate Composition identity: {identity}")
        observations[identity] = observe_trajectory(fingerprint.nav, supported_years)

    return observations
