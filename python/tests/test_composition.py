from __future__ import annotations

import pandas as pd
import pytest

from team_analysis.composition import Composition
from team_analysis.composition_timeline import build_composition_nav
from team_analysis.team import Team
from lakshya_core.models import Fund


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_composition_requires_exact_team_members_and_weights_sum_to_one():
    team = Team(members=(_fund("A"), _fund("B")))

    composition = Composition(team=team, weights={"A": 0.25, "B": 0.75})

    assert composition.weights == {"A": 0.25, "B": 0.75}


def test_composition_rejects_missing_or_extra_members():
    team = Team(members=(_fund("A"), _fund("B")))

    with pytest.raises(ValueError):
        Composition(team=team, weights={"A": 1.0})

    with pytest.raises(ValueError):
        Composition(team=team, weights={"A": 0.5, "B": 0.5, "C": 0.0})


def test_composition_rejects_negative_weights_and_non_unit_total():
    team = Team(members=(_fund("A"), _fund("B")))

    with pytest.raises(ValueError):
        Composition(team=team, weights={"A": -0.1, "B": 1.1})

    with pytest.raises(ValueError):
        Composition(team=team, weights={"A": 0.4, "B": 0.4})


def test_composition_builds_weighted_nav():
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.25, "B": 0.75})

    a = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
            "nav": [100.0, 110.0, 120.0],
        }
    )
    b = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
            "nav": [200.0, 180.0, 160.0],
        }
    )

    result = build_composition_nav(composition, {"A": a, "B": b})

    assert result["nav"].tolist() == [175.0, 162.5, 150.0]


def test_composition_uses_latest_as_of_nav_for_each_member():
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.5, "B": 0.5})

    a = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-03"]),
            "nav": [100.0, 130.0],
        }
    )
    b = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
            "nav": [200.0, 220.0, 240.0],
        }
    )

    result = build_composition_nav(composition, {"A": a, "B": b})

    assert result["nav"].tolist() == [150.0, 160.0, 185.0]
