"""Weighted NAV trajectories for TEAM compositions."""

from collections.abc import Mapping

import pandas as pd

from lakshya_core.nav_history import normalize_nav_history

from .composition import Composition


def build_composition_nav(
    composition: Composition,
    fund_histories: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build the weighted collective NAV trajectory for a Composition.

    Each Fund contributes its latest observed NAV on or before each
    observation date. The resulting weighted trajectory is then suitable for
    the existing Elevation, Protection, and Resilience engines.
    """

    histories = {
        fund_id: normalize_nav_history(history)
        for fund_id, history in fund_histories.items()
    }

    expected = set(composition.weights)
    if set(histories) != expected:
        raise ValueError(
            "Fund histories must contain exactly the Composition member ISINs."
        )

    starts = [history["date"].min() for history in histories.values()]
    ends = [history["date"].max() for history in histories.values()]
    common_start = max(starts)
    common_end = min(ends)

    if common_start > common_end:
        raise ValueError(
            "Composition members have no common period of observed NAV history."
        )

    timeline = pd.DatetimeIndex(
        sorted(
            {
                date
                for history in histories.values()
                for date in history.loc[
                    history["date"].between(common_start, common_end),
                    "date",
                ]
            }
        )
    )

    composition_nav = pd.Series(0.0, index=timeline)

    for fund_id, weight in composition.weights.items():
        series = histories[fund_id].set_index("date")["nav"]
        nav = series.reindex(timeline, method="ffill")
        if nav.isna().any():
            raise ValueError(
                "Unable to construct a complete as-of composition trajectory."
            )
        composition_nav = composition_nav + weight * nav

    return pd.DataFrame(
        {"date": timeline, "nav": composition_nav.to_numpy()}
    ).reset_index(drop=True)
