from datetime import date
from pathlib import Path

from mission.purpose_loader import load_purposes


def test_load_purposes_accepts_human_due_date_format(tmp_path: Path):
    purposes = tmp_path / "purposes.csv"
    purposes.write_text(
        "name,due,desired,monthly_plan\n"
        "Edu_B,01-Jan-2031,5500000,40000\n"
        "Kutti,NA,,\n",
        encoding="utf-8",
    )
    positions = tmp_path / "positions.csv"
    positions.write_text(
        "investor,folio,isin,units,nav,market_value,purpose\n"
        "Amma,F1,ISIN1,1,100,2400000,Edu_B\n"
        "Amma,F2,ISIN2,1,100,335000,Kutti\n",
        encoding="utf-8",
    )

    loaded = load_purposes(
        date(2026, 9, 8),
        purposes_path=purposes,
        positions_path=positions,
    )

    edu = next(p for p in loaded if p.name == "Edu_B")
    kutti = next(p for p in loaded if p.name == "Kutti")
    assert edu.due == date(2031, 1, 1)
    assert edu.horizon_years == 4
    assert edu.capital == 2400000
    assert kutti.due is None
    assert kutti.trajectory_horizon_years == 7
    assert kutti.capital == 335000
