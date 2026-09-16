from pathlib import Path

from mission.durable_stage_output import write_csv_checkpoint
from mission.mission_stage import MissionCheckpointDeps, MissionStage


def _write_outputs(output: Path, purpose_inputs: str) -> None:
    global_path = output / "global_survivors.csv"
    global_path.write_text("composition\nA|isin=1.0\n", encoding="utf-8")
    achievability = output / "achievability_Edu_B.csv"
    mission = output / "mission_survivors_Edu_B.csv"
    write_csv_checkpoint(
        achievability,
        [{"composition": "A|isin=1.0", "status": "WITHIN_OBSERVED_TERRAIN"}],
        stage="mission_achievability",
        as_of="2026-09-10",
        inputs={
            "global_survivors_sha256": __import__("lakshya_core.hashing", fromlist=["sha256_file"]).sha256_file(global_path),
            "global_checkpoint_stage": "global_frontier",
            "purpose_inputs_sha256": purpose_inputs,
        },
    )
    from lakshya_core.hashing import sha256_file
    write_csv_checkpoint(
        mission,
        [{"composition": "A|isin=1.0"}],
        stage="mission",
        as_of="2026-09-10",
        inputs={
            "achievability_sha256": sha256_file(achievability),
            "purpose_inputs_sha256": purpose_inputs,
        },
    )


def test_mission_checkpoint_is_invalidated_when_purpose_inputs_change(tmp_path: Path):
    output = tmp_path / "output"
    output.mkdir()
    _write_outputs(output, "purpose-hash-v1")

    current = {"value": "purpose-hash-v1"}
    stage = MissionStage(
        MissionCheckpointDeps(
            output_dir=output,
            as_of_string=lambda: "2026-09-10",
            sha256=__import__("lakshya_core.hashing", fromlist=["sha256_file"]).sha256_file,
            purpose_inputs_sha256=lambda _as_of: current["value"],
            is_valid_csv_checkpoint=__import__("mission.durable_stage_output", fromlist=["is_valid_csv_checkpoint"]).is_valid_csv_checkpoint,
        )
    )

    purpose = type("Purpose", (), {"name": "Edu_B"})()
    assert stage.checkpoint_valid(purpose)

    current["value"] = "purpose-hash-v2"
    assert not stage.checkpoint_valid(purpose)
