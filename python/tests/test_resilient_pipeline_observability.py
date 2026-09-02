from pathlib import Path

import mission.resilient_pipeline as pipeline


def test_console_and_forensic_log_are_distinct_channels(tmp_path: Path, monkeypatch, capsys):
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", output)
    monkeypatch.setattr(pipeline, "LOG_PATH", output / "pipeline.log")

    pipeline._log("STAGE COMPLETE | survivors=42")
    pipeline._event("FORENSIC detail=checkpoint_hash_verified sha256=abc123")

    console = capsys.readouterr().out
    forensic = (output / "pipeline.log").read_text(encoding="utf-8")

    assert "STAGE COMPLETE | survivors=42" in console
    assert "FORENSIC detail=checkpoint_hash_verified sha256=abc123" not in console
    assert "FORENSIC detail=checkpoint_hash_verified sha256=abc123" in forensic
    assert "STAGE COMPLETE | survivors=42" not in forensic
    assert "T" in forensic.split(" | ", 1)[0]


def test_manifest_update_is_forensic_and_persisted(tmp_path: Path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", output)
    monkeypatch.setattr(pipeline, "LOG_PATH", output / "pipeline.log")
    monkeypatch.setattr(pipeline, "MANIFEST_PATH", output / "manifest.json")
    pipeline._RUN_MANIFEST = {"as_of": "2026-08-31", "stages": {}}

    pipeline._manifest_update("mission", "complete", survivors=42)

    assert pipeline._RUN_MANIFEST["stages"]["mission"]["status"] == "complete"
    assert pipeline._RUN_MANIFEST["stages"]["mission"]["survivors"] == 42
    assert (output / "manifest.json").is_file()

    forensic = (output / "pipeline.log").read_text(encoding="utf-8")
    assert "MANIFEST_UPDATE stage=mission status=complete survivors=42" in forensic
