from pathlib import Path

from mission.trajectory_checkpoint import (
    is_valid_completion_marker,
    marker_path,
    write_completion_marker,
)


def test_trajectory_completion_marker_round_trip(tmp_path):
    mission = tmp_path / "mission_survivors_Edu_B.csv"
    trajectory = tmp_path / "Edu_B.csv"
    mission.write_text("composition\nA|A=1.0\n", encoding="utf-8")
    trajectory.write_text("composition,date\nA|A=1.0,2026-08-31\n", encoding="utf-8")

    marker = write_completion_marker(
        trajectory,
        purpose="Edu_B",
        as_of="2026-08-31",
        mission_path=mission,
        row_count=1,
    )

    assert marker == marker_path(trajectory)
    assert marker.exists()
    assert is_valid_completion_marker(
        trajectory,
        purpose="Edu_B",
        as_of="2026-08-31",
        mission_path=mission,
    )


def test_trajectory_checkpoint_invalid_when_mission_changes(tmp_path):
    mission = tmp_path / "mission_survivors_Edu_B.csv"
    trajectory = tmp_path / "Edu_B.csv"
    mission.write_text("composition\nA|A=1.0\n", encoding="utf-8")
    trajectory.write_text("composition,date\nA|A=1.0,2026-08-31\n", encoding="utf-8")
    write_completion_marker(
        trajectory,
        purpose="Edu_B",
        as_of="2026-08-31",
        mission_path=mission,
        row_count=1,
    )

    mission.write_text("composition\nB|B=1.0\n", encoding="utf-8")

    assert not is_valid_completion_marker(
        trajectory,
        purpose="Edu_B",
        as_of="2026-08-31",
        mission_path=mission,
    )


def test_trajectory_checkpoint_invalid_when_output_changes(tmp_path):
    mission = tmp_path / "mission_survivors_Edu_B.csv"
    trajectory = tmp_path / "Edu_B.csv"
    mission.write_text("composition\nA|A=1.0\n", encoding="utf-8")
    trajectory.write_text("composition,date\nA|A=1.0,2026-08-31\n", encoding="utf-8")
    write_completion_marker(
        trajectory,
        purpose="Edu_B",
        as_of="2026-08-31",
        mission_path=mission,
        row_count=1,
    )

    trajectory.write_text("composition,date\nA|A=1.0,2026-09-01\n", encoding="utf-8")

    assert not is_valid_completion_marker(
        trajectory,
        purpose="Edu_B",
        as_of="2026-08-31",
        mission_path=mission,
    )


def test_trajectory_checkpoint_invalid_for_wrong_provenance(tmp_path):
    mission = tmp_path / "mission_survivors_Edu_B.csv"
    trajectory = tmp_path / "Edu_B.csv"
    mission.write_text("composition\nA|A=1.0\n", encoding="utf-8")
    trajectory.write_text("composition,date\nA|A=1.0,2026-08-31\n", encoding="utf-8")
    write_completion_marker(
        trajectory,
        purpose="Edu_B",
        as_of="2026-08-31",
        mission_path=mission,
        row_count=1,
    )

    assert not is_valid_completion_marker(
        trajectory,
        purpose="Retirement",
        as_of="2026-08-31",
        mission_path=mission,
    )
    assert not is_valid_completion_marker(
        trajectory,
        purpose="Edu_B",
        as_of="2026-09-01",
        mission_path=mission,
    )
