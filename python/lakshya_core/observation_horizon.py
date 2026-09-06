"""Canonical analytical-horizon contract shared across production stages.

The horizon ladder is a cross-stage analytical contract, not ownership of any
single stage. MISSION and FINAL consume the same canonical horizons while
retaining their own stage-specific evidence and decision semantics.
"""

from __future__ import annotations

SUPPORTED_ANALYTICAL_HORIZONS: tuple[int, ...] = (3, 5, 7, 10)


def nearest_supported_horizon(horizon_years: float) -> int | None:
    """Return the longest canonical horizon not beyond a request."""
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")
    eligible = [
        years for years in SUPPORTED_ANALYTICAL_HORIZONS
        if years <= horizon_years
    ]
    return max(eligible) if eligible else None
