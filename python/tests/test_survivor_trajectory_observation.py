import pandas as pd
import pytest

from mission.survivor_trajectory_observation import observe_survivor_trajectories


def nav(values):
    return pd.DataFrame(
        {
            "date": pd.date_range("2018-01-01", periods=len(values), freq="YS"),
            "nav": values,
        }
    )


def test_observes_existing_survivors_without_ranking_or_pruning():
    survivors = {
        "A": nav([100, 110, 120, 130, 140, 150]),
        "B": nav([100, 140, 80, 120, 100, 150]),
    }

    result = observe_survivor_trajectories(survivors, 5)

    assert result.horizon_years == 5
    assert set(result.observations) == {"A", "B"}
    assert [p.normalized_nav for p in result.observations["A"].points] != [
        p.normalized_nav for p in result.observations["B"].points
    ]
    assert result.observations["A"].points[-1].normalized_nav == pytest.approx(
        result.observations["B"].points[-1].normalized_nav
    )


def test_missing_history_is_not_silently_discarded():
    survivors = {
        "A": nav([100, 110, 120, 130, 140, 150]),
        "B": nav([100, 110, 120]),
    }

    with pytest.raises(ValueError, match="Insufficient history"):
        observe_survivor_trajectories(survivors, 5)
