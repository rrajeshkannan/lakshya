from pathlib import Path

from mission.stage_checkpoint import (
    is_valid_completion_marker,
    marker_path,
    write_completion_marker,
)


def _write(path: Path, text: str = "composition,score\nA,1\n") -> None:
    path.write_text(text, encoding="utf-8")


def test_completion_marker_binds_output_bytes_and_inputs(tmp_path):
    output = tmp_path / "global_survivors.csv"
    _write(output)

    marker = write_completion_marker(
        output,
        stage="global_frontier",
        as_of="2026-08-31",
        inputs={"composition_evidence": "complete"},
        row_count=1,
    )

    assert marker == marker_path(output)
    assert is_valid_completion_marker(
        output,
        stage="global_frontier",
        as_of="2026-08-31",
        inputs={"composition_evidence": "complete"},
    )


def test_marker_rejects_changed_output(tmp_path):
    output = tmp_path / "mission_survivors_Edu_B.csv"
    _write(output)
    write_completion_marker(output, stage="mission", as_of="2026-08-31", row_count=1)

    output.write_text("composition,score\nA,2\n", encoding="utf-8")

    assert not is_valid_completion_marker(output, stage="mission", as_of="2026-08-31")


def test_marker_rejects_wrong_stage_or_as_of(tmp_path):
    output = tmp_path / "global_survivors.csv"
    _write(output)
    write_completion_marker(output, stage="global_frontier", as_of="2026-08-31")

    assert not is_valid_completion_marker(output, stage="mission", as_of="2026-08-31")
    assert not is_valid_completion_marker(output, stage="global_frontier", as_of="2026-09-01")


def test_marker_rejects_wrong_inputs(tmp_path):
    output = tmp_path / "team_survivors.csv"
    _write(output)
    write_completion_marker(
        output,
        stage="team",
        as_of="2026-08-31",
        inputs={"fund_scope": "17"},
    )

    assert not is_valid_completion_marker(
        output,
        stage="team",
        as_of="2026-08-31",
        inputs={"fund_scope": "16"},
    )


def test_corrupt_marker_is_invalid(tmp_path):
    output = tmp_path / "global_survivors.csv"
    _write(output)
    marker = write_completion_marker(output, stage="global_frontier", as_of="2026-08-31")
    marker.write_text("{not-json", encoding="utf-8")

    assert not is_valid_completion_marker(output, stage="global_frontier", as_of="2026-08-31")


def test_missing_marker_is_invalid(tmp_path):
    output = tmp_path / "trajectory.csv"
    _write(output)

    assert not is_valid_completion_marker(output, stage="trajectory", as_of="2026-08-31")
