"""Deterministic candidate Composition generation.

COMPOSITION is where an admitted TEAM is turned into explicit capital
allocations. The experimental search grid is 5% and every Team member must
participate with strictly positive weight. This avoids representing the same
economic portfolio multiple times through singleton/twin/trio containers.
"""

from __future__ import annotations

from .composition import Composition
from .team import Team


def generate_compositions(team: Team, step: float = 0.05) -> list[Composition]:
    """Generate positive-weight simplex points at ``step`` resolution.

    A singleton produces exactly one Composition at 100%. A twin produces
    19 allocations (5/95 through 95/5). A trio produces 171 allocations on
    the 5% grid. More generally, every member receives at least one grid unit
    and all grid units must sum to one.
    """
    if step <= 0 or step > 1:
        raise ValueError("Composition step must be greater than 0 and at most 1.")

    units = round(1.0 / step)
    if abs(units * step - 1.0) > 1e-9:
        raise ValueError("Composition step must divide 1.0 exactly.")

    members = tuple(fund.isin for fund in team.members)
    if units < len(members):
        return []

    compositions: list[Composition] = []

    def partitions(remaining: int, slots: int):
        if slots == 1:
            yield (remaining,)
            return
        # Start at one unit so every Team member participates. The final
        # allocation is therefore always strictly positive for every member.
        for value in range(1, remaining - slots + 2):
            for tail in partitions(remaining - value, slots - 1):
                yield (value, *tail)

    for allocation in partitions(units, len(members)):
        weights = {
            isin: round(allocation[index] * step, 10)
            for index, isin in enumerate(members)
        }
        compositions.append(Composition(team=team, weights=weights))

    return compositions
