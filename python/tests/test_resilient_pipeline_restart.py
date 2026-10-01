from pathlib import Path

from lakshya_core.hashing import sha256_file
import pandas as pd

import lfs.mission.resilient_pipeline as pipeline
from lfs.layout import (
    achievability_path,
    composition_candidates_path,
    global_survivors_path,
    mission_survivors_path,
    trajectory_observations_dir,
)
from lfs.mission.durable_stage_output import write_csv_checkpoint


AS_OF = "2026-08-31"


def _configure(tmp_path: Path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", output)
    monkeypatch.setattr(pipeline, "LOG_PATH", output / "pipeline.log")
    monkeypatch.setattr(pipeline, "MANIFEST_PATH", output / "manifest.json")
    monkeypatch.setattr(pipeline, "FINGERPRINT_DIR", tmp_path / "fingerprints")
    purposes = tmp_path / "purposes.csv"
    purposes.write_text("name,due,desired,monthly_plan\nEdu_B,2031-01-01,5500000,40000\n", encoding="utf-8")
    monkeypatch.setattr(pipeline, "PURPOSES_PATH", purposes)
    snapshot = pipeline._positions_as_of_path(AS_OF)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(
        "investor,folio,isin,units,nav,market_value,purpose\n"
        "Amma,F1,ISIN1,10,100,1000,Edu_B\n",
        encoding="utf-8",
    )
    pipeline._RUN_MANIFEST = {"as_of": AS_OF, "stages": {}}
    return output


def _write_global(output: Path):
    candidates = composition_candidates_path(output)
    candidates.parent.mkdir(parents=True, exist_ok=True)
    candidates.write_text("composition,team\nA|A=1.0,A\n", encoding="utf-8")
    write_csv_checkpoint(
        global_survivors_path(output),
        [{"composition": "A|A=1.0"}],
        stage="global_frontier",
        as_of=AS_OF,
        inputs=pipeline._global_inputs(),
    )


def _write_mission(output: Path):
    purpose_inputs = pipeline._purpose_inputs_sha256(AS_OF)
    achievability = achievability_path(output, "Edu_B")
    write_csv_checkpoint(
        achievability,
        [{"composition": "A|A=1.0", "status": "WITHIN_OBSERVED_TERRAIN"}],
        stage="mission_achievability",
        as_of=AS_OF,
        inputs={
            "global_survivors_sha256": sha256_file(global_survivors_path(output)),
            "global_checkpoint_stage": "global_frontier",
            "purpose_inputs_sha256": purpose_inputs,
        },
    )
    write_csv_checkpoint(
        mission_survivors_path(output, "Edu_B"),
        [{"composition": "A|A=1.0"}],
        stage="mission",
        as_of=AS_OF,
        inputs={
            "achievability_sha256": sha256_file(achievability),
            "purpose_inputs_sha256": purpose_inputs,
        },
    )


def _write_trajectory_checkpoints(output: Path):
    mission = mission_survivors_path(output, "Edu_B")
    observations = trajectory_observations_dir(output)
    trajectory = observations / "Edu_B.csv"
    coverage = observations / "Edu_B_coverage.csv"
    inputs = {
        "mission_sha256": sha256_file(mission),
        "trajectory_contract_version": str(pipeline.TRAJECTORY_CONTRACT_VERSION),
    }
    write_csv_checkpoint(
        trajectory,
        [{"composition": "A|A=1.0", "date": "2026-08-31", "nav": 100.0}],
        stage="trajectory",
        as_of=AS_OF,
        inputs=inputs,
    )
    write_csv_checkpoint(
        coverage,
        [{
            "composition": "A|A=1.0",
            "purpose_horizon_years": 4,
            "nominal_trajectory_horizon_years": 3,
            "trajectory_horizon_years": 3,
            "status": "observed",
        }],
        stage="trajectory_coverage",
        as_of=AS_OF,
        inputs=inputs,
    )


def test_valid_mission_checkpoint_is_reusable(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)

    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, capital=0.0)
    assert pipeline._mission_checkpoint_valid(purpose)


def test_mission_checkpoint_becomes_stale_when_global_changes(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)

    global_survivors_path(output).write_text(
        "composition\nMUTATED\n", encoding="utf-8"
    )
    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, capital=0.0)
    assert not pipeline._mission_checkpoint_valid(purpose)


def test_valid_trajectory_checkpoint_is_reusable(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)
    _write_trajectory_checkpoints(output)

    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, capital=0.0)
    assert pipeline._trajectory_checkpoint_valid(purpose)


def test_trajectory_becomes_stale_when_mission_changes(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)
    _write_trajectory_checkpoints(output)
    mission = mission_survivors_path(output, "Edu_B")

    frame = pd.read_csv(mission)
    frame.loc[0, "composition"] = "B|B=1.0"
    frame.to_csv(mission, index=False)

    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, capital=0.0)
    assert not pipeline._trajectory_checkpoint_valid(purpose)


def test_trajectory_checkpoint_missing_marker_is_not_reusable(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)
    _write_mission(output)
    trajectory = trajectory_observations_dir(output) / "Edu_B.csv"
    _write_trajectory_checkpoints(output)
    trajectory.with_suffix(trajectory.suffix + ".complete.json").unlink()

    purpose = pipeline.Purpose(name="Edu_B", horizon_years=4, capital=0.0)
    assert not pipeline._trajectory_checkpoint_valid(purpose)
