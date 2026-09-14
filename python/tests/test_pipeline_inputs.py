from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from mission.pipeline_inputs import load_fund_histories, load_purposes


def test_load_fund_histories_reads_one_json_per_fund_and_applies_as_of(tmp_path: Path):
    nav_dir = tmp_path / "nav"
    nav_dir.mkdir()
    (nav_dir / "FUND1.json").write_text(
        '{"observations": ['
        '{"date": "2026-08-30", "nav": 100.0}, '
        '{"date": "2026-09-01", "nav": 101.0}'
        ']}',
        encoding="utf-8",
    )

    histories = load_fund_histories(
        [SimpleNamespace(isin="FUND1")],
        nav_dir=nav_dir,
        as_of=pd.Timestamp("2026-08-31"),
    )

    assert list(histories) == ["FUND1"]
    assert histories["FUND1"]["date"].tolist() == [pd.Timestamp("2026-08-30")]
    assert histories["FUND1"]["nav"].tolist() == [100.0]


def test_load_fund_histories_reports_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="MISSING"):
        load_fund_histories(
            [SimpleNamespace(isin="MISSING")],
            nav_dir=tmp_path,
            as_of=pd.Timestamp("2026-08-31"),
        )


def _floor_years(start: pd.Timestamp, due: pd.Timestamp) -> int:
    return due.year - start.year - int((due.month, due.day) < (start.month, start.day))


def test_load_purposes_preserves_finite_due_date_horizon(tmp_path: Path):
    path = tmp_path / "purposes.csv"
    path.write_text(
        "name,due,value,desired,monthly_plan,analytical_horizon_years\n"
        "Education,2030-09-14,100000,500000,10000,\n",
        encoding="utf-8",
    )

    purposes = load_purposes(path, as_of=pd.Timestamp("2026-09-14"), floor_years=_floor_years)

    assert len(purposes) == 1
    assert purposes[0].name == "Education"
    assert purposes[0].trajectory_horizon_years == 4


def test_load_purposes_supports_na_due_with_analytical_horizon(tmp_path: Path):
    path = tmp_path / "purposes.csv"
    path.write_text(
        "name,due,value,desired,monthly_plan,analytical_horizon_years\n"
        "Legacy,NA,250000,,,12\n",
        encoding="utf-8",
    )

    purposes = load_purposes(path, as_of=pd.Timestamp("2026-09-14"), floor_years=_floor_years)

    assert len(purposes) == 1
    assert purposes[0].name == "Legacy"
    assert purposes[0].trajectory_horizon_years == 12


def test_load_purposes_rejects_missing_required_column(tmp_path: Path):
    path = tmp_path / "purposes.csv"
    path.write_text(
        "name,due,value,desired,monthly_plan\n"
        "Education,2030-09-14,100000,500000,10000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required columns"):
        load_purposes(path, as_of=pd.Timestamp("2026-09-14"), floor_years=_floor_years)


def test_load_purposes_rejects_due_date_not_beyond_as_of(tmp_path: Path):
    path = tmp_path / "purposes.csv"
    path.write_text(
        "name,due,value,desired,monthly_plan,analytical_horizon_years\n"
        "Expired,2026-09-14,100000,500000,10000,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not beyond as-of date"):
        load_purposes(path, as_of=pd.Timestamp("2026-09-14"), floor_years=_floor_years)


def test_load_purposes_rejects_na_due_without_analytical_horizon(tmp_path: Path):
    path = tmp_path / "purposes.csv"
    path.write_text(
        "name,due,value,desired,monthly_plan,analytical_horizon_years\n"
        "Open,NA,250000,,,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires analytical_horizon_years"):
        load_purposes(path, as_of=pd.Timestamp("2026-09-14"), floor_years=_floor_years)
