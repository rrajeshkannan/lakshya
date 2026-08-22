"""Collective NAV trajectories for TEAM-stage analysis.

A Team trajectory is derived from the persisted NAV trajectories of its
member Funds.  The constituent NAVs are never combined at the metric level.
Instead, the collective NAV is calculated first and the existing behavioural
engine can then operate on that collective trajectory.

For a Team T and observation date D:

    NAV_T(D) = sum(NAV_i(as-of D))

where each member contributes its latest NAV observation on or before D.

The collective timeline is the union of member observation dates within the
period in which every member has an observed history.  Missing calendar days
are not manufactured.
"""

from collections.abc import Mapping

import pandas as pd

from lakshya_core.nav_history import normalize_nav_history


def build_collective_nav(
    fund_histories: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build the collective NAV trajectory for a Team.

    Args:
        fund_histories: Mapping of Fund identifier to canonical (or
            canonicalizable) NAV history containing ``date`` and ``nav``.

    Returns:
        A DataFrame with ``date`` and ``nav`` columns in chronological order.
        Each NAV is the sum of every member Fund's latest observation on or
        before that date.

    Raises:
        ValueError: If no members are supplied or the member histories have
            no common period of observed history.
    """

    if not fund_histories:
        raise ValueError("A Team must contain at least one Fund.")

    histories = {
        fund_id: normalize_nav_history(history)
        for fund_id, history in fund_histories.items()
    }

    starts = [history["date"].min() for history in histories.values()]
    ends = [history["date"].max() for history in histories.values()]

    common_start = max(starts)
    common_end = min(ends)

    if common_start > common_end:
        raise ValueError(
            "Team members have no common period of observed NAV history."
        )

    # The Team timeline contains every constituent observation date inside
    # the common period.  We do not manufacture calendar-day observations.
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

    collective = pd.DataFrame({"date": timeline})

    # Reindex each Fund onto the collective observation dates and carry its
    # latest known NAV forward.  Because the timeline starts only once every
    # Fund has begun, every member has a valid as-of value at every Team date.
    for history in histories.values():
        series = history.set_index("date")["nav"]
        collective_nav = series.reindex(timeline, method="ffill")

        if collective_nav.isna().any():
            raise ValueError(
                "Unable to construct a complete as-of collective trajectory."
            )

        collective["nav"] = collective.get("nav", 0.0) + collective_nav.to_numpy()

    return collective.reset_index(drop=True)
