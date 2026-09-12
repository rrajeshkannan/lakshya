from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from family.staging import initialize_staging, run_turn

TURN_HEADER = "purpose,value,monthly_plan,desired,due,capital_acquire_pct,sip_acquire_pct\n"
POSITIONS_HEADER = "investor,folio,isin,units,nav,market_value,purpose\n"


def _write_review(data: Path, as_of: str, purpose: str, winner: str = "X|X=1.0000") -> None:
    review = data / "reviews" / as_of
    review.mkdir(parents=True, exist_ok=True)
    (review / f"{purpose}_summary.csv").write_text(
        "purpose,purpose_horizon_years,primary_winner,contract_version\n"
        f'{purpose},9,"{winner}",1\n',
        encoding="utf-8",
    )


def _write_checkpoint(tmp_path: Path, purpose: str, upper: float = 0.10) -> None:
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    (output / f"achievability_{purpose}.csv").write_text(
        "composition,status,required_annual_return,comparison_horizon_years,observed_upper_return\n"
        f"X|X=1.0000,within_observed_terrain,0.05,9,{upper:.2f}\n",
        encoding="utf-8",
    )


def _turn(tmp_path: Path, rows: str) -> Path:
    path = tmp_path / "turn.csv"
    path.write_text(TURN_HEADER + rows, encoding="utf-8")
    return path


def _read(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_open_purpose_does_not_require_observed_terrain(tmp_path: Path):
    data = tmp_path / "data"
    purpose = data / "purpose" / "purposes.csv"
    purpose.parent.mkdir(parents=True)
    purpose.write_text(
        "name,due,desired,monthly_plan\n"
        "A,2036-01-01,1800,10\n"
        "Open,NA,,\n",
        encoding="utf-8",
    )
    positions = data / "lps" / "positions.csv"
    positions.parent.mkdir(parents=True)
    positions.write_text(
        POSITIONS_HEADER
        + "Amma,F1,PA,1,100,100,A\n"
        + "Amma,F2,PO,1,50,50,Open\n",
        encoding="utf-8",
    )
    _write_review(data, "2026-09-06", "A")
    _write_review(data, "2026-09-06", "Open")
    _write_checkpoint(tmp_path, "A")

    directory = initialize_staging("2026-09-06", data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "A,,,,,,\n"), data_dir=data)

    results = {row["purpose"]: row for row in _read(directory / "achievability_latest.csv")}
    assert results["A"]["status"] == "within_observed_terrain"
    assert results["Open"]["status"] == "not_applicable"
    assert results["Open"]["observed_upper_return"] == ""


def test_failed_evidence_validation_leaves_staging_workspace_unchanged(tmp_path: Path):
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
    _write_review(data, "2026-09-06", "A")
    _write_review(data, "2026-09-06", "B")
    _write_checkpoint(tmp_path, "A")

    directory = initialize_staging("2026-09-06", data_dir=data)
    paths = [
        directory / "purposes_staged.csv",
        directory / "reconciliation_ledger.csv",
        directory / "achievability_latest.csv",
        directory / "staging_state.json",
        directory / "staging.log",
    ]
    before = {path.name: path.read_bytes() for path in paths}

    with pytest.raises(FileNotFoundError, match="Achievability checkpoint missing"):
        run_turn("2026-09-06", _turn(tmp_path, "A,80,5,,,,\n"), data_dir=data)

    after = {path.name: path.read_bytes() for path in paths}
    assert after == before

    state = json.loads((directory / "staging_state.json").read_text(encoding="utf-8"))
    assert state["turn"] == 0
    assert state["working_revision"] == 0
    assert state["pool_capital"] == 0.0
    assert state["pool_monthly_sip"] == 0.0
