"""Parent-process orchestration for the MISSION stage.

The expensive per-Purpose worker remains in ``resilient_pipeline`` because it
depends on module-level runner state and must remain safely pickleable.

This module owns only:
    - loading persisted global-survivor identities,
    - selecting runnable Purposes,
    - submitting process-pool jobs,
    - consuming results,
    - preserving MISSION logging and manifest lifecycle.
"""

from __future__ import annotations

from concurrent.futures import as_completed as _as_completed
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class MissionExecutionDeps:
    load_global_identities: Callable[[], list[str]]
    runnable_purposes: Callable[..., list]
    checkpoint_valid: Callable[[object], bool]
    as_of_string: Callable[[], str]
    worker: Callable[..., tuple]
    executor_cls: type
    as_completed: Callable = _as_completed
    log: Callable[[str], None] = print
    detail: Callable[[str], None] = print
    manifest_update: Callable[..., None] = lambda *args, **kwargs: None


class MissionExecutionStage:
    """Run independent MISSION Purpose jobs in the parent process."""

    def __init__(self, deps: MissionExecutionDeps):
        self.deps = deps

    def run(
        self,
        purposes: Iterable,
        funds_by_isin,
        *,
        max_workers,
        skip_existing: bool,
    ) -> None:
        identities = self.deps.load_global_identities()
        runnable = self.deps.runnable_purposes(
            purposes,
            skip_existing=skip_existing,
            checkpoint_valid=self.deps.checkpoint_valid,
        )

        if not runnable:
            self.deps.log("No Purpose requires MISSION work")
            self.deps.detail("MISSION_SKIPPED reason=no_runnable_purposes")
            self.deps.manifest_update(
                "mission",
                "complete",
                purposes=0,
                global_survivors=len(identities),
            )
            return

        self.deps.log(
            f"[MISSION] running {len(runnable)} independent Purpose gates "
            f"from {len(identities)} persisted global survivors"
        )
        self.deps.detail(
            f"MISSION_STAGE_START purposes={len(runnable)} "
            f"identities={len(identities)} "
            f"workers={max_workers or 'auto'} "
            f"skip_existing={skip_existing}"
        )
        self.deps.manifest_update(
            "mission",
            "running",
            purposes=len(runnable),
            global_survivors=len(identities),
        )

        as_of = self.deps.as_of_string()
        with self.deps.executor_cls(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.deps.worker,
                    purpose,
                    identities,
                    funds_by_isin,
                    as_of,
                ): purpose.name
                for purpose in runnable
            }
            self.deps.detail(f"MISSION_WORKERS_READY submitted={len(futures)}")

            for future in self.deps.as_completed(futures):
                purpose_name = futures[future]
                try:
                    name, assessed, achievable, protected = future.result()
                    self.deps.log(
                        f"  {name}: assessed={assessed} "
                        f"achievability={achievable} protection={protected}"
                    )
                    self.deps.detail(
                        f"MISSION_WORKER_COMPLETE purpose={name} "
                        f"assessed={assessed} "
                        f"achievability={achievable} "
                        f"protection={protected}"
                    )
                except Exception as exc:
                    self.deps.detail(
                        f"MISSION_FAILED purpose={purpose_name} error={exc!r}"
                    )
                    self.deps.manifest_update(
                        "mission",
                        "failed",
                        failed_purpose=purpose_name,
                        error=repr(exc),
                    )
                    raise

        self.deps.detail("MISSION_STAGE_COMPLETE")
        self.deps.manifest_update(
            "mission",
            "complete",
            purposes=len(runnable),
            global_survivors=len(identities),
        )
