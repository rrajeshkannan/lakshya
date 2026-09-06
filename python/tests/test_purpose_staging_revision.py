from __future__ import annotations

import csv
import json
from pathlib import Path

from family.staging import commit_staging, initialize_staging, run_turn

TURN_HEADER = "purpose,value,monthly_plan,desired,due,analytical_horizon_years,capital_acquire_pct,sip_acquire_pct\n"


def _fixture(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    purpose = data / "purpose" / "purposes.csv"
    purpose.parent.mkdir(parents=True)
    purpose.write_text(
        "name,due,value,desired,monthly_plan,analytical_horizon_years\n"
        "A,2036-01-01,100,2000,10,\n"
        "B,2036-01-01,200,1000,10,\n"
        "C,2036-01-01,300,1000,10,\n",
        encoding="utf-8",
    )
    review = data / "reviews" / "2026-09-06"
    review.mkdir(parents=True)
    for name in ("A", "B", "C"):
        (review / f"{name}_summary.csv").write_text(
            "purpose,purpose_horizon_years,primary_winner,contract_version\n"
            f'{name},10,"X|X=1.0000",1\n',
            encoding="utf-8",
        )
    output = tmp_path / "output"
    output.mkdir()
    for name in ("A", "B", "C"):
        (output / f"achievability_{name}.csv").write_text(
            "composition,status,required_annual_return,comparison_horizon_years,observed_upper_return\n"
            "X|X=1.0000,within_observed_terrain,0.05,10,0.10\n",
            encoding="utf-8",
        )
    return data


def _turn(tmp_path: Path, rows: str, suffix: str) -> Path:
    path = tmp_path / f"turn_{suffix}.csv"
    path.write_text(TURN_HEADER + rows, encoding="utf-8")
    return path


def _read(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _state(data: Path) -> dict:
    path = data / "reviews" / "2026-09-06" / "purpose_staging" / "staging_state.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_working_revision_tracks_turns_without_resetting_cumulative_pool(tmp_path: Path):
    data = _fixture(tmp_path)
    initialize_staging("2026-09-06", data_dir=data)
    assert _state(data)["working_revision"] == 0

    # Turn 1 releases 100 into the pool.
    run_turn("2026-09-06", _turn(tmp_path, "A,0,10,,,,,\n", "one"), data_dir=data)
    assert _state(data)["working_revision"] == 1
    assert _state(data)["pool_capital"] == 100.0

    # Turn 2 consumes 60% of the existing pool; it must start from 100, not
    # from the original Purpose source.
    run_turn("2026-09-06", _turn(tmp_path, "B,,,,,,60,\n", "two"), data_dir=data)
    assert _state(data)["working_revision"] == 2
    assert _state(data)["pool_capital"] == 40.0

    # Turn 3 consumes the remaining 40%; working-file replacement must preserve
    # the state produced by turns 1 and 2.
    run_turn("2026-09-06", _turn(tmp_path, "C,,,,,,100,\n", "three"), data_dir=data)
    assert _state(data)["working_revision"] == 3
    assert _state(data)["pool_capital"] == 0.0

    staging = data / "reviews" / "2026-09-06" / "purpose_staging"
    ledger = _read(staging / "reconciliation_ledger.csv")
    assert [row["turn"] for row in ledger] == ["1", "2", "3"]
    assert [row["kind"] for row in ledger] == ["RELEASE_CAPITAL", "ACQUIRE_CAPITAL", "ACQUIRE_CAPITAL"]
    assert [float(row["pool_after"]) for row in ledger] == [100.0, 40.0, 0.0]


def test_commit_records_final_working_revision(tmp_path: Path):
    data = _fixture(tmp_path)
    initialize_staging("2026-09-06", data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "A,0,10,,,,,\n", "one"), data_dir=data)
    run_turn("2026-09-06", _turn(tmp_path, "B,,,,,,100,\n", "two"), data_dir=data)

    commit_staging("2026-09-06", data_dir=data)
    state = _state(data)
    assert state["status"] == "COMMITTED"
    assert state["working_revision"] == 2
    assert state["committed_working_revision"] == 2
