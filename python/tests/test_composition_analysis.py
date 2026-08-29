from __future__ import annotations

import pandas as pd

from lakshya_core.models import Fund
from team_analysis.analyze_composition import analyze_composition
from team_analysis.composition import Composition
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_generated_composition_can_flow_through_analysis():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))
    composition = Composition(
        team=team,
        weights={"A": 0.90, "B": 0.05, "C": 0.05},
    )

    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [90.0 + 2 * i for i in range(30)]}),
        "C": pd.DataFrame({"date": dates, "nav": [110.0 - i for i in range(30)]}),
    }

    fingerprint = analyze_composition(composition, histories)

    assert isinstance(fingerprint, CompositionFingerprint)
    assert fingerprint.composition is composition
    assert fingerprint.elevation is not None
    assert fingerprint.protection is not None


def test_zero_weight_member_remains_part_of_composition_coordinate_space():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))
    composition = Composition(team=team, weights={"A": 0.90, "B": 0.10, "C": 0.0})

    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [200.0 + i for i in range(30)]}),
        "C": pd.DataFrame({"date": dates, "nav": [10000.0 + 10 * i for i in range(30)]}),
    }

    fingerprint = analyze_composition(composition, histories)

    assert fingerprint.composition.weights["C"] == 0.0
