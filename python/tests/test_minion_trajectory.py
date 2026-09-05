import pandas as pd

from mission.minion_trajectory import _three_way_path, _case_summary


def _nav(values):
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=len(values), freq="D"),
        "nav": values,
    })


def test_three_way_path_normalizes_all_paths_to_same_start():
    path = _three_way_path(_nav([100, 110, 120]), _nav([200, 220, 240]), _nav([50, 55, 60]), 0)
    assert path.iloc[0]["norm_trio"] == 1.0
    assert path.iloc[0]["norm_twin_a"] == 1.0
    assert path.iloc[0]["norm_twin_b"] == 1.0
    assert path.iloc[1]["norm_trio"] == 1.1
    assert path.iloc[1]["norm_twin_a"] == 1.1
    assert path.iloc[1]["norm_twin_b"] == 1.1
    assert path["trio_inside_twin_envelope"].all()


def test_residual_detects_minion_present_path_departure():
    path = _three_way_path(_nav([100, 120, 140]), _nav([100, 110, 120]), _nav([100, 130, 150]), 0)
    assert path.iloc[1]["residual_a_pct_points"] > 0
    assert path.iloc[1]["residual_b_pct_points"] < 0
    assert not path.iloc[1]["trio_inside_twin_envelope"]
    summary = _case_summary(
        "Retirement", "trio", "minion", 5.0,
        "twin_a", "a", "twin_b", "b", path,
        "persisted_fingerprint", "persisted_fingerprint"
    )
    assert summary["trio_outside_envelope_pct"] > 0
    assert summary["max_abs_envelope_excursion_pct_points"] > 0
