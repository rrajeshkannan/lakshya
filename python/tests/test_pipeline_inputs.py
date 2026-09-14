from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from mission.pipeline_inputs import load_fund_histories


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
    assert histories["FUND1"]["date"].tolist() == [
        pd.Timestamp("2026-08-30")
    ]
    assert histories["FUND1"]["nav"].tolist() == [100.0]


def test_load_fund_histories_reports_missing_file(tmp_path: Path):
    try:
        load_fund_histories(
            [SimpleNamespace(isin="MISSING")],
            nav_dir=tmp_path,
            as_of=pd.Timestamp("2026-08-31"),
        )
    except FileNotFoundError as error:
        assert "MISSING" in str(error)
    else:
        raise AssertionError("missing NAV evidence should raise FileNotFoundError")
