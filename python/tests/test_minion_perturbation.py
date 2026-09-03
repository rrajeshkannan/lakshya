from pathlib import Path

import pandas as pd
import pytest

from mission.minion_perturbation import (
    _aligned_paths,
    _path_metrics,
    boundary_twins,
    make_identity,
    parse_composition_identity,
)


def test_parse_and_make_identity_are_canonical():
    identity = "A,B,C|A=0.8000,B=0.1000,C=0.1000"
    members, weights = parse_composition_identity(identity)
    assert members == ("A", "B", "C")
    assert weights == {"A": 0.8, "B": 0.1, "C": 0.1}
    assert make_identity(weights) == identity


def test_boundary_twins_remove_minion_and_assign_its_weight_to_each_recipient():
    identity = "A,B,C|A=0.8000,B=0.1000,C=0.1000"
    assert boundary_twins(identity, "C") == [
        ("A", "A,B|A=0.9000,B=0.1000"),
        ("B", "A,B|A=0.8000,B=0.2000"),
    ]


def test_boundary_twins_are_exact_grid_boundaries_for_five_percent_minion():
    identity = "A,B,C|A=0.8500,B=0.1000,C=0.0500"
    twins = boundary_twins(identity, "C")
    assert {identity for _, identity in twins} == {
        "A,B|A=0.9000,B=0.1000",
        "A,B|A=0.8500,B=0.1500",
    }


def _nav(values):
    dates = pd.date_range("2020-01-01", periods=len(values), freq="D")
    return pd.DataFrame({"date": dates, "nav": values})


def test_aligned_paths_use_same_start_and_common_dates():
    trio = _nav([100, 105, 95, 110, 120])
    twin = _nav([200, 210, 190, 220, 240])
    path = _aligned_paths(trio, twin, 1)
    assert path["date"].iloc[0] == trio["date"].iloc[0]
    assert path["norm_trio"].iloc[0] == pytest.approx(1.0)
    assert path["norm_twin"].iloc[0] == pytest.approx(1.0)
    assert path["norm_trio"].iloc[-1] == pytest.approx(1.2)
    assert path["norm_twin"].iloc[-1] == pytest.approx(1.2)


def test_path_metrics_preserve_path_difference_not_only_endpoint():
    path = _aligned_paths(
        _nav([100, 120, 90, 130]),
        _nav([100, 105, 100, 130]),
        1,
    )
    trio = _path_metrics(path, "trio")
    twin = _path_metrics(path, "twin")
    assert trio["end_normalized_nav"] == pytest.approx(1.3)
    assert twin["end_normalized_nav"] == pytest.approx(1.3)
    assert trio["max_drawdown_pct"] < twin["max_drawdown_pct"]
    assert trio["max_abs_path_gap_pct"] > 0


def test_boundary_twins_reject_non_trios():
    with pytest.raises(ValueError):
        boundary_twins("A,B|A=0.9000,B=0.1000", "B")
