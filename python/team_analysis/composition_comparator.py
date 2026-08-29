"""COMPOSITION-stage directional comparator surface."""

from __future__ import annotations

from typing import Any, Mapping

from lakshya_core.dominance import Dimension

from .comparator_surface import ROLLING_METRICS, ROLLING_HORIZONS, fund_team_dimensions
from .composition_fingerprint import CompositionFingerprint


def _evidence_for_horizon(elevation: Any, horizon: int) -> Any:
    if isinstance(elevation, Mapping):
        return elevation.get(horizon)
    return getattr(elevation, f"rolling_{horizon}y")


def _put_rolling(values: dict[str, Any], horizon: int, evidence: Any) -> None:
    prefix = f"elevation_{horizon}y_"
    for metric in ROLLING_METRICS:
        values[prefix + metric] = None if evidence is None else getattr(evidence, metric)


def composition_comparator_values(
    fingerprint: CompositionFingerprint,
) -> dict[str, Any]:
    """Map fresh Composition evidence onto the complete behavioural gate surface."""
    values: dict[str, Any] = {}
    for horizon in ROLLING_HORIZONS:
        _put_rolling(values, horizon, _evidence_for_horizon(fingerprint.elevation, horizon))

    protection = fingerprint.protection
    values.update({
        "protection_median_severity_pct": protection.median_severity_pct,
        "protection_percentile_75_severity_pct": protection.percentile_75_severity_pct,
        "protection_percentile_90_severity_pct": protection.percentile_90_severity_pct,
        "protection_percentile_95_severity_pct": protection.percentile_95_severity_pct,
        "protection_percentile_99_severity_pct": protection.percentile_99_severity_pct,
        "protection_maximum_severity_pct": protection.maximum_severity_pct,
    })
    for threshold in (5, 10, 15, 20, 25, 30):
        values[f"protection_pct_days_at_or_above_{threshold}"] = (
            protection.pct_days_at_or_above_threshold.get(threshold)
        )

    expected = {dimension.name for dimension in fund_team_dimensions()}
    if set(values) != expected:
        raise AssertionError(
            "Composition comparator surface does not match the declared gate dimensions."
        )
    return values


def composition_dimensions() -> tuple[Dimension, ...]:
    """Return the complete current 40-dimensional Composition gate surface."""
    return fund_team_dimensions()
