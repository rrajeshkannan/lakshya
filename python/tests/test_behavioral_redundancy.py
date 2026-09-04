from __future__ import annotations

import pandas as pd
import pytest

from mission.behavioral_redundancy import (
    _align_paths,
    _metrics,
    build_nearest_rows,
    build_pairwise_rows,
    parse_members,
)


def path(values, elapsed=None):
    if elapsed is None:
        elapsed = list(range(len(values)))
    return pd.DataFrame({"elapsed_days": elapsed, "normalized_nav": values})


def test_parse_members_uses_native_composition_identity():
    assert parse_members("A,B,C|A=0.8,B=0.1,C=0.1") == ("A", "B", "C")


def test_align_paths_uses_common_elapsed_days_without_inventing_values():
    left = path([1.0, 1.1, 1.2], [0, 1, 2])
    right = path([1.0, 1.05, 1.1], [1, 2, 3])
    result = _align_paths(left, right)
    assert result["elapsed_days"].tolist() == [1, 2]
    assert result["nav_a"].tolist() == [1.1, 1.2]
    assert result["nav_b"].tolist() == [1.0, 1.05]


def test_identical_paths_have_zero_level_and_cagr_drawdown_difference():
    metrics = _metrics(path([1.0, 1.1, 1.05, 1.2]), path([1.0, 1.1, 1.05, 1.2]))
    assert metrics["mean_abs_level_gap_pct_points"] == pytest.approx(0.0)
    assert metrics["max_abs_level_gap_pct_points"] == pytest.approx(0.0)
    assert metrics["cagr_difference_pp"] == pytest.approx(0.0)
    assert metrics["max_drawdown_difference_pp"] == pytest.approx(0.0)
    assert metrics["daily_return_correlation"] == pytest.approx(1.0)


def test_pairwise_rows_compare_each_unique_pair_without_ranking():
    paths = {
        "A|A=0.5000": path([1.0, 1.1, 1.2]),
        "B|B=1.0000": path([1.0, 1.05, 1.1]),
        "C|C=1.0000": path([1.0, 0.9, 1.0]),
    }
    rows = build_pairwise_rows("Edu_B", list(paths), paths)
    assert len(rows) == 3
    assert {(row["composition_a"], row["composition_b"]) for row in rows} == {
        ("A|A=0.5000", "B|B=1.0000"),
        ("A|A=0.5000", "C|C=1.0000"),
        ("B|B=1.0000", "C|C=1.0000"),
    }
    assert all("score" not in row for row in rows)


def test_nearest_rows_are_metric_specific_not_a_composite_score():
    pairwise = [
        {
            "purpose": "Edu_B",
            "composition_a": "A|A=1.0000",
            "composition_b": "B|B=1.0000",
            "mean_abs_level_gap_pct_points": 1.0,
            "max_abs_level_gap_pct_points": 3.0,
            "daily_return_correlation": 0.90,
            "cagr_difference_pp": 0.5,
            "max_drawdown_difference_pp": -0.2,
        },
        {
            "purpose": "Edu_B",
            "composition_a": "A|A=1.0000",
            "composition_b": "C|C=1.0000",
            "mean_abs_level_gap_pct_points": 2.0,
            "max_abs_level_gap_pct_points": 2.0,
            "daily_return_correlation": 0.95,
            "cagr_difference_pp": -0.1,
            "max_drawdown_difference_pp": 0.8,
        },
    ]
    rows = build_nearest_rows(pairwise)
    assert len(rows) == 10
    assert {row["relationship_metric"] for row in rows} == {
        "mean_abs_level_gap_pct_points",
        "max_abs_level_gap_pct_points",
        "daily_return_correlation",
        "cagr_difference_pp",
        "max_drawdown_difference_pp",
    }
    assert all("score" not in row for row in rows)
    correlation_row = next(
        row for row in rows
        if row["composition"] == "A|A=1.0000" and row["relationship_metric"] == "daily_return_correlation"
    )
    assert correlation_row["nearest_composition"] == "C|C=1.0000"
