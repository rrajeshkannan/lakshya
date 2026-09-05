from __future__ import annotations

import json
from pathlib import Path

from run_production import _final_checkpoint_valid, _write_checkpoint
from final.compromise_programming import FINAL_CONTRACT_VERSION


def test_final_checkpoint_is_invalidated_when_mission_changes(tmp_path: Path, monkeypatch):
    mission_path = tmp_path / "mission_survivors_Test.csv"
    mission_path.write_text("composition\nA|isin=1.0\n", encoding="utf-8")
    checkpoint = tmp_path / "final_Test_checkpoint.json"
    payload = {
        "contract_version": FINAL_CONTRACT_VERSION,
        "purpose": "Test",
        "mission_sha256": "placeholder",
        "bootstrap_resamples": 10,
        "bootstrap_seed": 7,
    }

    monkeypatch.setattr("run_production.OUTPUT_DIR", tmp_path)

    # Compute the real mission hash by using the runner's helper contract.
    from run_production import _sha256

    payload["mission_sha256"] = _sha256(mission_path)
    _write_checkpoint(checkpoint, payload)
    (tmp_path / "final_Test_summary.csv").write_text("purpose\nTest\n", encoding="utf-8")

    assert _final_checkpoint_valid(
        "Test", mission_path, bootstrap_resamples=10, bootstrap_seed=7
    )

    mission_path.write_text("composition\nB|isin=1.0\n", encoding="utf-8")
    assert not _final_checkpoint_valid(
        "Test", mission_path, bootstrap_resamples=10, bootstrap_seed=7
    )
