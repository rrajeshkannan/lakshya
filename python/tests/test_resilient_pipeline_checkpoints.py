from pathlib import Path

import pandas as pd
import pytest

import mission.resilient_pipeline as pipeline
from mission.durable_stage_output import write_csv_checkpoint


AS_OF = "2026-08-31"


def _configure(tmp_path: Path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", output)
    monkeypatch.setattr(pipeline, "LOG_PATH", output / "pipeline.log")
    monkeypatch.setattr(pipeline, "MANIFEST_PATH", output / "manifest.json")
    pipeline._RUN_MANIFEST = {"as_of": AS_OF, "stages": {}}
    return output


def _write_global_inputs(output: Path):
    (output / "composition_candidates.csv").write_text(
        "composition,team\nA|A=1.0,A\n", encoding="utf-8"
    )


def _write_global_checkpoint(output: Path):
    write_csv_checkpoint(
        output / "global_survivors.csv",
        [{"composition": "A|A=1.0"}],
        stage="global_frontier",
        as_of=AS_OF,
        inputs=pipeline._global_inputs(),
    )


def test_global_checkpoint_is_loaded_only_when_provenance_matches(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global_inputs(output)
    _write_global_checkpoint(output)

    assert pipeline._load_global_identities() == ["A|A=1.0"]


def test_global_checkpoint_is_rejected_when_upstream_input_changes(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global_inputs(output)
    _write_global_checkpoint(output)

    (output / "composition_candidates.csv").write_text(
        "composition,team\nA|A=1.0,A\nB|B=1.0,B\n", encoding="utf-8"
    )

    with pytest.raises((ValueError, FileNotFoundError)):
        pipeline._load_global_identities()


def test_global_checkpoint_is_rejected_when_marker_is_missing(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global_inputs(output)
    _write_global_checkpoint(output)
    (output / "global_survivors.csv.complete.json").unlink()

    with pytest.raises((ValueError, FileNotFoundError)):
        pipeline._load_global_identities()


def test_global_checkpoint_is_rejected_for_different_as_of(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global_inputs(output)
    write_csv_checkpoint(
        output / "global_survivors.csv",
        [{"composition": "A|A=1.0"}],
        stage="global_frontier",
        as_of="2027-08-31",
        inputs=pipeline._global_inputs(),
    )

    with pytest.raises((ValueError, FileNotFoundError)):
        pipeline._load_global_identities()


def test_global_checkpoint_output_mutation_is_detected(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    _write_global_inputs(output)
    _write_global_checkpoint(output)

    frame = pd.read_csv(output / "global_survivors.csv")
    frame.loc[0, "composition"] = "MUTATED"
    frame.to_csv(output / "global_survivors.csv", index=False)

    with pytest.raises((ValueError, FileNotFoundError)):
        pipeline._load_global_identities()


def _write_mission_checkpoint(output: Path):
    mission_path = output / "mission_survivors_Edu_B.csv"
    write_csv_checkpoint(
        mission_path,
        [{"composition": "A|A=1.0"}],
        stage="mission",
        as_of=AS_OF,
        inputs={"achievability_sha256": "achievability-placeholder"},
    )
    return mission_path


def test_trajectory_checkpoint_requires_current_contract_version(tmp_path: Path, monkeypatch):
    output = _configure(tmp_path, monkeypatch)
    mission_path = _write_mission_checkpoint(output)
    trajectory_path = output / "trajectory_observations" / "Edu_B.csv"
    coverage_path = output / "trajectory_observations" / "Edu_B_coverage.csv"
    old_inputs = {
        "mission_sha256": pipeline._sha256(mission_path),
        "trajectory_contract_version": str(pipeline.TRAJECTORY_CONTRACT_VERSION - 1),
    }

    write_csv_checkpoint(
        trajectory_path,
        [{"composition": "A|A=1.0", "horizon_years": 5}],
        stage="trajectory",
        as_of=AS_OF,
        inputs=old_inputs,
    )
    write_csv_checkpoint(
        coverage_path,
        [{"composition": "A|A=1.0", "trajectory_horizon_years": 5, "status": "observed"}],
        stage="trajectory_coverage",
        as_of=AS_OF,
        inputs=old_inputs,
    )

    assert not pipeline._trajectory_checkpoint_valid(
        pipeline.Purpose(name="Edu_B", horizon_years=4)
    )
