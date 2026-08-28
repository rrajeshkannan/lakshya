"""[lakshya] Public TEAM-stage orchestration boundary."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

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
    """Run the TEAM stage and return the non-dominated Team frontier.

    [lakshya] This is orchestration only. Candidate generation, collective
    evidence construction, fingerprinting, comparator mapping, and frontier
    calculation remain delegated to their respective components.

    The default gate is the declared TEAM comparator surface. Callers may
    provide a narrower dimension tuple for focused analytical experiments or
    tests.
    """
    selected_dimensions = (
        fund_team_dimensions() if dimensions is None else dimensions
    )

    return team_frontier_from_histories(
        funds,
        fund_histories,
        selected_dimensions,
    )
