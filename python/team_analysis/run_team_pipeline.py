"""[lakshya] Public TEAM-stage orchestration boundary."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from math import comb

import pandas as pd

from lakshya_core.dominance import Dimension
from lakshya_core.models import Fund

from .comparator_surface import fund_team_dimensions
from .frontier_pipeline import team_frontier_from_histories
from .fund_frontier import fund_frontier_from_histories


def _team_label(team) -> str:
    return "|".join(member.isin for member in team.members)


def run_team_pipeline(
    *,
    funds: Iterable[Fund],
    fund_histories: Mapping[str, pd.DataFrame],
    dimensions: tuple[Dimension, ...] | None = None,
    detail: Callable[[str], None] | None = None,
):
    """Run the FUND weak-Pareto gate followed by the TEAM frontier.

    Human admission happens before this boundary. The FUND gate is the
    behavioural elimination step inside LFS; only its survivors enter TEAM
    candidate generation.

    The gate is transient: comparator values are derived directly from the
    supplied NAV histories and no Fund fingerprint artifact is persisted.
    """
    selected_dimensions = (
        fund_team_dimensions() if dimensions is None else dimensions
    )

    admitted_funds = list(funds)
    surviving_funds = fund_frontier_from_histories(
        admitted_funds,
        fund_histories,
        dimensions=selected_dimensions,
    )

    if detail is not None:
        detail(
            f"FUND_FRONTIER admitted={len(admitted_funds)} "
            f"survivors={len(surviving_funds)}"
        )
        detail(
            "FUND_SURVIVORS "
            + " ".join(sorted(fund.isin for fund in surviving_funds))
        )

    team_candidate_counts = {
        size: comb(len(surviving_funds), size)
        for size in range(1, min(3, len(surviving_funds)) + 1)
    }
    team_candidate_total = sum(team_candidate_counts.values())
    if detail is not None:
        detail(
            "TEAM_CANDIDATE_UNIVERSE "
            + " ".join(f"size_{size}={count}" for size, count in team_candidate_counts.items())
            + f" total={team_candidate_total}"
        )

    def on_frontier_event(event: str, item: object, related: object | None) -> None:
        if detail is None:
            return
        team = _team_label(item)
        if event == "dominated":
            detail(f"TEAM_DOMINATED candidate={team} dominated_by={_team_label(related)}")
        elif event == "evicted":
            detail(f"TEAM_DOMINATED candidate={team} dominated_by={_team_label(related)}")

    teams = team_frontier_from_histories(
        surviving_funds,
        fund_histories,
        selected_dimensions,
        on_frontier_event=on_frontier_event,
    )

    if detail is not None:
        detail(
            f"TEAM_FRONTIER_SUMMARY candidates={team_candidate_total} survivors={len(teams)} "
            f"dominated_or_evicted={team_candidate_total - len(teams)}"
        )

    return teams
