"""Fund-stage directional comparator values."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from lakshya_core.dominance import Dimension
from lakshya_core.drawdown_severity import calculate_protection
from lakshya_core.elevation import calculate_elevation
from lakshya_core.models import Fund

from team_analysis.comparator_surface import ROLLING_HORIZONS, ROLLING_METRICS, PROTECTION_METRICS, fund_team_dimensions


def fund_comparator_values(
    fund: Fund,
    nav: pd.DataFrame,
) -> tuple[Fund, dict[str, float | None]]:
    """Map a Fund's observed NAV history onto the declared 40-dimension gate.

    The values are derived transiently from the authoritative NAV history.
    No Fund fingerprint artifact is persisted.
    """
    elevation = calculate_elevation(nav)
    protection = calculate_protection(nav)

    values: dict[str, float | None] = {}
    for horizon in ROLLING_HORIZONS:
        evidence = getattr(elevation, f"rolling_{horizon}y")
        for metric in ROLLING_METRICS:
            values[f"elevation_{horizon}y_{metric}"] = (
                None if evidence is None else getattr(evidence, metric)
            )

    for metric in (
        "median_severity_pct",
        "percentile_75_severity_pct",
        "percentile_90_severity_pct",
        "percentile_95_severity_pct",
        "percentile_99_severity_pct",
        "maximum_severity_pct",
    ):
        values[f"protection_{metric}"] = getattr(protection, metric)

    for threshold in (5, 10, 15, 20, 25, 30):
        key = f"pct_days_at_or_above_{threshold}"
        values[f"protection_{key}"] = protection.pct_days_at_or_above_threshold[threshold]

    expected = {dimension.name for dimension in fund_team_dimensions()}
    if set(values) != expected:
        raise AssertionError("Fund comparator values do not match the declared gate dimensions.")

    return fund, values


def fund_frontier_from_histories(
    funds: list[Fund],
    fund_histories: Mapping[str, pd.DataFrame],
    dimensions: tuple[Dimension, ...] | None = None,
) -> list[Fund]:
    """Return the weak-Pareto Fund frontier from the supplied histories."""
    from lakshya_core.dominance import non_dominated_frontier

    selected_dimensions = fund_team_dimensions() if dimensions is None else dimensions
    candidates = [fund_comparator_values(fund, fund_histories[fund.isin]) for fund in funds]
    frontier = non_dominated_frontier(
        [values for _, values in candidates],
        selected_dimensions,
    )
    surviving_values = {id(values): fund for fund, values in candidates}
    return [surviving_values[id(values)] for values in frontier]
