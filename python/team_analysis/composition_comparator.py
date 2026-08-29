"""COMPOSITION-stage directional comparator surface."""

from __future__ import annotations

from typing import Any, Mapping

from lakshya_core.dominance import Dimension

from .comparator_surface import ROLLING_METRICS, ROLLING_HORIZONS, fund_team_dimensions
from .composition_fingerprint import CompositionFingerprint


def _evidence_for_horizon(elevation: Any, horizon: int) -> Any:
    if isinstance(elevation, Mapping):
        return elevation.get(horizon)
    try:
        return elevation[horizon]
    except (TypeError, KeyError, IndexError):
        return getattr(elevation, f"rolling_{horizon}y")


def _metric(evidence: Any, metric: str) -> Any:
    if isinstance(evidence, Mapping):
        return evidence.get(metric)
    try:
        return evidence[metric]
    except (TypeError, KeyError, IndexError):
        return getattr(evidence, metric)


def _put_rolling(values: dict[str, Any], horizon: int, evidence: Any) -> None:
    prefix = f"elevation_{horizon}y_"
    for metric in ROLLING_METRICS:
        values[prefix + metric] = None if evidence is None else _metric(evidence, metric)


def composition_comparator_values(
    fingerprint: CompositionFingerprint,
) -> dict[str, Any]:
    """Map fresh Composition evidence onto the complete behavioural gate surface."""
    values: dict[str, Any] = {}
    for horizon in ROLLING_HORIZONS:
        _put_rolling(values, horizon, _evidence_for_horizon(fingerprint.elevation, horizon))

    protection = fingerprint.protection
    values.update({
        "protection_median_severity_pct": _metric(protection, "median_severity_pct"),
        "protection_percentile_75_severity_pct": _metric(protection, "percentile_75_severity_pct"),
        "protection_percentile_90_severity_pct": _metric(protection, "percentile_90_severity_pct"),
        "protection_percentile_95_severity_pct": _metric(protection, "percentile_95_severity_pct"),
        "protection_percentile_99_severity_pct": _metric(protection, "percentile_99_severity_pct"),
        "protection_maximum_severity_pct": _metric(protection, "maximum_severity_pct"),
    })
    if isinstance(protection, Mapping):
        threshold_values = protection.get("pct_days_at_or_above_threshold", {})
    else:
        try:
            threshold_values = protection["pct_days_at_or_above_threshold"]
        except (TypeError, KeyError, IndexError):
            threshold_values = protection.pct_days_at_or_above_threshold
    for threshold in (5, 10, 15, 20, 25, 30):
        values[f"protection_pct_days_at_or_above_{threshold}"] = threshold_values.get(threshold)

    expected = {dimension.name for dimension in fund_team_dimensions()}
    if set(values) != expected:
        raise AssertionError(
            "Composition comparator surface does not match the declared gate dimensions."
        )
    return values


def composition_dimensions() -> tuple[Dimension, ...]:
    """Return the complete current 40-dimensional Composition gate surface."""
    return fund_team_dimensions()
