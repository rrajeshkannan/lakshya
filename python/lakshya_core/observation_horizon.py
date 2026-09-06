"""Canonical analytical-horizon contract shared across production stages."""

from __future__ import annotations

SUPPORTED_ANALYTICAL_HORIZONS: tuple[int, ...] = (3, 5, 7, 10)


def nearest_supported_horizon(horizon_years: float) -> int | None:
    """Return the longest canonical horizon not beyond a request.

    MISSION, TRAJECTORY, and FINAL use the same analytical horizon ladder.
    Keeping the contract in ``lakshya_core`` makes that shared rule explicit
    without creating a dependency between stage packages.
    """
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")

    eligible = [
        years for years in SUPPORTED_ANALYTICAL_HORIZONS
        if years <= horizon_years
    ]
    return max(eligible) if eligible else None
