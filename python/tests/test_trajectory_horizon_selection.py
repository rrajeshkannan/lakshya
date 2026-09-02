import pandas as pd
import pytest

from mission.trajectory_observation import select_observable_horizon


def nav(periods):
    return pd.DataFrame(
        {
            "date": pd.date_range("2010-01-01", periods=periods, freq="YS"),
            "nav": [100 + i for i in range(periods)],
        }
    )


def test_selection_uses_canonical_nominal_horizon_and_available_history():
    assert select_observable_horizon(nav(13), 7) == 7
    assert select_observable_horizon(nav(13), 10) == 10


def test_selection_falls_back_when_selected_horizon_is_not_lived():
    assert select_observable_horizon(nav(9), 7) == 7
    assert select_observable_horizon(nav(7), 7) == 5
    assert select_observable_horizon(nav(5), 7) == 3


def test_selection_returns_none_below_three_years_of_lived_history():
    assert select_observable_horizon(nav(3), 10) is None


def test_selection_rejects_noncanonical_nominal_horizon():
    with pytest.raises(ValueError, match="canonical analytical horizons"):
        select_observable_horizon(nav(13), 9)
