from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from family.staging import initialize_staging, run_turn
from family.staging_history import snapshot_current_staging

TURN_HEADER = "purpose,value,monthly_plan,desired,due,capital_acquire_pct,sip_acquire_pct\n"
POSITIONS_HEADER = "investor,folio,isin,units,nav,market_value,purpose\n"


def _fixture(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    purpose = data / "purpose" / "purposes.csv"
    purpose.parent.mkdir(parents=True)
    purpose.write_text(
        "name,due,desired,monthly_plan\n"
        "A,2036-01-01,1800,10\n"
        "B,2036-01-01,2000,10\n",
        encoding="utf-8",
    )
    positions = data / "lps" / "positions.csv"
    positions.parent.mkdir(parents=True)
    positions.write_text(
        POSITIONS_HEADER
        + "Amma,F1,PA,1,100,100,A\n"
        + "Amma,F2,PB,1,200,200,B\n",
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


def test_snapshot_preserves_turn_zero_and_refuses_overwrite(tmp_path: Path):
    data = _fixture(tmp_path)
    directory = initialize_staging("2026-09-06", data_dir=data)
    snapshot = snapshot_current_staging(directory)
    assert snapshot.name == "turn_000"
    for name in (
        "purposes_staged.csv",
        "achievability_latest.csv",
        "reconciliation_ledger.csv",
        "staging_state.json",
    ):
        assert (snapshot / name).is_file()
    with pytest.raises(FileExistsError):
        snapshot_current_staging(directory)


def test_snapshot_preserves_each_completed_turn_as_immutable_state(tmp_path: Path):
    data = _fixture(tmp_path)
    directory = initialize_staging("2026-09-06", data_dir=data)
    snapshot_current_staging(directory)

    run_turn("2026-09-06", _turn(tmp_path, "A,80,5,,,,\n"), data_dir=data)
    snapshot_one = snapshot_current_staging(directory)
    assert snapshot_one.name == "turn_001"
    one_rows = _read(snapshot_one / "purposes_staged.csv")
    assert float(next(r for r in one_rows if r["name"] == "A")["value"]) == pytest.approx(80.0)

    run_turn("2026-09-06", _turn(tmp_path, "A,70,5,,,,\n"), data_dir=data)
    snapshot_two = snapshot_current_staging(directory)
    assert snapshot_two.name == "turn_002"
    two_rows = _read(snapshot_two / "purposes_staged.csv")
    assert float(next(r for r in two_rows if r["name"] == "A")["value"]) == pytest.approx(70.0)

    # Earlier history remains unchanged after later turns.
    one_rows_after = _read(snapshot_one / "purposes_staged.csv")
    assert float(next(r for r in one_rows_after if r["name"] == "A")["value"]) == pytest.approx(80.0)

    state = json.loads((snapshot_two / "staging_state.json").read_text(encoding="utf-8"))
    assert state["turn"] == 2


def test_snapshot_captures_review_surface_when_present(tmp_path: Path):
    data = _fixture(tmp_path)
    directory = initialize_staging("2026-09-06", data_dir=data)
    (directory / "purpose_review_latest.csv").write_text(
        "purpose,current_corpus\nA,100\n",
        encoding="utf-8",
    )
    snapshot = snapshot_current_staging(directory)
    assert (snapshot / "purpose_review.csv").read_text(encoding="utf-8") == (
        "purpose,current_corpus\nA,100\n"
    )
