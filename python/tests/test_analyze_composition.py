from __future__ import annotations

import pandas as pd

from lakshya_core.models import Fund
from team_analysis.analyze_composition import analyze_composition
from team_analysis.composition import Composition
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_analyze_composition_builds_fresh_fingerprint_from_weighted_nav():
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.25, "B": 0.75})

    histories = {
        "A": pd.DataFrame(
            {
                "date": pd.date_range("2010-01-01", periods=30, freq="D"),
                "nav": [100.0 + i for i in range(30)],
            }
        ),
        "B": pd.DataFrame(
            {
                "date": pd.date_range("2010-01-01", periods=30, freq="D"),
                "nav": [200.0 - i for i in range(30)],
            }
        ),
    }

    fingerprint = analyze_composition(composition, histories)

    assert fingerprint.composition is composition
    assert fingerprint.elevation is not None
    assert fingerprint.protection is not None
