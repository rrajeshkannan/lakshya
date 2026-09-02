"""Durable provenance checks for Purpose trajectory outputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = 1


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def marker_path(trajectory_path: Path) -> Path:
    return trajectory_path.with_suffix(trajectory_path.suffix + ".complete.json")


def write_completion_marker(
    trajectory_path: Path,
    *,
    purpose: str,
    as_of: str,
    mission_path: Path,
    row_count: int,
) -> Path:
    """Atomically record the exact evidence from which a trajectory was built."""
    marker = marker_path(trajectory_path)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "purpose": purpose,
        "as_of": as_of,
        "mission_file": mission_path.name,
        "mission_sha256": file_sha256(mission_path),
        "trajectory_sha256": file_sha256(trajectory_path),
        "row_count": row_count,
    }
    temporary = marker.with_suffix(marker.suffix + ".tmp")
    marker.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
    temporary.replace(marker)
    return marker


def is_valid_completion_marker(
    trajectory_path: Path,
    *,
    purpose: str,
    as_of: str,
    mission_path: Path,
) -> bool:
    """Return True only when output and its exact MISSION input still match."""
    marker = marker_path(trajectory_path)
    if not trajectory_path.is_file() or not marker.is_file() or not mission_path.is_file():
        return False
    try:
        with marker.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("schema_version") != SCHEMA_VERSION:
            return False
        if payload.get("purpose") != purpose or payload.get("as_of") != as_of:
            return False
        if payload.get("mission_file") != mission_path.name:
            return False
        if payload.get("mission_sha256") != file_sha256(mission_path):
            return False
        if payload.get("trajectory_sha256") != file_sha256(trajectory_path):
            return False
        return True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
