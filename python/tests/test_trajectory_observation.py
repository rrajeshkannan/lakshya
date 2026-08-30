"""Tests for the experimental raw Composite-NAV trajectory observation."""

import pandas as pd
import pytest

from mission.trajectory_observation import observe_trajectory


def nav(values):
    dates = pd.to_datetime([
        "2018-01-01",
        "2019-01-01",
        "2020-01-01",
        "2021-01-01",
        "2022-01-01",
        "2023-01-01",
        "2024-01-01",
        "2025-01-01",
    ])
    return pd.DataFrame({"date": dates, "nav": values})


def test_preserves_full_path_and_normalizes_only_to_observed_start():
    result = observe_trajectory(nav([100, 110, 90, 120, 105, 130, 125, 150]), 5)

    assert result.horizon_years == 5
    assert result.start_date == pd.Timestamp("2020-01-01")
    assert result.end_date == pd.Timestamp("2025-01-01")
    assert [point.elapsed_days for point in result.points] == [0, 366, 731, 1096, 1461, 1827]
    assert [point.nav for point in result.points] == [90, 120, 105, 130, 125, 150]
    assert result.points[0].normalized_nav == pytest.approx(1.0)
    assert result.points[-1].normalized_nav == pytest.approx(150 / 90)


def test_same_horizon_and_same_outcome_can_preserve_different_paths():
    smooth = observe_trajectory(nav([100, 110, 120, 130, 140, 150, 150, 150]), 5)
    turbulent = observe_trajectory(nav([100, 140, 80, 120, 100, 150, 150, 150]), 5)

    assert smooth.start_date == turbulent.start_date
    assert smooth.end_date == turbulent.end_date
    assert smooth.points[-1].normalized_nav == pytest.approx(
        turbulent.points[-1].normalized_nav
    )
    assert [point.normalized_nav for point in smooth.points] != [
        point.normalized_nav for point in turbulent.points
    ]


def test_insufficient_history_is_explicit():
    short = nav([100, 110, 120])

    with pytest.raises(ValueError, match="Insufficient history"):
        observe_trajectory(short, 5)


def test_invalid_nav_is_rejected():
    invalid = nav([100, 110, 0, 120, 130, 140, 150, 160])

    with pytest.raises(ValueError, match="positive"):
        observe_trajectory(invalid, 5)
