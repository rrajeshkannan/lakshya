from pathlib import Path

import mission.resilient_pipeline as pipeline


def test_write_rows_uses_explicit_worker_as_of_without_manifest(tmp_path: Path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(pipeline, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", output)
    pipeline._RUN_MANIFEST = None

    captured = {}

    def fake_write_csv_checkpoint(path, rows, *, stage, as_of, inputs):
        captured.update(path=path, rows=rows, stage=stage, as_of=as_of, inputs=inputs)
        return len(rows)

    monkeypatch.setattr(pipeline, "write_csv_checkpoint", fake_write_csv_checkpoint)

    count = pipeline._write_rows(
        output / "mission.csv",
        [{"composition": "A|A=1.0"}],
        stage="mission",
        inputs={"source": "global"},
        as_of="2026-08-31",
    )

    assert count == 1
    assert captured["stage"] == "mission"
    assert captured["as_of"] == "2026-08-31"
    assert captured["inputs"] == {"source": "global"}
