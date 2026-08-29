"""Streaming COMPOSITION-stage analytical pipeline primitives."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping

import pandas as pd

from .analyze_composition import analyze_composition
from .composition import Composition
from .composition_fingerprint import CompositionFingerprint
from .generate_compositions import generate_compositions
from .team import Team


def stream_composition_fingerprints(
    teams: Iterable[Team],
    fund_histories: Mapping[str, pd.DataFrame],
) -> Iterator[tuple[Composition, CompositionFingerprint]]:
    """Yield Composition identity and fresh fingerprint one candidate at a time.

    The supplied Teams are assumed to have already passed the TEAM-stage gate.
    Composition generation and analysis are derived from those admitted Teams;
    no Team-level behavioural evidence is inherited by a Composition.
    """
    for team in teams:
        for composition in generate_compositions(team):
            histories = {
                member.isin: fund_histories[member.isin]
                for member in team.members
            }
            yield composition, analyze_composition(composition, histories)
