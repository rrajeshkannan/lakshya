"""Production analytical-horizon contract shared with MISSION/TRAJECTORY.

FINAL uses the same canonical analytical horizon ladder as the upstream
MISSION and TRAJECTORY layers.  Keeping the helper local to the package avoids
turning ``final`` into an accidental dependency on a private MISSION module.
"""

from __future__ import annotations

SUPPORTED_ANALYTICAL_HORIZONS: tuple[int, ...] = (3, 5, 7, 10)


def nearest_supported_horizon(horizon_years: float) -> int | None:
    """Return the greatest canonical horizon not exceeding the request."""
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")
    eligible = [years for years in SUPPORTED_ANALYTICAL_HORIZONS if years <= horizon_years]
    return max(eligible) if eligible else None
