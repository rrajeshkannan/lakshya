from pathlib import Path

import pandas as pd
import pytest

from mission.durable_stage_output import (
    is_valid_csv_checkpoint,
    load_csv_checkpoint,
    write_csv_checkpoint,
)


def test_write_creates_valid_csv_checkpoint(tmp_path: Path):
    path = tmp_path / "global.csv"
    rows = [{"composition": "A|A=1.0"}]

    assert write_csv_checkpoint(
        path,
        rows,
        stage="global_frontier",
        as_of="2026-08-31",
        inputs={"candidate_count": "10"},
    ) == 1

    assert is_valid_csv_checkpoint(
        path,
        stage="global_frontier",
        as_of="2026-08-31",
        inputs={"candidate_count": "10"},
    )
    loaded = load_csv_checkpoint(
        path,
        stage="global_frontier",
        as_of="2026-08-31",
        inputs={"candidate_count": "10"},
    )
    pd.testing.assert_frame_equal(loaded, pd.DataFrame(rows))


def test_modified_output_is_not_reusable(tmp_path: Path):
    path = tmp_path / "mission.csv"
    write_csv_checkpoint(path, [{"composition": "A"}], stage="mission", as_of="2026-08-31")
    path.write_text(path.read_text() + "B\n", encoding="utf-8")

    assert not is_valid_csv_checkpoint(path, stage="mission", as_of="2026-08-31")
    with pytest.raises(ValueError):
        load_csv_checkpoint(path, stage="mission", as_of="2026-08-31")


def test_wrong_inputs_make_checkpoint_stale(tmp_path: Path):
    path = tmp_path / "trajectory.csv"
    write_csv_checkpoint(
        path,
        [{"composition": "A"}],
        stage="trajectory",
        as_of="2026-08-31",
        inputs={"mission_sha256": "abc"},
    )

    assert not is_valid_csv_checkpoint(
        path,
        stage="trajectory",
        as_of="2026-08-31",
        inputs={"mission_sha256": "def"},
    )


def test_missing_marker_is_not_reusable(tmp_path: Path):
    path = tmp_path / "mission.csv"
    write_csv_checkpoint(path, [{"composition": "A"}], stage="mission", as_of="2026-08-31")
    marker = path.with_suffix(path.suffix + ".complete.json")
    marker.unlink()

    assert not is_valid_csv_checkpoint(path, stage="mission", as_of="2026-08-31")


def test_wrong_stage_or_as_of_is_not_reusable(tmp_path: Path):
    path = tmp_path / "global.csv"
    write_csv_checkpoint(path, [{"composition": "A"}], stage="global_frontier", as_of="2026-08-31")

    assert not is_valid_csv_checkpoint(path, stage="mission", as_of="2026-08-31")
    assert not is_valid_csv_checkpoint(path, stage="global_frontier", as_of="2027-08-31")


def test_partial_write_never_publishes_completion_marker(tmp_path: Path):
    path = tmp_path / "output.csv"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("composition\npartial\n", encoding="utf-8")

    assert not path.exists()
    assert not is_valid_csv_checkpoint(path, stage="test", as_of="2026-08-31")
