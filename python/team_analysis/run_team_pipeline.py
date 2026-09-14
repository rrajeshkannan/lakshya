"""[lakshya] Public TEAM-stage orchestration boundary."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

from fund_analysis.comparator import fund_frontier_from_histories
from lakshya_core.dominance import Dimension
from lakshya_core.models import Fund

from .comparator_surface import fund_team_dimensions
from .frontier_pipeline import team_frontier_from_histories


def run_team_pipeline(
    *,
    funds: Iterable[Fund],
    fund_histories: Mapping[str, pd.DataFrame],
    dimensions: tuple[Dimension, ...] | None = None,
):
    """Run the FUND gate followed by the TEAM frontier.

    [lakshya] Human admission happens before this boundary. The FUND stage
    applies the declared weak-Pareto behavioural gate to those admitted
    Funds, and only its survivors enter TEAM candidate generation.

    No score, rank, weighting, or suitability judgement is introduced by
    the gate. The FUND comparison is transient and is derived directly from
    the supplied NAV histories; no Fund fingerprint artifact is persisted.

    Callers may provide a narrower dimension tuple for focused TEAM tests or
    experiments. The same selected surface is used for the FUND gate so that
    the orchestration remains internally consistent.
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

    return team_frontier_from_histories(
        surviving_funds,
        fund_histories,
        selected_dimensions,
    )
