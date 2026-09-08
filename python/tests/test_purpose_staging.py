from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from family.staging import commit_staging, initialize_staging, run_turn

TURN_HEADER = "purpose,value,monthly_plan,desired,due,analytical_horizon_years,capital_acquire_pct,sip_acquire_pct\n"
POSITIONS_HEADER = "investor,folio,isin,units,nav,market_value,purpose\n"


def _fixture(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    purpose = data / "purpose" / "purposes.csv"
    purpose.parent.mkdir(parents=True)
    purpose.write_text(
        "name,due,desired,monthly_plan\n"
        "A,2036-01-01,2000,10\n"
        "B,2036-01-01,1000,10\n",
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
