"""Collective NAV trajectories for TEAM-stage analysis.

A Team trajectory is derived from the persisted NAV trajectories of its
member Funds. The constituent NAVs are never combined at the metric level.
Instead, the collective NAV is calculated first and the existing behavioural
engine can then operate on that collective trajectory.

For a Team T and observation date D:

    NAV_T(D) = sum(NAV_i(as-of D))

where each member contributes its latest NAV observation on or before D.

The collective timeline is the union of member observation dates within the
period in which every member has an observed history. Missing calendar days
are not manufactured.
"""

from collections.abc import Mapping

import pandas as pd

from lakshya_core.nav_history import normalize_nav_history


def build_collective_nav(
    fund_histories: Mapping[str, pd.DataFrame],
    *,
    assume_canonical: bool = False,
) -> pd.DataFrame:
    """Build the collective NAV trajectory for a Team.

    Args:
        fund_histories: Mapping of Fund identifier to NAV history containing
            ``date`` and ``nav``.
        assume_canonical: When True, treat the supplied histories as already
            validated canonical NAV histories. This is an internal fast path
            for callers that already crossed the NAV-history boundary.
            When False, histories are normalized and validated here.

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

    histories = (
        dict(fund_histories)
        if assume_canonical
        else {
            fund_id: normalize_nav_history(history)
            for fund_id, history in fund_histories.items()
        }
    )

    starts = [history["date"].min() for history in histories.values()]
    ends = [history["date"].max() for history in histories.values()]

    common_start = max(starts)
    common_end = min(ends)

    if common_start > common_end:
        raise ValueError(
            "Team members have no common period of observed NAV history."
        )

    # [lakshya] Canonical histories are already sorted, unique, and typed.
    # Build the union through pandas Index operations rather than iterating
    # every Timestamp through a Python set/sorted cycle. This preserves the
    # exact Collective Timeline contract while avoiding substantial Python
    # datetime iteration overhead across the streamed Team universe.
    timeline = pd.DatetimeIndex([])
    for history in histories.values():
        dates = history["date"]
        start = dates.searchsorted(common_start, side="left")
        end = dates.searchsorted(common_end, side="right")
        member_dates = pd.DatetimeIndex(dates.iloc[start:end])
        timeline = timeline.union(member_dates)

    collective = pd.DataFrame({"date": timeline})

    # [lakshya] Start with integer zero rather than float zero so a singleton
    # preserves the NAV dtype; normal floating-point NAV histories remain
    # floating-point when summed.
    collective["nav"] = 0

    for history in histories.values():
        dates = history["date"]
        navs = history["nav"]
        positions = dates.searchsorted(timeline, side="right") - 1

        if (positions < 0).any():
            raise ValueError(
                "Unable to construct a complete as-of collective trajectory."
            )

        collective["nav"] = collective["nav"] + navs.iloc[positions].to_numpy()

    return collective.reset_index(drop=True)
