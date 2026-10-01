"""Durable index helpers for persisted Composition fingerprint checkpoints.

This module owns only the narrow checkpoint-index representation. It does not
validate fingerprint contents and does not decide which Composition work must
be computed; those remain responsibilities of the resilient pipeline.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from team_analysis.composition_fingerprint_store import FINGERPRINT_SCHEMA_VERSION

CHECKPOINT_INDEX_SCHEMA_VERSION = 1


def checkpoint_metadata(path: Path) -> dict[str, int] | None:
    """Return filesystem metadata used by the narrow index fast path."""
    try:
        stat = path.stat()
    except OSError:
        return None
    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "inode": stat.st_ino,
    }


def load_checkpoint_index(
    path: Path,
    candidates_sha256: str,
) -> dict[str, dict[str, int]]:
    """Load an index only when its structural inputs still match."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

    if (
        payload.get("schema_version") != CHECKPOINT_INDEX_SCHEMA_VERSION
        or payload.get("composition_candidates_sha256") != candidates_sha256
        or payload.get("fingerprint_schema_version") != FINGERPRINT_SCHEMA_VERSION
        or not isinstance(payload.get("entries"), dict)
    ):
        return {}
    return payload["entries"]


def publish_checkpoint_index(
    path: Path,
    candidates_sha256: str,
    entries: dict[str, dict[str, int]],
) -> None:
    """Atomically publish the current Composition checkpoint index."""
    payload = {
        "schema_version": CHECKPOINT_INDEX_SCHEMA_VERSION,
        "composition_candidates_sha256": candidates_sha256,
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "entries": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
