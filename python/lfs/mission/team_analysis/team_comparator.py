"""[lakshya] Convert Team behavioural evidence into gate dimensions."""

from __future__ import annotations

from typing import Any

from .comparator_surface import ROLLING_METRICS, fund_team_dimensions


def _put_rolling(values: dict[str, Any], horizon: int, evidence: Any) -> None:
    prefix = f"elevation_{horizon}y_"
    for metric in ROLLING_METRICS:
        values[prefix + metric] = None if evidence is None else getattr(evidence, metric)


def team_comparator_values(fingerprint: Any) -> dict[str, Any]:
    """Return Team gate values directly from the collective fingerprint.

    [lakshya] Unavailable evidence remains explicitly represented as None so
    the comparator surface stays exactly aligned with its declared dimensions.
    """
    values: dict[str, Any] = {}
    elevation = fingerprint.elevation
    _put_rolling(values, 3, elevation.rolling_3y)
    _put_rolling(values, 5, elevation.rolling_5y)
    _put_rolling(values, 7, elevation.rolling_7y)
    _put_rolling(values, 10, elevation.rolling_10y)

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
        raise AssertionError("Team comparator surface does not match the declared gate dimensions.")
    return values
