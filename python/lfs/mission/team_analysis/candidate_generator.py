"""[lakshya] Deterministic TEAM candidate generation."""

from __future__ import annotations

from itertools import combinations
from typing import Iterable, Iterator

from lakshya_core.models import Fund

from .team import Team


MAX_TEAM_SIZE = 3


def generate_team_candidates(funds: Iterable[Fund]) -> Iterator[Team]:
    """Yield every singleton, pair, and trio exactly once.

    Candidate membership is derivable state, not persisted analytical
    evidence. Funds are canonicalized once before enumeration so a Team's
    member ordering is deterministic and combinations never duplicate the
    same unordered collective.
    """
    ordered_funds = tuple(sorted(funds, key=lambda fund: fund.isin))

    if len({fund.isin for fund in ordered_funds}) != len(ordered_funds):
        raise ValueError("Fund candidates must have unique ISINs.")

    for size in range(1, min(MAX_TEAM_SIZE, len(ordered_funds)) + 1):
        for members in combinations(ordered_funds, size):
            yield Team(members)
