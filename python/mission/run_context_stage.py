"""Run-context initialization for the resilient pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import platform
import uuid


@dataclass(frozen=True)
class RunContext:
    run_id: str
    as_of: str
    mode: str
    workers: int | str
    purpose_selection: list[str] | str
    python: str
    pipeline: str
    stages: dict


@dataclass(frozen=True)
class RunContextDeps:
    wall_timestamp: Callable[[], str]
    output_dir: object
    write_manifest: Callable[[], None]
    log: Callable[[str], None]
    detail: Callable[[str], None]
    log_path: object
    manifest_path: object
    set_manifest: Callable[[dict], None]


class RunContextStage:
    """Initialize the run manifest and emit the run-start lifecycle events."""

    def __init__(self, deps: RunContextDeps):
        self._deps = deps

    def initialize(
        self,
        *,
        valuation_date,
        resume_from: str | None,
        workers: int | None,
        purpose_names: list[str] | None,
    ) -> RunContext:
        self._deps.output_dir.mkdir(parents=True, exist_ok=True)
        run_id = uuid.uuid4().hex[:12]
        mode = resume_from or "full"
        worker_value = workers or "auto"
        purpose_selection = purpose_names or "all"
        as_of = str(valuation_date.date())
        manifest = {
            "run_id": run_id,
            "started_at": self._deps.wall_timestamp(),
            "as_of": as_of,
            "mode": mode,
            "workers": worker_value,
            "purpose_selection": purpose_selection,
            "python": platform.python_version(),
            "pipeline": "resilient_pipeline",
            "stages": {},
        }
        self._deps.set_manifest(manifest)
        self._deps.write_manifest()
        self._deps.log(
            f"START as-of {valuation_date.date()} mode={mode} workers={worker_value}"
        )
        self._deps.detail(
            f"RUN_START run_id={run_id} as_of={valuation_date.date()} mode={mode} "
            f"workers={worker_value} log={self._deps.log_path} manifest={self._deps.manifest_path}"
        )
        return RunContext(
            run_id=run_id,
            as_of=as_of,
            mode=mode,
            workers=worker_value,
            purpose_selection=purpose_selection,
            python=manifest["python"],
            pipeline=manifest["pipeline"],
            stages=manifest["stages"],
        )
