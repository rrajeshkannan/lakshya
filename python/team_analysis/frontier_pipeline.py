"""[lakshya] End-to-end streaming TEAM frontier pipeline."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping

import pandas as pd

from lakshya_core.dominance import Dimension
from lakshya_core.models import Fund

from .collective_timeline import build_collective_nav
from .team import Team
from .team_comparator import team_comparator_values
from .team_fingerprint import TeamFingerprint
from .streaming_frontier import streaming_frontier
from .candidate_generator import generate_team_candidates


def stream_team_evidence(
    funds: Iterable[Fund],
    fund_histories: Mapping[str, pd.DataFrame],
) -> Iterator[tuple[Team, TeamFingerprint]]:
    """Yield Team identity and fingerprint one candidate at a time.

    [lakshya] The candidate universe is derived and streamed. A collective
    NAV is built before any TEAM behavioural metric is calculated.
    """
    for team in generate_team_candidates(funds):
        histories = {member.isin: fund_histories[member.isin] for member in team.members}
        nav = build_collective_nav(histories)
        yield team, TeamFingerprint(team, nav)


def team_frontier_from_histories(
    funds: Iterable[Fund],
    fund_histories: Mapping[str, pd.DataFrame],
    dimensions: tuple[Dimension, ...],
) -> list[Team]:
    """Compute the exact TEAM frontier without retaining the Team universe."""
    candidates = (
        (team, team_comparator_values(fingerprint))
        for team, fingerprint in stream_team_evidence(funds, fund_histories)
    )
    return streaming_frontier(candidates, dimensions)
