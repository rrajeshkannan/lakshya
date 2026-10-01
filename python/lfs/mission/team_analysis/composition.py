"""Composition identity for TEAM-stage portfolio shaping.

A Composition describes how capital is allocated across the Funds of an
already-admitted Team. It contains weights only; behavioural evidence is
always recalculated from the resulting weighted NAV trajectory.

The Composition *generator* uses Lakshya's experimental search convention:
all members of a Team participate with strictly positive weight on a 5%
grid (with a singleton naturally fixed at 100%). The domain object itself
remains permissive of non-negative weights so it can represent externally
constructed boundary cases without silently changing their meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from .team import Team


@dataclass(frozen=True)
class Composition:
    """A valid capital composition of a Team.

    Weights are keyed by Fund ISIN. Every Team member must be represented
    exactly once, weights must be non-negative, and the total must equal 1.
    The generator is stricter: generated multi-member Compositions give every
    member positive weight.
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


def composition_identity(composition: Composition) -> str:
    """Return the canonical textual identity used across pipeline stages.

    Team identity and allocation are both encoded, with ISINs sorted so the
    identity is independent of dictionary insertion order. This is deliberately
    a value identity rather than a hash of ``Composition`` because the
    dataclass contains a mutable ``dict`` and is therefore unhashable.
    """
    members = ",".join(sorted(composition.weights))
    weights = ",".join(
        f"{isin}={composition.weights[isin]:.4f}"
        for isin in sorted(composition.weights)
    )
    return f"{members}|{weights}"
