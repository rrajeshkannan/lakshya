from __future__ import annotations

import csv
from pathlib import Path

from family.review_surface import refresh_review_surface


def _read(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_review_surface_normalizes_money_and_connects_final_evidence(tmp_path: Path):
    data = tmp_path / "data"
    staging = data / "reviews" / "2026-09-06" / "purpose_staging"
    staging.mkdir(parents=True)
    (staging / "purposes_staged.csv").write_text(
        "name,due,value,desired,monthly_plan\n"
        "A,2036-01-01,2.35715e+06,5500000,40000\n"
        "B,NA,341588,,\n",
        encoding="utf-8",
    )
    review = data / "reviews" / "2026-09-06"
    (review / "A_summary.csv").write_text(
        "purpose,purpose_horizon_years,primary_winner,contract_version\n"
        'A,9,"X|X=1.0000",1\n',
        encoding="utf-8",
    )
    output = tmp_path / "output"
    output.mkdir()
    (output / "achievability_A.csv").write_text(
        "composition,status,required_annual_return,comparison_horizon_years,observed_upper_return\n"
        "X|X=1.0000,within_observed_terrain,0.05,9,0.10\n",
        encoding="utf-8",
    )

    result = refresh_review_surface("2026-09-06", data_dir=data)
    rows = {row["purpose"]: row for row in _read(result)}
    assert rows["A"]["current_corpus"] == "2357150.00"
    assert rows["A"]["target_corpus"] == "5500000.00"
    assert rows["A"]["gap_today"] == "-3142850.00"
    assert rows["A"]["monthly_sip"] == "40000.00"
    assert rows["A"]["horizon_years"] == "9"
    assert rows["A"]["selected_composition"] == "X|X=1.0000"
    assert rows["A"]["selected_formation"] == "X:100%"
    assert rows["A"]["observed_terrain"] == "observed terrain demonstrated by selected FINAL formation"
    assert "observed_upper_return" not in rows["A"]
    assert rows["A"]["achievability_status"] == "within_observed_terrain"
    assert rows["B"]["achievability_status"] == "not_applicable"

    staged = _read(staging / "purposes_staged.csv")
    assert staged[0]["value"] == "2357150.00"
