from __future__ import annotations

import json

from mission.trajectory_checkpoint import (
    is_valid_completion_marker,
    marker_path,
    write_completion_marker,
)


def test_completion_marker_round_trip(tmp_path):
    mission = tmp_path / "mission_survivors_Edu_B.csv"
    trajectory = tmp_path / "trajectory.csv"
    mission.write_text("composition\nA|x=1\n", encoding="utf-8")
    trajectory.write_text("composition,date\nA|x=1,2026-01-01\n", encoding="utf-8")

    marker = write_completion_marker(mission, trajectory, "Edu_B", "2026-08-31", 1)

    assert marker == marker_path(trajectory)
    assert marker.exists()
    assert is_valid_completion_marker(mission, trajectory, "Edu_B", "2026-08-31")
    assert not marker.with_suffix(marker.suffix + ".tmp").exists()


def test_completion_marker_invalidates_when_mission_changes(tmp_path):
    mission = tmp_path / "mission.csv"
    trajectory = tmp_path / "trajectory.csv"
    mission.write_text("composition\nA|x=1\n", encoding="utf-8")
    trajectory.write_text("x\n1\n", encoding="utf-8")
    write_completion_marker(mission, trajectory, "Edu_B", "2026-08-31", 1)

    mission.write_text("composition\nB|x=1\n", encoding="utf-8")

    assert not is_valid_completion_marker(mission, trajectory, "Edu_B", "2026-08-31")


def test_completion_marker_invalidates_when_trajectory_changes(tmp_path):
    mission = tmp_path / "mission.csv"
    trajectory = tmp_path / "trajectory.csv"
    mission.write_text("composition\nA|x=1\n", encoding="utf-8")
    trajectory.write_text("x\n1\n", encoding="utf-8")
    write_completion_marker(mission, trajectory, "Edu_B", "2026-08-31", 1)

    trajectory.write_text("x\n2\n", encoding="utf-8")

    assert not is_valid_completion_marker(mission, trajectory, "Edu_B", "2026-08-31")


def test_completion_marker_invalidates_for_wrong_purpose_or_as_of(tmp_path):
    mission = tmp_path / "mission.csv"
    trajectory = tmp_path / "trajectory.csv"
    mission.write_text("composition\nA|x=1\n", encoding="utf-8")
    trajectory.write_text("x\n1\n", encoding="utf-8")
    write_completion_marker(mission, trajectory, "Edu_B", "2026-08-31", 1)

    assert not is_valid_completion_marker(mission, trajectory, "Retirement", "2026-08-31")
    assert not is_valid_completion_marker(mission, trajectory, "Edu_B", "2025-08-31")


def test_completion_marker_missing_or_corrupt_is_invalid(tmp_path):
    mission = tmp_path / "mission.csv"
    trajectory = tmp_path / "trajectory.csv"
    mission.write_text("composition\nA|x=1\n", encoding="utf-8")
    trajectory.write_text("x\n1\n", encoding="utf-8")

    assert not is_valid_completion_marker(mission, trajectory, "Edu_B", "2026-08-31")
    marker = marker_path(trajectory)
    marker.write_text("{broken", encoding="utf-8")
    assert not is_valid_completion_marker(mission, trajectory, "Edu_B", "2026-08-31")


def test_completion_marker_payload_records_provenance(tmp_path):
    mission = tmp_path / "mission.csv"
    trajectory = tmp_path / "trajectory.csv"
    mission.write_text("composition\nA|x=1\n", encoding="utf-8")
    trajectory.write_text("x\n1\n", encoding="utf-8")
    marker = write_completion_marker(mission, trajectory, "Edu_B", "2026-08-31", 1)

    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["purpose"] == "Edu_B"
    assert payload["as_of"] == "2026-08-31"
    assert payload["row_count"] == 1
    assert payload["mission_filename"] == mission.name
    assert payload["trajectory_sha256"]
