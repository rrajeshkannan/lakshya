from __future__ import annotations

import re

from mission import resilient_pipeline


def test_macro_console_and_forensic_log_are_distinct(tmp_path, monkeypatch, capsys):
    output_dir = tmp_path / "output"
    log_path = output_dir / "trajectory_pipeline.log"
    monkeypatch.setattr(resilient_pipeline, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(resilient_pipeline, "LOG_PATH", log_path)

    resilient_pipeline._log("MACRO_STAGE_COMPLETE")
    console = capsys.readouterr().out

    assert "MACRO_STAGE_COMPLETE" in console
    assert not log_path.exists()

    resilient_pipeline._detail("FINGERPRINT_PERSISTED composition=ABC")
    forensic = log_path.read_text(encoding="utf-8")

    assert "FINGERPRINT_PERSISTED composition=ABC" in forensic
    assert "MACRO_STAGE_COMPLETE" not in forensic
    assert re.match(r"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}[+-]\\d{2}:\\d{2} \\| ", forensic)


def test_detail_is_flush_visible_for_live_tail(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    log_path = output_dir / "trajectory_pipeline.log"
    monkeypatch.setattr(resilient_pipeline, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(resilient_pipeline, "LOG_PATH", log_path)

    resilient_pipeline._detail("WORK_UNIT_COMPLETE id=17")

    assert log_path.exists()
    assert log_path.read_text(encoding="utf-8").endswith("WORK_UNIT_COMPLETE id=17\n")
