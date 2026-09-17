from __future__ import annotations

import csv
from pathlib import Path

import pytest

from final.archival import archive_final_summaries


def _write_summary(output: Path, purpose: str, text: str = "purpose,metric\n") -> None:
    (output / f"final_{purpose}_summary.csv").write_text(text, encoding="utf-8")


def _write_checkpoint(output: Path, purpose: str) -> None:
    (output / f"final_{purpose}_checkpoint.json").write_text(
        '{"contract_version":"1","purpose":"%s","purpose_horizon_years":7,'
        '"mission_sha256":"abc","bootstrap_resamples":5000,"bootstrap_seed":20260906}\n' % purpose,
        encoding="utf-8",
    )


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_archives_selected_summaries_as_one_lfs_snapshot(tmp_path: Path):
    output = tmp_path / "output"
    archive = tmp_path / "lfs"
    output.mkdir()
    for purpose in ("Retirement", "Edu_B"):
        _write_summary(output, purpose, f"purpose,metric\n{purpose},value\n")
        _write_checkpoint(output, purpose)

    archived = archive_final_summaries(
        "2026-09-06", ["Retirement", "Edu_B"], output_dir=output, archive_root=archive, final_contract_version="1"
    )

    assert [path.name for path in archived] == ["purpose_summaries.csv"]
    rows = _rows(archive / "purpose_summaries.csv")
    assert [row["purpose"] for row in rows] == ["Edu_B", "Retirement"]
    assert all(row["as_of"] == "2026-09-06" for row in rows)


def test_archival_identical_rerun_is_idempotent(tmp_path: Path):
    output = tmp_path / "output"
    archive = tmp_path / "lfs"
    output.mkdir()
    _write_summary(output, "Retirement", "purpose,metric\nRetirement,value\n")
    _write_checkpoint(output, "Retirement")

    first = archive_final_summaries(
        "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
    )
    before = (archive / "purpose_summaries.csv").read_text(encoding="utf-8")
    second = archive_final_summaries(
        "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
    )
    after = (archive / "purpose_summaries.csv").read_text(encoding="utf-8")

    assert [path.name for path in first] == ["purpose_summaries.csv"]
    assert [path.name for path in second] == ["purpose_summaries.csv"]
    assert after == before


def test_archival_replaces_selected_purpose_row(tmp_path: Path):
    output = tmp_path / "output"
    archive = tmp_path / "lfs"
    output.mkdir()
    _write_summary(output, "Retirement", "purpose,metric\nRetirement,First\n")
    _write_checkpoint(output, "Retirement")
    archive_final_summaries(
        "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
    )

    _write_summary(output, "Retirement", "purpose,metric\nRetirement,Second\n")
    archive_final_summaries(
        "2026-09-07", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
    )

    rows = _rows(archive / "purpose_summaries.csv")
    assert rows == [{"as_of": "2026-09-07", "purpose": "Retirement", "metric": "Second"}]


def test_partial_run_preserves_unselected_purposes(tmp_path: Path):
    output = tmp_path / "output"
    archive = tmp_path / "lfs"
    output.mkdir()
    for purpose in ("Retirement", "Edu_B"):
        _write_summary(output, purpose, f"purpose,metric\n{purpose},first\n")
        _write_checkpoint(output, purpose)

    archive_final_summaries(
        "2026-09-06", ["Retirement", "Edu_B"], output_dir=output, archive_root=archive, final_contract_version="1"
    )
    _write_summary(output, "Edu_B", "purpose,metric\nEdu_B,second\n")
    archive_final_summaries(
        "2026-09-07", ["Edu_B"], output_dir=output, archive_root=archive, final_contract_version="1"
    )

    rows = {row["purpose"]: row for row in _rows(archive / "purpose_summaries.csv")}
    assert rows["Edu_B"]["metric"] == "second"
    assert rows["Edu_B"]["as_of"] == "2026-09-07"
    assert rows["Retirement"]["metric"] == "first"
    assert rows["Retirement"]["as_of"] == "2026-09-06"


def test_archival_requires_requested_summary_and_valid_contract(tmp_path: Path):
    output = tmp_path / "output"
    archive = tmp_path / "lfs"
    output.mkdir()
    _write_summary(output, "Retirement")

    with pytest.raises(FileNotFoundError):
        archive_final_summaries(
            "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
        )

    _write_summary(output, "Retirement", "purpose,metric\nRetirement,value\n")
    _write_checkpoint(output, "Retirement")
    checkpoint = output / "final_Retirement_checkpoint.json"
    checkpoint.write_text(
        checkpoint.read_text(encoding="utf-8").replace('"contract_version":"1"', '"contract_version":"2"'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        archive_final_summaries(
            "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
        )
