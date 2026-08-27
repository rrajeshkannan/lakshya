"""[lakshya] Generic multidimensional dominance and frontier primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Dimension:
    """A named comparison dimension with an explicit direction."""

    name: str
    direction: str

    def __post_init__(self) -> None:
        if self.direction not in {"up", "down"}:
            raise ValueError("Dimension direction must be 'up' or 'down'.")


def dominates(
    a: Mapping[str, float],
    b: Mapping[str, float],
    dimensions: Sequence[Dimension],
) -> bool:
    """Return whether A strictly dominates B across all eligible dimensions.

    A must be no worse than B on every dimension and strictly better on at
    least one. Missing/None values are not eligible for comparison and are
    therefore ignored for that dimension. If no dimension is eligible, no
    object dominates another.
    """
    better = False
    compared = False

    for dimension in dimensions:
        av = a.get(dimension.name)
        bv = b.get(dimension.name)
        if av is None or bv is None:
            continue

        compared = True
        if dimension.direction == "up":
            if av < bv:
                return False
            if av > bv:
                better = True
        else:
            if av > bv:
                return False
            if av < bv:
                better = True

    return compared and better


def non_dominated_frontier(
    objects: Iterable[Mapping[str, float]],
    dimensions: Sequence[Dimension],
) -> list[Mapping[str, float]]:
    """Return every globally non-dominated object, preserving input order.

    This intentionally computes the mathematical frontier from the complete
    candidate set rather than progressively settling a mutable basket.
    """
    candidates = list(objects)
    return [
        candidate
        for i, candidate in enumerate(candidates)
        if not any(
            j != i and dominates(other, candidate, dimensions)
            for j, other in enumerate(candidates)
        )
    ]
