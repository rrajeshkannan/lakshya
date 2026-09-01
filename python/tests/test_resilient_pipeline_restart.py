from pathlib import Path

import pandas as pd

import mission.resilient_pipeline as pipeline
from mission.durable_stage_output import write_csv_checkpoint


AS_OF = "2026-08-31"


def _configure(tmp_path: Path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", output)
    monkeypatch.setattr(pipeline, "LOG_PATH", output / "pipeline.log")
    monkeypatch.setattr(pipeline, "MANIFEST_PATH", output / "manifest.json")
    monkeypatch.setattr(pipeline, "FINGERPRINT_DIR", tmp_path / "fingerprints")
    pipeline._RUN_MANIFEST = {"as_of": AS_OF, "stages": {}}
    return output


def _write_global(output: Path):
    candidates = output / "composition_candidates.csv"
    candidates.write_text("composition,team\nA|A=1.0,A\n", encoding="utf-8")
    write_csv_checkpoint(
        output / "global_survivors.csv",
        [{"composition": "A|A=1.0"}],
        stage="global_frontier",
        as_of=AS_OF,
        inputs=pipeline._global_inputs(),
    )


def _write_mission(output: Path):
    write_csv_checkpoint(
        output / "achievability_Edu_B.csv",
        [{"composition": "A|A=1.0", "status": "WITHIN_OBSERVED_TERRAIN"}],
        stage="mission_achievability",
        as_of=AS_OF,
        inputs={
            "global_survivors_sha256": pipeline._sha256(output / "global_survivors.csv"),
            "global_checkpoint_stage": "global_frontier",
        },
    )
    write_csv_checkpoint(
        output / "mission_survivors_Edu_B.csv",
        [{"composition": "A|A=1.0"}],
        stage="mission",
        as_of=AS_OF,
        inputs={"achievability_sha256": pipeline._sha256(output / "achievability_Edu_B.csv")},
    )


def test_valid_mission_checkpoint_is_reusable(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)

    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, current_capital=0.0)
    assert pipeline._mission_checkpoint_valid(purpose)


def test_mission_checkpoint_becomes_stale_when_global_changes(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)

    (output / "global_survivors.csv").write_text(
        "composition\nMUTATED\n", encoding="utf-8"
    )
    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, current_capital=0.0)
    assert not pipeline._mission_checkpoint_valid(purpose)


def test_valid_trajectory_checkpoint_is_reusable(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)
    mission = output / "mission_survivors_Edu_B.csv"
    trajectory = output / "trajectory_observations" / "Edu_B.csv"
    write_csv_checkpoint(
        trajectory,
        [{"composition": "A|A=1.0", "date": "2026-08-31", "nav": 100.0}],
        stage="trajectory",
        as_of=AS_OF,
        inputs={"mission_sha256": pipeline._sha256(mission)},
    )

    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, current_capital=0.0)
    assert pipeline._trajectory_checkpoint_valid(purpose)


def test_trajectory_becomes_stale_when_mission_changes(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)
    mission = output / "mission_survivors_Edu_B.csv"
    trajectory = output / "trajectory_observations" / "Edu_B.csv"
    write_csv_checkpoint(
        trajectory,
        [{"composition": "A|A=1.0", "date": "2026-08-31", "nav": 100.0}],
        stage="trajectory",
        as_of=AS_OF,
        inputs={"mission_sha256": pipeline._sha256(mission)},
    )

    frame = pd.read_csv(mission)
    frame.loc[0, "composition"] = "B|B=1.0"
    frame.to_csv(mission, index=False)

    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, current_capital=0.0)
    assert not pipeline._trajectory_checkpoint_valid(purpose)


def test_trajectory_checkpoint_missing_marker_is_not_reusable(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)
    mission = output / "mission_survivors_Edu_B.csv"
    trajectory = output / "trajectory_observations" / "Edu_B.csv"
    write_csv_checkpoint(
        trajectory,
        [{"composition": "A|A=1.0", "date": "2026-08-31", "nav": 100.0}],
        stage="trajectory",
        as_of=AS_OF,
        inputs={"mission_sha256": pipeline._sha256(mission)},
    )
    trajectory.with_suffix(trajectory.suffix + ".complete.json").unlink()

    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, current_capital=0.0)
    assert not pipeline._trajectory_checkpoint_valid(purpose)
