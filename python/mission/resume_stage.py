"""Resume-mode orchestration for the resilient trajectory pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ResumeStageDeps:
    log: Callable[[str], None]
    detail: Callable[[str], None]
    run_mission_resume: Callable[[object, object, int | None], None]
    observe_trajectories: Callable[[object, object, int | None], None]
    complete: Callable[[], None]


class ResumeStage:
    def __init__(self, deps: ResumeStageDeps) -> None:
        self._deps = deps

    def dispatch(self, resume_from, purposes, funds_by_isin, workers) -> bool:
        if resume_from == "mission":
            self._deps.log("[RESUME MISSION] Loading persisted Purpose checkpoints")
            self._deps.detail("RESUME_MISSION_START")
            self._deps.observe_trajectories(purposes, funds_by_isin, workers)
            self._deps.log("RESUME MISSION DONE")
            self._deps.detail("RESUME_MISSION_COMPLETE")
            self._deps.complete()
            return True
        if resume_from == "global":
            self._deps.log("[RESUME GLOBAL] Loading persisted global Composition evidence")
            self._deps.detail("RESUME_GLOBAL_START")
            self._deps.run_mission_resume(purposes, funds_by_isin, workers)
            self._deps.observe_trajectories(purposes, funds_by_isin, workers)
            self._deps.log("RESUME GLOBAL DONE")
            self._deps.detail("RESUME_GLOBAL_COMPLETE")
            self._deps.complete()
            return True
        return False
