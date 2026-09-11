from __future__ import annotations

import csv
from pathlib import Path

from family.staging import initialize_staging
from family.staging_history import write_turn_template

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
    return data


def _read(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_turn_template_contains_the_whole_family(tmp_path: Path):
    data = _fixture(tmp_path)
    directory = initialize_staging("2026-09-06", data_dir=data)
    template = write_turn_template(directory)
    rows = _read(template)
    assert [row["purpose"] for row in rows] == ["A", "B"]
    assert rows[0]["value"] == "100.00"
    assert rows[1]["value"] == "200.00"
    assert rows[0]["monthly_plan"] == "10"
    assert rows[0]["capital_acquire_pct"] == ""
    assert rows[0]["sip_acquire_pct"] == ""
