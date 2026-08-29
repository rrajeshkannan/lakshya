"""Deterministic candidate Composition generation."""

from __future__ import annotations

from .composition import Composition
from .team import Team


def generate_compositions(team: Team, step_pct: int = 5) -> list[Composition]:
    """Generate the complete non-negative weight grid for an admitted Team.

    The default 5% step is the candidate-generation convention. Zero weights
    are retained because the Team remains the fixed three-member coordinate
    space; they naturally express singleton and twin compositions.
    """
    if not 1 <= step_pct <= 100 or 100 % step_pct != 0:
        raise ValueError("step_pct must be a positive divisor of 100.")

    member_count = len(team.members)
    if not 1 <= member_count <= 3:
        raise ValueError("Composition generation supports Teams of 1 to 3 members.")

    isins = [fund.isin for fund in team.members]
    units = 100 // step_pct

    def compositions(remaining: int, slots: int, prefix: tuple[int, ...]):
        if slots == 1:
            yield prefix + (remaining,)
            return
        for value in range(remaining + 1):
            yield from compositions(remaining - value, slots - 1, prefix + (value,))

    return [
        Composition(
            team=team,
            weights={isin: units_value * step_pct / 100 for isin, units_value in zip(isins, allocation)},
        )
        for allocation in compositions(units, member_count, ())
    ]
