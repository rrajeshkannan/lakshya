from __future__ import annotations

import pandas as pd
import pytest

from mission.behavioral_neighborhood_structure import _parse_composition, _structural_row


def test_parse_composition_preserves_native_identity_weights():
    identity = "A,B,C|A=75,B=10,C=15"
    assert _parse_composition(identity) == {"A": 75.0, "B": 10.0, "C": 15.0}


def test_structural_row_reports_interpretable_weight_and_fund_changes():
    row = _structural_row(
        "Edu_B",
        "A,B,C|A=75,B=10,C=15",
        "A,B,D|A=80,B=5,D=15",
        "mean_abs_level_gap_pct_points",
        0.18,
        {"same_team": False},
    )
    assert row["same_team"] is False
    assert row["cardinality_a"] == 3
    assert row["cardinality_b"] == 3
    assert row["shared_fund_count"] == 2
    assert row["funds_added_in_b"] == "D"
    assert row["funds_removed_in_b"] == "C"
    assert row["weight_l1_difference_pp"] == pytest.approx(40.0)
    assert row["max_single_fund_weight_change_pp"] == pytest.approx(15.0)
    assert row["changed_fund_count"] == 4


def test_structural_row_is_zero_for_identical_compositions():
    identity = "A,B|A=90,B=10"
    row = _structural_row("Retirement", identity, identity, "mean_abs_level_gap_pct_points", 0.0, {"same_team": True})
    assert row["weight_l1_difference_pp"] == 0.0
    assert row["max_single_fund_weight_change_pp"] == 0.0
    assert row["changed_fund_count"] == 0
    assert row["funds_added_in_b"] == ""
    assert row["funds_removed_in_b"] == ""
