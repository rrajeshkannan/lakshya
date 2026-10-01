from __future__ import annotations

import json
from pathlib import Path

from lfs.layout import final_checkpoint_path, final_summary_path, mission_survivors_path
from lfs.runner import _final_checkpoint_valid, _write_checkpoint
from lfs.final.compromise_programming import FINAL_CONTRACT_VERSION


def test_final_checkpoint_is_invalidated_when_mission_changes(tmp_path: Path, monkeypatch):
    mission_path = mission_survivors_path(tmp_path, "Test")
    mission_path.parent.mkdir(parents=True, exist_ok=True)
    mission_path.write_text("composition\nA|isin=1.0\n", encoding="utf-8")
    checkpoint = final_checkpoint_path(tmp_path, "Test")
    payload = {
        "contract_version": FINAL_CONTRACT_VERSION,
        "purpose": "Test",
        "mission_sha256": "placeholder",
        "bootstrap_resamples": 10,
        "bootstrap_seed": 7,
    }

    monkeypatch.setattr("lfs.runner.OUTPUT_DIR", tmp_path)

    # Compute the real mission hash by using the runner's helper contract.
    from core.hashing import sha256_file

    payload["mission_sha256"] = sha256_file(mission_path)
    _write_checkpoint(checkpoint, payload)
    summary = final_summary_path(tmp_path, "Test")
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text("purpose\nTest\n", encoding="utf-8")

    assert _final_checkpoint_valid(
        "Test", mission_path, bootstrap_resamples=10, bootstrap_seed=7
    )

    mission_path.write_text("composition\nB|isin=1.0\n", encoding="utf-8")
    assert not _final_checkpoint_valid(
        "Test", mission_path, bootstrap_resamples=10, bootstrap_seed=7
    )
