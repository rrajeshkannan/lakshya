"""[lakshya] TEAM/FUND directional comparator-surface definitions."""

from __future__ import annotations

from lakshya_core.dominance import Dimension


ROLLING_METRICS = (
    "minimum",
    "percentile_25",
    "median",
    "percentile_75",
    "maximum",
    "mean",
    "positive_period_pct",
)

ROLLING_HORIZONS = (3, 5, 7, 10)

PROTECTION_METRICS = (
    "median_severity_pct",
    "percentile_75_severity_pct",
    "percentile_90_severity_pct",
    "percentile_95_severity_pct",
    "percentile_99_severity_pct",
    "maximum_severity_pct",
    "pct_days_at_or_above_5",
    "pct_days_at_or_above_10",
    "pct_days_at_or_above_15",
    "pct_days_at_or_above_20",
    "pct_days_at_or_above_25",
    "pct_days_at_or_above_30",
)


def elevation_dimensions() -> tuple[Dimension, ...]:
    """Return the 28 upward Elevation dimensions."""
    return tuple(
        Dimension(f"elevation_{years}y_{metric}", "up")
        for years in ROLLING_HORIZONS
        for metric in ROLLING_METRICS
    )


def protection_dimensions() -> tuple[Dimension, ...]:
    """Return the 12 downward Protection dimensions."""
    return tuple(Dimension(f"protection_{metric}", "down") for metric in PROTECTION_METRICS)


def fund_team_dimensions() -> tuple[Dimension, ...]:
    """Return the complete current FUND/TEAM directional gate surface."""
    return elevation_dimensions() + protection_dimensions()
