"""Immutable history snapshots for Purpose staging simulations."""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from .staging import PURPOSE_FIELDS, TURN_FIELDS


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_turn_template(directory: Path) -> Path:
    """Create the full-family editable input for the next simulation turn."""
    state_path = directory / "staging_state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"Staging state missing: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("status") != "STAGING":
        raise ValueError("Staging workspace is already committed")
    staged_path = directory / "purposes_staged.csv"
    rows = _read_csv(staged_path)
    if not rows or set(rows[0]) != set(PURPOSE_FIELDS):
        raise ValueError(f"Staged Purpose file has an unexpected column layout: {staged_path}")
    template = directory / "simulation_input_latest.csv"
    template_rows = [
        {
            "purpose": row["name"],
            "value": row["value"],
            "monthly_plan": row["monthly_plan"],
            "desired": row["desired"],
            "due": row["due"],
            "capital_acquire_pct": "",
            "sip_acquire_pct": "",
        }
        for row in rows
    ]
    _write_csv(template, TURN_FIELDS, template_rows)
    return template


def snapshot_current_staging(
    directory: Path,
    *,
    turn_input: Path | None = None,
    include_review: bool = True,
) -> Path:
    """Snapshot the current staging state into an immutable turn directory.

    The snapshot is a complete reviewer-visible state: staged Purpose inputs,
    the exact simulation input when supplied, achievability results,
    reconciliation ledger, staging state, and the human-facing review surface.
    Existing snapshots are never overwritten.
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

    if turn_input is not None:
        if not turn_input.is_file():
            raise FileNotFoundError(f"Simulation input missing: {turn_input}")
        shutil.copy2(turn_input, snapshot / "simulation_input.csv")

    review = directory / "purpose_review_latest.csv"
    if include_review and review.is_file():
        shutil.copy2(review, snapshot / "purpose_review.csv")

    return snapshot
