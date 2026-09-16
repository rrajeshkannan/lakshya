"""FUND weak-Pareto gate immediately before TEAM formation."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

import pandas as pd

from lakshya_core.dominance import Dimension, dominates, non_dominated_frontier
from lakshya_core.drawdown_severity import calculate_protection
from lakshya_core.elevation import calculate_elevation
from lakshya_core.models import Fund

from .comparator_surface import ROLLING_HORIZONS, ROLLING_METRICS, fund_team_dimensions


FundDominanceEvent = Callable[[Fund, Fund], None]


def fund_comparator_values(
    fund: Fund,
    nav: pd.DataFrame,
) -> tuple[Fund, dict[str, float | None]]:
    """Map one Fund's NAV history onto the declared FUND/TEAM gate surface."""
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
        values[f"protection_pct_days_at_or_above_{threshold}"] = (
            protection.pct_days_at_or_above_threshold[threshold]
        )

    expected = {dimension.name for dimension in fund_team_dimensions()}
    if set(values) != expected:
        raise AssertionError("Fund comparator surface does not match the declared gate dimensions.")

    return fund, values


def fund_frontier_from_histories(
    funds: Iterable[Fund],
    fund_histories: Mapping[str, pd.DataFrame],
    dimensions: tuple[Dimension, ...] | None = None,
    *,
    on_dominated: FundDominanceEvent | None = None,
) -> list[Fund]:
    """Return the weak-Pareto Fund frontier from the supplied histories.

    The optional callback is observability only. It does not participate in
    the frontier decision and therefore cannot change the mathematical result.
    """
    selected_dimensions = fund_team_dimensions() if dimensions is None else dimensions
    candidates = [
        fund_comparator_values(fund, fund_histories[fund.isin])
        for fund in funds
    ]
    candidate_values = [values for _, values in candidates]
    frontier_values = non_dominated_frontier(candidate_values, selected_dimensions)
    frontier_ids = {id(values) for values in frontier_values}

    if on_dominated is not None:
        for fund, values in candidates:
            if id(values) in frontier_ids:
                continue
            dominator = next(
                (
                    other_fund
                    for other_fund, other_values in candidates
                    if other_fund is not fund
                    and dominates(other_values, values, selected_dimensions)
                ),
                None,
            )
            if dominator is None:
                raise AssertionError(
                    f"FUND frontier inconsistency: non-frontier fund has no dominator: {fund.isin}"
                )
            on_dominated(fund, dominator)

    return [
        next(fund for fund, values in candidates if values is frontier_values_item)
        for frontier_values_item in frontier_values
    ]
