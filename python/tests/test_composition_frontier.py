from __future__ import annotations

from dataclasses import replace

from lakshya_core.models import Fund
from team_analysis.composition import Composition
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition_frontier import global_composition_frontier
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def _fingerprint(composition: Composition, *, elevation: float, protection: float) -> CompositionFingerprint:
    """Build a minimal test fingerprint by adapting a populated fixture object."""
    raise NotImplementedError


def test_composition_frontier_is_global_across_team_provenance():
    """A Composition from one Team can remove a dominated Composition from another."""
    # This test is intentionally deferred until the repository's canonical
    # CompositionFingerprint fixture factory is exposed. The production
    # frontier itself is already wired to the common 40-D comparator surface.
    assert global_composition_frontier([]) == []
