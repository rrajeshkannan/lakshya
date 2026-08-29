"""Deterministic candidate Composition generation."""

from __future__ import annotations

from itertools import product

from .composition import Composition
from .team import Team


def generate_compositions(team: Team, step: float = 0.05) -> list[Composition]:
    """Generate the simplex of non-negative Team weights at ``step`` resolution.

    The default 5% grid is deliberately both the smallest sampled allocation
    and the perturbation delta. This is a search convention, not a claim that
    smaller allocations are invalid. Composition itself remains capable of
    representing any non-negative weights summing to one.
    """
    if step <= 0 or step > 1:
        raise ValueError("Composition step must be greater than 0 and at most 1.")

    units = round(1.0 / step)
    if abs(units * step - 1.0) > 1e-9:
        raise ValueError("Composition step must divide 1.0 exactly.")

    members = tuple(fund.isin for fund in team.members)
    compositions: list[Composition] = []

    def partitions(remaining: int, slots: int):
        if slots == 1:
            yield (remaining,)
            return
        for value in range(remaining + 1):
            for tail in partitions(remaining - value, slots - 1):
                yield (value, *tail)

    for allocation in partitions(units, len(members)):
        weights = {
            isin: allocation[index] * step
            for index, isin in enumerate(members)
        }
        compositions.append(Composition(team=team, weights=weights))

    return compositions
