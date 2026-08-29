"""COMPOSITION-stage directional comparator surface."""

from __future__ import annotations

from lakshya_core.dominance import Dimension

from .comparator_surface import fund_team_dimensions
from .composition_fingerprint import CompositionFingerprint


def composition_comparator_values(
    fingerprint: CompositionFingerprint,
) -> dict[str, float]:
    """Map Composition evidence onto the complete behavioural gate surface."""
    values: dict[str, float] = {}

    for dimension in fund_team_dimensions():
        namespace, horizon, metric = dimension.name.split("_", 2)
        if namespace == "elevation":
            years = int(horizon.removesuffix("y"))
            values[dimension.name] = fingerprint.elevation[years][metric]
        else:
            values[dimension.name] = fingerprint.protection[metric]

    return values


def composition_dimensions() -> tuple[Dimension, ...]:
    """Return the complete current 40-dimensional Composition gate surface."""
    return fund_team_dimensions()
