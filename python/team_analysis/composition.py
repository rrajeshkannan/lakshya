"""Composition identity for TEAM-stage portfolio shaping.

A Composition describes how capital is allocated across the Funds of an
already-admitted Team. It contains weights only; behavioural evidence is
always recalculated from the resulting weighted NAV trajectory.
"""

from __future__ import annotations

from dataclasses import dataclass

from .team import Team


@dataclass(frozen=True)
class Composition:
    """A valid capital composition of a Team.

    Weights are keyed by Fund ISIN. Every Team member must be represented
    exactly once, weights must be non-negative, and the total must equal 1.
    """

    team: Team
    weights: dict[str, float]

    def __post_init__(self) -> None:
        expected = {fund.isin for fund in self.team.members}
        actual = set(self.weights)

        if actual != expected:
            raise ValueError(
                "Composition weights must contain exactly the Team member ISINs."
            )

        if any(weight < 0 for weight in self.weights.values()):
            raise ValueError("Composition weights must be non-negative.")

        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError("Composition weights must sum to 1.0.")
