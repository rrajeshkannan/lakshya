from __future__ import annotations

import pandas as pd

from mission.behavioral_neighborhood import _components, _mutual_links, _nearest_for_purpose


def pairwise_rows():
    return pd.DataFrame([
        {"purpose":"Edu_B","composition_a":"A","composition_b":"B","same_fund_set":True,"mean_abs_level_gap_pct_points":1.0,"max_abs_level_gap_pct_points":2.0,"daily_return_correlation":0.99,"cagr_difference_pp":0.1,"max_drawdown_difference_pp":0.2},
        {"purpose":"Edu_B","composition_a":"B","composition_b":"C","same_fund_set":False,"mean_abs_level_gap_pct_points":2.0,"max_abs_level_gap_pct_points":3.0,"daily_return_correlation":0.98,"cagr_difference_pp":0.2,"max_drawdown_difference_pp":0.3},
        {"purpose":"Edu_B","composition_a":"A","composition_b":"C","same_fund_set":False,"mean_abs_level_gap_pct_points":5.0,"max_abs_level_gap_pct_points":6.0,"daily_return_correlation":0.90,"cagr_difference_pp":0.5,"max_drawdown_difference_pp":0.6},
    ])


def test_nearest_and_mutual_nearest_are_descriptive_only():
    nearest = _nearest_for_purpose(pairwise_rows())
    a = nearest[nearest["composition"] == "A"].iloc[0]
    b = nearest[nearest["composition"] == "B"].iloc[0]
    c = nearest[nearest["composition"] == "C"].iloc[0]
    assert a["nearest_composition"] == "B"
    assert b["nearest_composition"] == "A"
    assert c["nearest_composition"] == "B"
    assert bool(a["mutual_nearest"])
    assert bool(b["mutual_nearest"])
    assert not bool(c["mutual_nearest"])


def test_mutual_links_are_deduplicated():
    links = _mutual_links(_nearest_for_purpose(pairwise_rows()))
    assert len(links) == 1
    assert {links.iloc[0]["composition_a"], links.iloc[0]["composition_b"]} == {"A", "B"}


def test_components_use_only_mutual_nearest_links_without_thresholds():
    components = _components(_nearest_for_purpose(pairwise_rows()))
    sizes = sorted(components.groupby("component_id")["composition"].size().tolist())
    assert sizes == [1, 2]
