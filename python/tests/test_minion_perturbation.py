import json

import pandas as pd
import pytest

from mission import minion_perturbation as mp
from mission.minion_perturbation import (
    _aligned_paths,
    _build_nav_from_fund_histories,
    _load_required_navs,
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


def _long_path(points):
    values = [100.0] * 366
    for index, value in points.items():
        values[index] = value
    return _nav(values)


def test_aligned_paths_use_same_start_and_common_dates():
    trio = _long_path({100: 105.0, 200: 95.0, 365: 120.0})
    twin = _long_path({100: 210.0, 200: 190.0, 365: 240.0})
    path = _aligned_paths(trio, twin, 1)
    assert path["date"].iloc[0] == trio["date"].iloc[0]
    assert path["norm_trio"].iloc[0] == pytest.approx(1.0)
    assert path["norm_twin"].iloc[0] == pytest.approx(1.0)
    assert path["norm_trio"].iloc[-1] == pytest.approx(1.2)
    assert path["norm_twin"].iloc[-1] == pytest.approx(1.2)


def test_path_metrics_preserve_path_difference_not_only_endpoint():
    path = _aligned_paths(
        _long_path({100: 120.0, 200: 90.0, 365: 130.0}),
        _long_path({100: 105.0, 200: 100.0, 365: 130.0}),
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


def test_reconstruct_boundary_nav_uses_asof_weighting():
    identity = "A,B|A=0.7500,B=0.2500"
    histories = {
        "A": _nav([100.0, 110.0, 120.0]),
        "B": _nav([200.0, 180.0, 160.0]),
    }
    result = _build_nav_from_fund_histories(identity, histories)
    assert result["nav"].tolist() == pytest.approx([125.0, 127.5, 130.0])


def test_required_navs_load_persisted_identities_once(tmp_path):
    trio = "A,B,C|A=0.8000,B=0.1000,C=0.1000"
    twin = "A,B|A=0.9000,B=0.1000"
    for identity in (trio, twin):
        payload = {
            "composition": identity,
            "kind": "composition_fingerprint",
            "nav": [{"date": "2020-01-01", "nav": 100.0}],
        }
        (tmp_path / f"{identity}.json").write_text(json.dumps(payload), encoding="utf-8")

    task = ("Retirement", trio, "C", twin, "A", {trio}, 1)
    cache, sources = _load_required_navs([task, task], tmp_path, tmp_path)

    assert sorted(cache) == sorted([trio, twin])
    assert sources == {trio: "persisted_fingerprint", twin: "persisted_fingerprint"}
