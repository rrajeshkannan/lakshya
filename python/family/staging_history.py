"""Immutable history snapshots for Purpose staging simulations."""
from __future__ import annotations

import json
import shutil
from pathlib import Path


def snapshot_current_staging(directory: Path, *, include_review: bool = True) -> Path:
    """Snapshot the current staging state into an immutable turn directory.

    The snapshot is a complete reviewer-visible state: staged Purpose inputs,
    achievability results, reconciliation ledger, staging state, and (when
    available) the human-facing review surface. Existing snapshots are never
    overwritten.
    """
    state_path = directory / "staging_state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"Staging state missing: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    turn = int(state["turn"])
    snapshot = directory / "simulations" / f"turn_{turn:03d}"
    if snapshot.exists():
        raise FileExistsError(f"Simulation snapshot already exists: {snapshot}")
    snapshot.mkdir(parents=True)

    required = [
        "purposes_staged.csv",
        "achievability_latest.csv",
        "reconciliation_ledger.csv",
        "staging_state.json",
    ]
    for name in required:
        source = directory / name
        if not source.is_file():
            raise FileNotFoundError(f"Required staging artifact missing: {source}")
        shutil.copy2(source, snapshot / name)

    review = directory / "purpose_review_latest.csv"
    if include_review and review.is_file():
        shutil.copy2(review, snapshot / "purpose_review.csv")

    return snapshot
