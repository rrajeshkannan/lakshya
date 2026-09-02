import pandas as pd

from mission.trajectory_observation import select_observable_horizon


def nav(periods):
    return pd.DataFrame(
        {
            "date": pd.date_range("2010-01-01", periods=periods, freq="YS"),
            "nav": [100 + i for i in range(periods)],
        }
    )


def test_selection_uses_purpose_upper_bound_and_available_history():
    assert select_observable_horizon(nav(13), 9) == 7
    assert select_observable_horizon(nav(13), 12) == 10


def test_selection_falls_back_when_selected_horizon_is_not_lived():
    assert select_observable_horizon(nav(9), 9) == 7
    assert select_observable_horizon(nav(7), 9) == 5
    assert select_observable_horizon(nav(5), 9) == 3


def test_selection_returns_none_below_three_years_of_lived_history():
    assert select_observable_horizon(nav(3), 12) is None
