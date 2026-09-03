from __future__ import annotations

import csv

import pytest

from mission.purpose_composition_map import (
    build_purpose_composition_map,
    parse_composition_identity,
    write_purpose_composition_map,
)


A95_B05 = "A,B|A=0.95,B=0.05"
A05_B95 = "A,B|A=0.05,B=0.95"
A50_B50 = "A,B|A=0.50,B=0.50"
C100 = "C|C=1.00"


def test_parse_composition_identity_preserves_members_and_weights():
    members, weights = parse_composition_identity(A95_B05)
    assert members == ("A", "B")
    assert weights == {"A": 0.95, "B": 0.05}


def test_map_distinguishes_exact_composition_from_fund_set():
    survivors = {"Edu_B": [A95_B05, A05_B95, A50_B50]}
    map_rows, summary_rows, exposure_rows, overlap_rows = build_purpose_composition_map(survivors)

    assert len(map_rows) == 3
    assert summary_rows[0]["unique_exact_compositions"] == 3
    assert summary_rows[0]["unique_fund_sets"] == 1
    assert summary_rows[0]["unique_teams"] == 1
    assert summary_rows[0]["pair_count"] == 3
    assert exposure_rows[0]["isin"] == "A"
    assert exposure_rows[0]["presence_pct"] == pytest.approx(100.0)
    assert overlap_rows == []


def test_cross_purpose_overlap_counts_exact_and_membership_levels():
    survivors = {
        "Edu_B": [A95_B05, C100],
        "Marriage": [A95_B05, A50_B50],
    }
    _, _, _, overlap_rows = build_purpose_composition_map(survivors)

    assert len(overlap_rows) == 1
    row = overlap_rows[0]
    assert row["exact_composition_overlap"] == 1
    assert row["fund_set_overlap"] == 1
    assert row["team_overlap"] == 1


def test_fund_set_and_team_identity_are_explicitly_equivalent():
    survivors = {"Stitch": [A95_B05, A05_B95, C100]}
    map_rows, summary_rows, _, _ = build_purpose_composition_map(survivors)

    assert all(row["team"] == row["fund_set"] for row in map_rows)
    assert summary_rows[0]["fund_set_equals_team_identity"] is True


def test_empty_or_duplicate_survivors_are_rejected():
    with pytest.raises(ValueError):
        build_purpose_composition_map({})
    with pytest.raises(ValueError):
        build_purpose_composition_map({"Edu_B": []})
    with pytest.raises(ValueError):
        build_purpose_composition_map({"Edu_B": [A95_B05, A95_B05]})


def test_artifacts_are_written_with_separate_deterministic_schemas(tmp_path):
    paths = write_purpose_composition_map(
        {"Edu_B": [A95_B05, A05_B95], "Marriage": [A95_B05]},
        output_dir=tmp_path,
    )

    assert [path.name for path in paths] == [
        "purpose_composition_map.csv",
        "purpose_composition_summary.csv",
        "purpose_fund_exposure.csv",
        "purpose_overlap.csv",
    ]
    with paths[1].open(newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))
    with paths[2].open(newline="", encoding="utf-8") as handle:
        exposure = list(csv.DictReader(handle))
    with paths[3].open(newline="", encoding="utf-8") as handle:
        overlap = list(csv.DictReader(handle))

    assert len(summary) == 2
    assert len(exposure) == 4
    assert {(row["purpose"], row["isin"]) for row in exposure} == {
        ("Edu_B", "A"),
        ("Edu_B", "B"),
        ("Marriage", "A"),
        ("Marriage", "B"),
    }
    assert len(overlap) == 1
