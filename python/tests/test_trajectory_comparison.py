import pandas as pd
import pytest

from mission.trajectory_comparison import (
    compare_survivor_trajectories,
    compare_trajectories,
)


def nav(values):
    return pd.DataFrame(
        {
            "date": pd.date_range("2018-01-01", periods=len(values), freq="YS"),
            "nav": values,
        }
    )


def test_same_time_and_outcome_can_have_different_paths():
    left = nav([100, 110, 120, 130, 140, 150])
    right = nav([100, 140, 80, 120, 100, 150])

    comparison = compare_trajectories(left, right, 5)

    assert comparison.left.start_date == comparison.right.start_date
    assert comparison.left.end_date == comparison.right.end_date
    assert comparison.left.points[-1].normalized_nav == pytest.approx(
        comparison.right.points[-1].normalized_nav
    )
    assert [p.normalized_nav for p in comparison.left.points] != [
        p.normalized_nav for p in comparison.right.points
    ]


def test_survivor_observation_preserves_candidate_identity_and_path():
    survivors = {
        "A": nav([100, 110, 120, 130, 140, 150]),
        "B": nav([100, 140, 80, 120, 100, 150]),
    }

    observations = compare_survivor_trajectories(survivors, 5)

    assert set(observations) == {"A", "B"}
    assert len(observations["A"].points) == len(observations["B"].points)
    assert observations["A"].points[-1].normalized_nav == pytest.approx(
        observations["B"].points[-1].normalized_nav
    )


def test_survivor_without_common_horizon_is_explicit():
    survivors = {
        "A": nav([100, 110, 120, 130, 140, 150]),
        "B": nav([100, 110, 120]),
    }

    with pytest.raises(ValueError, match="Insufficient history"):
        compare_survivor_trajectories(survivors, 5)
