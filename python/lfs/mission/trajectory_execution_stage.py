"""Parent-process orchestration for TRAJECTORY observation jobs."""

from __future__ import annotations

from concurrent.futures import as_completed as _as_completed
from dataclasses import dataclass
from typing import Callable, Iterable

@dataclass(frozen=True)
class TrajectoryExecutionDeps:
    prepare_jobs: Callable[[Iterable], object]
    worker: Callable[..., tuple]
    as_of_string: Callable[[], str]
    executor_cls: type
    as_completed: Callable = _as_completed
    log: Callable[[str], None] = print
    detail: Callable[[str], None] = print
    manifest_update: Callable[..., None] = lambda *args, **kwargs: None

class TrajectoryExecutionStage:
    """Run persisted-MISSION trajectory jobs in the parent process."""
    def __init__(self, deps: TrajectoryExecutionDeps):
        self.deps = deps

    def run(self, purposes, funds_by_isin, *, max_workers) -> None:
        preparation = self.deps.prepare_jobs(purposes)
        jobs = preparation.jobs
        if not jobs:
            self.deps.log("No persisted MISSION outputs require trajectory observation")
            self.deps.detail("TRAJECTORY_STAGE_SKIPPED reason=no_jobs")
            self.deps.manifest_update("trajectory", "complete", purposes=0)
            return
        self.deps.detail(f"TRAJECTORY_STAGE_START purposes={len(jobs)} workers={max_workers or 'auto'}")
        self.deps.manifest_update("trajectory", "running", purposes=len(jobs))
        as_of = self.deps.as_of_string()
        with self.deps.executor_cls(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.deps.worker, purpose, identities, funds_by_isin, as_of): purpose.name
                for purpose, identities in jobs
            }
            self.deps.detail(f"TRAJECTORY_WORKERS_READY submitted={len(futures)}")
            for future in self.deps.as_completed(futures):
                purpose_name = futures[future]
                try:
                    count, rows = future.result()
                    self.deps.log(f"  {purpose_name}: trajectory complete survivors={count} rows={rows}")
                    self.deps.detail(f"TRAJECTORY_WORKER_COMPLETE purpose={purpose_name} survivors={count} rows={rows}")
                except Exception as exc:
                    self.deps.detail(f"TRAJECTORY_FAILED purpose={purpose_name} error={exc!r}")
                    self.deps.manifest_update("trajectory", "failed", failed_purpose=purpose_name, error=repr(exc))
                    raise
        self.deps.log("RESUME DONE")
        self.deps.detail("TRAJECTORY_STAGE_COMPLETE")
        self.deps.manifest_update("trajectory", "complete", purposes=len(jobs))
