"""MISSION-facing alias for the shared analytical-horizon contract."""

from lakshya_core.observation_horizon import (
    SUPPORTED_ANALYTICAL_HORIZONS,
    nearest_supported_horizon,
)

SUPPORTED_OBSERVATION_HORIZONS = SUPPORTED_ANALYTICAL_HORIZONS

__all__ = ["SUPPORTED_OBSERVATION_HORIZONS", "nearest_supported_horizon"]
