"""Experimental MISSION Protection-only frontier.

This frontier is intentionally applied after Purpose/Elevation qualification.
It asks only whether a surviving Composition is weakly dominated when viewed
through the Protection evidence surface, without importing Elevation or
Purpose into the comparison.
"""

from __future__ import annotations

from collections.abc import Iterable

from .comparator_surface import protection_dimensions
from .composition import Composition
from .composition_comparator import composition_comparator_values
from .composition_fingerprint import CompositionFingerprint
from .streaming_frontier import streaming_frontier


def protection_frontier(
    candidates: Iterable[tuple[Composition, CompositionFingerprint]],
) -> list[Composition]:
    """Return Protection-only non-dominated Compositions.

    Candidates are expected to have already survived the preceding
    Purpose/Elevation qualification stage. Only the declared 12-dimensional
    Protection surface participates in this frontier.
    """
    items = (
        (composition, composition_comparator_values(fingerprint))
        for composition, fingerprint in candidates
    )
    return streaming_frontier(items, protection_dimensions())
