from __future__ import annotations

import pandas as pd

from lakshya_core.models import Fund
from team_analysis.analyze_composition import analyze_composition
from team_analysis.composition import Composition
from team_analysis.composition_comparator import (
    composition_comparator_values,
    composition_dimensions,
)
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_composition_comparator_exposes_the_same_40_dimensions_as_team():
    assert len(composition_dimensions()) == 40
    assert [dimension.name for dimension in composition_dimensions()] == [
        dimension.name
        for dimension in composition_dimensions()
    ]


def test_composition_comparator_maps_fresh_evidence():
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.95, "B": 0.05})
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [90.0 + 2 * i for i in range(30)]}),
    }

    fingerprint = analyze_composition(composition, histories)
    values = composition_comparator_values(fingerprint)

    assert len(values) == 40
    assert values["elevation_3y_minimum"] is None
    assert values["protection_median_severity_pct"] is not None
