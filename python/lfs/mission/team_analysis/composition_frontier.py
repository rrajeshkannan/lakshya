"""Global COMPOSITION-stage behavioural frontier."""

from __future__ import annotations

from collections.abc import Iterable

from .composition import Composition
from .composition_comparator import composition_comparator_values, composition_dimensions
from .composition_fingerprint import CompositionFingerprint
from .streaming_frontier import streaming_frontier


def global_composition_frontier(
    candidates: Iterable[tuple[Composition, CompositionFingerprint]],
) -> list[Composition]:
    """Return globally non-dominated Compositions across all admitted Teams."""
    items = (
        (composition, composition_comparator_values(fingerprint))
        for composition, fingerprint in candidates
    )
    return streaming_frontier(items, composition_dimensions())
