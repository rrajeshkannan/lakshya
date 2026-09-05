from __future__ import annotations

import json
from pathlib import Path

import pytest

from final.archival import archive_final_summaries


def _write_summary(output: Path, purpose: str, text: str = "purpose,metric\n") -> None:
    (output / f"final_{purpose}_summary.csv").write_text(text, encoding="utf-8")


def _write_checkpoint(output: Path, purpose: str) -> None:
    (output / f"final_{purpose}_checkpoint.json").write_text(
        json.dumps(
            {
                "contract_version": "1",
                "purpose": purpose,
                "purpose_horizon_years": 7,
                "mission_sha256": "abc",
                "bootstrap_resamples": 5000,
                "bootstrap_seed": 20260906,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_archives_selected_summaries_and_manifest(tmp_path: Path):
    output = tmp_path / "output"
    archive = tmp_path / "reviews"
    output.mkdir()
    for purpose in ("Retirement", "Edu_B"):
        _write_summary(output, purpose, f"purpose\n{purpose}\n")
        _write_checkpoint(output, purpose)

    archived = archive_final_summaries(
        "2026-09-06",
        ["Retirement", "Edu_B"],
        output_dir=output,
        archive_root=archive,
        final_contract_version="1",
    )

    assert [path.name for path in archived] == ["Edu_B_summary.csv", "Retirement_summary.csv"]
    review_dir = archive / "2026-09-06"
    assert (review_dir / "Edu_B_summary.csv").read_text(encoding="utf-8") == "purpose\nEdu_B\n"
    assert (review_dir / "Retirement_summary.csv").exists()
    manifest = json.loads((review_dir / "review_manifest.json").read_text(encoding="utf-8"))
    assert manifest["archive_schema_version"] == 1
    assert manifest["as_of"] == "2026-09-06"
    assert [item["purpose"] for item in manifest["purposes"]] == ["Edu_B", "Retirement"]


def test_archival_is_idempotent_for_identical_existing_record(tmp_path: Path):
    output = tmp_path / "output"
    archive = tmp_path / "reviews"
    output.mkdir()
    _write_summary(output, "Retirement", "purpose\nRetirement\n")
    _write_checkpoint(output, "Retirement")

    first = archive_final_summaries(
        "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
    )
    second = archive_final_summaries(
        "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
    )
    assert first == second


def test_archival_refuses_conflicting_existing_record(tmp_path: Path):
    output = tmp_path / "output"
    archive = tmp_path / "reviews"
    output.mkdir()
    _write_summary(output, "Retirement", "purpose\nRetirement\n")
    _write_checkpoint(output, "Retirement")
    archive_dir = archive / "2026-09-06"
    archive_dir.mkdir(parents=True)
    (archive_dir / "Retirement_summary.csv").write_text("purpose\nDifferent\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        archive_final_summaries(
            "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
        )


def test_archival_requires_requested_summary_and_valid_contract(tmp_path: Path):
    output = tmp_path / "output"
    archive = tmp_path / "reviews"
    output.mkdir()
    _write_summary(output, "Retirement")

    with pytest.raises(FileNotFoundError):
        archive_final_summaries(
            "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
        )

    _write_checkpoint(output, "Retirement")
    checkpoint = output / "final_Retirement_checkpoint.json"
    checkpoint.write_text(
        checkpoint.read_text(encoding="utf-8").replace('"contract_version": "1"', '"contract_version": "2"'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        archive_final_summaries(
            "2026-09-06", ["Retirement"], output_dir=output, archive_root=archive, final_contract_version="1"
        )
