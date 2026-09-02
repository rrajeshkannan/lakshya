from pathlib import Path

import mission.resilient_pipeline as pipeline
from mission.durable_stage_output import write_csv_checkpoint


AS_OF = "2026-08-31"


class _FakeFuture:
    def __init__(self, value=None, error=None):
        self._value = value
        self._error = error

    def result(self):
        if self._error is not None:
            raise self._error
        return self._value


class _FakeExecutor:
    def __init__(self, futures):
        self.futures = futures
        self.submitted = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args):
        purpose = args[0]
        self.submitted.append(purpose.name)
        return self.futures[purpose.name]


def _configure(tmp_path: Path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", output)
    monkeypatch.setattr(pipeline, "LOG_PATH", output / "pipeline.log")
    monkeypatch.setattr(pipeline, "MANIFEST_PATH", output / "manifest.json")
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


def _purpose(name: str):
    return pipeline.Purpose(name=name, horizon_years=4, current_capital=0.0)


def _install_fake_executor(monkeypatch, executor):
    monkeypatch.setattr(
        pipeline,
        "ProcessPoolExecutor",
        lambda max_workers=None: executor,
    )
    monkeypatch.setattr(pipeline, "as_completed", lambda futures: futures)


def test_successful_sibling_checkpoint_survives_failed_purpose(
    tmp_path: Path, monkeypatch
):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)

    purposes = [_purpose("Edu_B"), _purpose("Retirement")]
    completed = output / "mission_survivors_Retirement.csv"
    completed.write_text("completed sibling\n", encoding="utf-8")

    futures = {
        "Edu_B": _FakeFuture(error=RuntimeError("simulated purpose failure")),
        "Retirement": _FakeFuture(value=("Retirement", 1, 1, 1)),
    }
    executor = _FakeExecutor(futures)
    _install_fake_executor(monkeypatch, executor)

    try:
        pipeline._run_mission_from_global(
            purposes,
            {},
            max_workers=2,
            skip_existing=False,
        )
    except RuntimeError as exc:
        assert "simulated purpose failure" in str(exc)
    else:
        raise AssertionError("expected the failed purpose to propagate its error")

    assert completed.read_text(encoding="utf-8") == "completed sibling\n"
    assert executor.submitted == ["Edu_B", "Retirement"]


def test_retry_can_skip_already_valid_purpose_and_run_only_failed_work(
    tmp_path: Path, monkeypatch
):
    output = _configure(tmp_path, monkeypatch)
    _write_global(output)

    completed = output / "mission_survivors_Retirement.csv"
    completed.write_text("completed sibling\n", encoding="utf-8")

    purposes = [_purpose("Edu_B"), _purpose("Retirement")]
    monkeypatch.setattr(
        pipeline,
        "_mission_checkpoint_valid",
        lambda purpose: purpose.name == "Retirement",
    )

    executor = _FakeExecutor({"Edu_B": _FakeFuture(value=("Edu_B", 1, 1, 1))})
    _install_fake_executor(monkeypatch, executor)

    pipeline._run_mission_from_global(
        purposes,
        {},
        max_workers=1,
        skip_existing=True,
    )

    assert executor.submitted == ["Edu_B"]
    assert completed.read_text(encoding="utf-8") == "completed sibling\n"
