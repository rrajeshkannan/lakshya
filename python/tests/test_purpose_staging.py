from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from family.staging import commit_staging, initialize_staging, run_turn

TURN_HEADER = "purpose,value,monthly_plan,desired,due,analytical_horizon_years,capital_acquire_pct,sip_acquire_pct\n"


def _fixture(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    purpose = data / "purpose" / "purposes.csv"
    purpose.parent.mkdir(parents=True)
    purpose.write_text(
        "name,due,value,desired,monthly_plan,analytical_horizon_years\n"
        "A,2036-01-01,100,300,10,\n"
        "B,2036-01-01,200,300,10,\n",
        encoding="utf-8",
    )
    review = data / "reviews" / "2026-09-06"
    review.mkdir(parents=True)
    for name in ("A", "B"):
        (review / f"{name}_summary.csv").write_text(
            "purpose,purpose_horizon_years,primary_winner,contract_version\n"
            f'{name},10,"X|X=1.0000",1\n',
            encoding="utf-8",
        )
    output = tmp_path / "output"
    output.mkdir()
    for name in ("A", "B"):
        (output / f"achievability_{name}.csv").write_text(
            "composition,status,required_annual_return,comparison_horizon_years,observed_upper_return\n"
            "X|X=1.0000,within_observed_terrain,0.05,10,0.10\n",
            encoding="utf-8",
        )
    return data


def _turn(tmp_path: Path, rows: str) -> Path:
    path = tmp_path / "turn.csv"
    path.write_text(TURN_HEADER + rows, encoding="utf-8")
    return path


def _read(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_initialize_isolates_staged_state_from_authoritative_source(tmp_path: Path):
    data = _fixture(tmp_path)
    source = data / "purpose" / "purposes.csv"
    original = source.read_text(encoding="utf-8")
    directory = initialize_staging("2026-09-06", data_dir=data)
    assert source.read_text(encoding="utf-8") == original
    assert (directory / "purposes_staged.csv").is_file()
    assert (directory / "reconciliation_ledger.csv").is_file()
    assert (directory / "achievability_latest.csv").is_file()
    assert (directory / "staging_state.json").is_file()
    assert (directory / "staging.log").is_file()


def test_turn_releases_capital_and_sip_and_records_ledger(tmp_path: Path):
    data = _fixture(tmp_path)
    initialize_staging("2026-09-06", data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "A,80,5,,,,,\n"), data_dir=data)
    staging = data / "reviews" / "2026-09-06" / "purpose_staging"
    state = json.loads((staging / "staging_state.json").read_text(encoding="utf-8"))
    assert state["pool_capital"] == pytest.approx(20.0)
    assert state["pool_monthly_sip"] == pytest.approx(5.0)
    ledger = _read(staging / "reconciliation_ledger.csv")
    assert {row["kind"] for row in ledger} == {"RELEASE_CAPITAL", "RELEASE_SIP"}


def test_acquisition_percentage_updates_recipient_and_leaves_unallocated_pool(tmp_path: Path):
    data = _fixture(tmp_path)
    initialize_staging("2026-09-06", data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "A,50,10,,,,,\n"), data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "B,,,,,,60,\n"), data_dir=data)
    staging = data / "reviews" / "2026-09-06" / "purpose_staging"
    rows = _read(staging / "purposes_staged.csv")
    b = next(row for row in rows if row["name"] == "B")
    # 50 was released from A; 60% of that pool is acquired by B.
    assert float(b["value"]) == pytest.approx(230.0)
    state = json.loads((staging / "staging_state.json").read_text(encoding="utf-8"))
    assert state["pool_capital"] == pytest.approx(20.0)


def test_acquisition_percentages_cannot_exceed_100(tmp_path: Path):
    data = _fixture(tmp_path)
    initialize_staging("2026-09-06", data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "A,50,10,,,,,\n"), data_dir=data)
    with pytest.raises(ValueError, match="cannot exceed 100"):
        run_turn(
            "2026-09-06",
            _turn(tmp_path, "A,,,,,,70,\nB,,,,,,40,\n"),
            data_dir=data,
        )


def test_achievability_is_recomputed_after_each_turn(tmp_path: Path):
    data = _fixture(tmp_path)
    initialize_staging("2026-09-06", data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "A,,,,,,,\n"), data_dir=data)
    staging = data / "reviews" / "2026-09-06" / "purpose_staging"
    initial = {row["purpose"]: row for row in _read(staging / "achievability_latest.csv")}
    assert set(initial) == {"A", "B"}
    assert initial["A"]["status"] == "within_observed_terrain"
    assert initial["B"]["status"] == "within_observed_terrain"

    run_turn("2026-09-06", _turn(tmp_path, "A,50,10,,,,,\n"), data_dir=data)
    latest = {row["purpose"]: row for row in _read(staging / "achievability_latest.csv")}
    assert set(latest) == {"A", "B"}
    assert float(latest["A"]["required_annual_return"]) > float(initial["A"]["required_annual_return"])
    assert float(latest["B"]["required_annual_return"]) == pytest.approx(float(initial["B"]["required_annual_return"]))
    assert latest["A"]["status"] == "within_observed_terrain"
    assert latest["B"]["status"] == "within_observed_terrain"


def test_commit_blocks_with_nonempty_pool(tmp_path: Path):
    data = _fixture(tmp_path)
    initialize_staging("2026-09-06", data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "A,80,10,,,,,\n"), data_dir=data)
    with pytest.raises(ValueError, match="common-pool balances remain"):
        commit_staging("2026-09-06", data_dir=data)


def test_commit_preserves_authoritative_backup_and_marks_workspace(tmp_path: Path):
    data = _fixture(tmp_path)
    initialize_staging("2026-09-06", data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "A,80,10,,,,,\n"), data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "B,,,,,,100,\n"), data_dir=data)
    source = data / "purpose" / "purposes.csv"
    original = source.read_text(encoding="utf-8")
    commit_staging("2026-09-06", data_dir=data)
    staging = data / "reviews" / "2026-09-06" / "purpose_staging"
    assert (staging / "purposes_before_commit.csv").read_text(encoding="utf-8") == original
    state = json.loads((staging / "staging_state.json").read_text(encoding="utf-8"))
    assert state["status"] == "COMMITTED"
    assert "COMMIT" in (staging / "staging.log").read_text(encoding="utf-8")
