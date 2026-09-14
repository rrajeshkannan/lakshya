"""[lakshya] Public TEAM-stage orchestration boundary."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

from lakshya_core.dominance import Dimension
from lakshya_core.models import Fund

from .comparator_surface import fund_team_dimensions
from .frontier_pipeline import team_frontier_from_histories
from .fund_frontier import fund_frontier_from_histories


def run_team_pipeline(
    *,
    funds: Iterable[Fund],
    fund_histories: Mapping[str, pd.DataFrame],
    dimensions: tuple[Dimension, ...] | None = None,
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

    return team_frontier_from_histories(
        surviving_funds,
        fund_histories,
        selected_dimensions,
    )
