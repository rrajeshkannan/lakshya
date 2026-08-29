from __future__ import annotations

import pandas as pd

from lakshya_core.models import Fund
from team_analysis.composition import Composition
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_composition_fingerprint_is_derived_from_composition_nav():
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.5, "B": 0.5})

    nav = pd.DataFrame(
        {
            "date": pd.date_range("2010-01-01", periods=30, freq="D"),
            "nav": [100.0 + i for i in range(30)],
        }
    )

    fingerprint = CompositionFingerprint(composition, nav)

    assert fingerprint.composition is composition
    assert fingerprint.elevation is not None
    assert fingerprint.protection is not None


def test_singleton_composition_matches_team_evidence_for_same_trajectory():
    team = Team(members=(_fund("A"),))
    composition = Composition(team=team, weights={"A": 1.0})

    nav = pd.DataFrame(
        {
            "date": pd.date_range("2010-01-01", periods=30, freq="D"),
            "nav": [100.0 + i for i in range(30)],
        }
    )

    fingerprint = CompositionFingerprint(composition, nav)

    assert fingerprint.elevation == __import__(
        "team_analysis.team_fingerprint", fromlist=["TeamFingerprint"]
    ).TeamFingerprint(team, nav).elevation
    assert fingerprint.protection == __import__(
        "team_analysis.team_fingerprint", fromlist=["TeamFingerprint"]
    ).TeamFingerprint(team, nav).protection
