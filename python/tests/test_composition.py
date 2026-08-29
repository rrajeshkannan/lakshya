import pandas as pd
import pytest

from lakshya_core.models import Fund
from team_analysis.composition import Composition
from team_analysis.composition_timeline import build_composition_nav
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=isin, isin=isin, category="Test")


def _history(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=len(values), freq="D"),
            "nav": values,
        }
    )


def test_composition_requires_exact_team_members():
    team = Team(members=(_fund("A"), _fund("B")))

    with pytest.raises(ValueError):
        Composition(team=team, weights={"A": 1.0})


def test_composition_requires_non_negative_weights_summing_to_one():
    team = Team(members=(_fund("A"), _fund("B")))

    with pytest.raises(ValueError):
        Composition(team=team, weights={"A": 1.1, "B": -0.1})

    with pytest.raises(ValueError):
        Composition(team=team, weights={"A": 0.4, "B": 0.4})


def test_composition_builds_weighted_collective_nav():
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.25, "B": 0.75})

    result = build_composition_nav(
        composition,
        {
            "A": _history([100.0, 120.0, 140.0]),
            "B": _history([200.0, 180.0, 160.0]),
        },
    )

    assert result["nav"].tolist() == [175.0, 165.0, 155.0]


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

    assert result["nav"].tolist() == [150.0, 170.0, 185.0]
