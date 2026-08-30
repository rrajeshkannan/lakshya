import pandas as pd
import pytest

from mission.survivor_trajectory_experiment import observe_survivors_for_purpose
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition import Composition
from team_analysis.team import Team
from lakshya_core.models import Fund


def nav(values):
    return pd.DataFrame(
        {
            "date": pd.date_range("2015-01-01", periods=len(values), freq="YS"),
            "nav": values,
        }
    )


def make_fingerprint(values):
    fund = Fund(name="Fund A", isin="A", category="Test")
    composition = Composition(team=Team(members=(fund,)), weights={"A": 1.0})
    return composition, CompositionFingerprint(composition, nav(values))


def test_purpose_horizon_is_the_only_purpose_input_and_uses_floor_years():
    survivors = [make_fingerprint([100, 110, 120, 130, 140, 150])]

    result = observe_survivors_for_purpose(survivors, 4.5)

    observation = next(iter(result.values()))
    assert observation.horizon_years == 4


def test_invalid_purpose_horizon_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        observe_survivors_for_purpose([], 0)
