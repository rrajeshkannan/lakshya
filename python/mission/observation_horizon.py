"""Canonical analytical horizon convention shared by MISSION and TRAJECTORY."""

from __future__ import annotations

SUPPORTED_OBSERVATION_HORIZONS: tuple[int, ...] = (3, 5, 7, 10)


def nearest_supported_horizon(horizon_years: float) -> int | None:
    """Return the longest supported analytical horizon not beyond a request.

    The analytical horizon ladder is deliberately shared across MISSION's
    Elevation comparison and TRAJECTORY observation. A requested Purpose
    horizon is therefore never used directly as an observation horizon.
    """
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")

    eligible = [
        years for years in SUPPORTED_OBSERVATION_HORIZONS
        if years <= horizon_years
    ]
    return max(eligible) if eligible else None
