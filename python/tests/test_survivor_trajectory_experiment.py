import pandas as pd
import pytest

from mission.survivor_trajectory_experiment import observe_survivors_for_purpose
from mission.trajectory_observation import observe_trajectory
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition import Composition, composition_identity
from team_analysis.team import Team
from lakshya_core.models import Fund


def nav(values):
    return pd.DataFrame(
        {
            "date": pd.date_range("2010-01-01", periods=len(values), freq="YS"),
            "nav": values,
        }
    )


def make_fingerprint(values, isin="A"):
    fund = Fund(name=f"Fund {isin}", isin=isin, category="Test")
    composition = Composition(team=Team(members=(fund,)), weights={isin: 1.0})
    return composition, CompositionFingerprint(composition, nav(values))


def test_trajectory_uses_canonical_horizon_not_purpose_horizon():
    survivors = [make_fingerprint([100 + i for i in range(13)])]
    result = observe_survivors_for_purpose(survivors, 9)
    observation = next(iter(result.values()))
    assert observation.horizon_years == 7


def test_trajectory_horizon_matches_mission_convention_for_retirement():
    survivors = [make_fingerprint([100 + i for i in range(15)])]
    result = observe_survivors_for_purpose(survivors, 12)
    observation = next(iter(result.values()))
    assert observation.horizon_years == 10


def test_trajectory_uses_longest_supported_horizon_not_beyond_purpose():
    survivors = [make_fingerprint([100 + i for i in range(13)])]

    expected = {
        4: 3,
        5: 5,
        6: 5,
        7: 7,
        8: 7,
        9: 7,
        10: 10,
        11: 10,
        12: 10,
    }

    for purpose_horizon, trajectory_horizon in expected.items():
        result = observe_survivors_for_purpose(survivors, purpose_horizon)
        observation = next(iter(result.values()))
        assert observation.horizon_years == trajectory_horizon


def test_trajectory_falls_back_to_nearest_available_lower_horizon_per_survivor():
    # The 9Y Purpose nominally selects 7Y. Survivor A has 7Y history,
    # while survivor B only has 5Y, so each Composition gets its own lens.
    survivors = [
        make_fingerprint([100 + i for i in range(9)], "A"),
        make_fingerprint([100 + i for i in range(7)], "B"),
    ]
    result = observe_survivors_for_purpose(survivors, 9)

    observations = {
        composition.split("|", 1)[0]: observation.horizon_years
        for composition, observation in result.items()
    }
    assert observations == {"A": 7, "B": 5}


def test_short_history_survivor_is_not_rejected_by_trajectory():
    survivors = [make_fingerprint([100, 110, 120, 130])]
    result = observe_survivors_for_purpose(survivors, 12)
    observation = next(iter(result.values()))
    assert observation.horizon_years == 3


def test_no_three_year_history_has_no_trajectory_observation():
    survivors = [make_fingerprint([100, 110, 120])]
    result = observe_survivors_for_purpose(survivors, 12)
    assert result == {}


def test_observation_uses_canonical_composition_identity():
    composition, fingerprint = make_fingerprint([100, 110, 120, 130, 140, 150])
    result = observe_survivors_for_purpose([(composition, fingerprint)], 4)
    assert composition_identity(composition) in result


def test_invalid_purpose_horizon_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        observe_survivors_for_purpose([], 0)


def test_trajectory_rejects_duplicate_dates_at_canonical_boundary():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2021-01-01"]),
            "nav": [100, 101, 110],
        }
    )
    with pytest.raises(ValueError, match="duplicate dates"):
        observe_trajectory(data, 1)
