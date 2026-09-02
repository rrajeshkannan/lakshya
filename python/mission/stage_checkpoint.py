"""Durable completion markers for restartable pipeline stages."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

STAGE_CHECKPOINT_SCHEMA_VERSION = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def marker_path(output_path: Path) -> Path:
    """Return the sidecar completion marker for one durable output."""
    return output_path.with_suffix(output_path.suffix + ".complete.json")


def write_completion_marker(
    output_path: Path,
    *,
    stage: str,
    as_of: str,
    inputs: dict[str, str] | None = None,
    row_count: int | None = None,
) -> Path:
    """Atomically write a provenance-bearing completion marker.

    The marker is written only after the output itself has been atomically
    replaced. Its content binds completion to the exact output bytes and the
    stage inputs supplied by the caller.
    """
    if not output_path.is_file():
        raise FileNotFoundError(f"Cannot checkpoint missing stage output: {output_path}")
    payload = {
        "schema_version": STAGE_CHECKPOINT_SCHEMA_VERSION,
        "kind": "stage_completion",
        "stage": stage,
        "as_of": as_of,
        "output_file": output_path.name,
        "output_sha256": _sha256(output_path),
        "row_count": row_count,
        "inputs": dict(sorted((inputs or {}).items())),
    }
    destination = marker_path(output_path)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(destination)
    return destination


def is_valid_completion_marker(
    output_path: Path,
    *,
    stage: str,
    as_of: str,
    inputs: dict[str, str] | None = None,
) -> bool:
    """Return True only when output and its completion marker agree."""
    if not output_path.is_file():
        return False
    marker = marker_path(output_path)
    if not marker.is_file():
        return False
    try:
        with marker.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("schema_version") != STAGE_CHECKPOINT_SCHEMA_VERSION:
            return False
        if payload.get("kind") != "stage_completion":
            return False
        if payload.get("stage") != stage or payload.get("as_of") != as_of:
            return False
        if payload.get("output_file") != output_path.name:
            return False
        if payload.get("output_sha256") != _sha256(output_path):
            return False
        expected_inputs = dict(sorted((inputs or {}).items()))
        return payload.get("inputs", {}) == expected_inputs
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
