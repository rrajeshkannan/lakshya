"""Durable persistence for COMPOSITION-stage behavioural evidence.

A CompositionFingerprint is expensive analytical evidence.  Once computed,
it must become a durable reusable artifact rather than remaining only in RAM.
This module owns the persistence boundary; it performs no analytical work.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from lakshya_core.models import ElevationEvidence, ProtectionEvidence
from lakshya_core.rolling_returns import RollingReturnEvidence

from .composition import Composition, composition_identity
from .composition_fingerprint import CompositionFingerprint

FINGERPRINT_SCHEMA_VERSION = 1


def fingerprint_path(root: Path, composition: Composition) -> Path:
    """Return the stable on-disk path for one Composition fingerprint."""
    return root / f"{composition_identity(composition)}.json"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def _rolling_to_dict(value: RollingReturnEvidence | None) -> dict | None:
    return None if value is None else asdict(value)


def _nav_to_records(nav: pd.DataFrame) -> list[dict[str, Any]]:
    frame = nav.copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def fingerprint_to_payload(fingerprint: CompositionFingerprint) -> dict[str, Any]:
    """Convert the complete Composition evidence to a JSON-safe payload."""
    composition = fingerprint.composition
    return {
        "schema_version": FINGERPRINT_SCHEMA_VERSION,
        "kind": "composition_fingerprint",
        "composition": composition_identity(composition),
        "members": [member.isin for member in composition.team.members],
        "weights": {
            isin: float(composition.weights[isin])
            for isin in sorted(composition.weights)
        },
        "nav": _nav_to_records(fingerprint.nav),
        "elevation": {
            "rolling_3y": _rolling_to_dict(fingerprint.elevation.rolling_3y),
            "rolling_5y": _rolling_to_dict(fingerprint.elevation.rolling_5y),
            "rolling_7y": _rolling_to_dict(fingerprint.elevation.rolling_7y),
            "rolling_10y": _rolling_to_dict(fingerprint.elevation.rolling_10y),
        },
        "protection": asdict(fingerprint.protection),
    }


def persist_fingerprint(
    fingerprint: CompositionFingerprint,
    root: Path,
) -> Path:
    """Atomically persist one complete Composition fingerprint."""
    root.mkdir(parents=True, exist_ok=True)
    destination = fingerprint_path(root, fingerprint.composition)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    payload = fingerprint_to_payload(fingerprint)
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(destination)
    return destination


def _rolling_from_dict(value: dict | None) -> RollingReturnEvidence | None:
    return None if value is None else RollingReturnEvidence(**value)


def load_fingerprint(
    path: Path,
    composition: Composition,
) -> CompositionFingerprint:
    """Load a persisted fingerprint without recalculating any metrics."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("schema_version") != FINGERPRINT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported Composition fingerprint schema in {path}: "
            f"{payload.get('schema_version')}"
        )

    expected_identity = composition_identity(composition)
    if payload.get("composition") != expected_identity:
        raise ValueError(f"Composition identity mismatch in {path}")

    nav = pd.DataFrame(payload["nav"])
    if "date" in nav.columns:
        nav["date"] = pd.to_datetime(nav["date"])

    elevation_payload = payload["elevation"]
    elevation = ElevationEvidence(
        rolling_3y=_rolling_from_dict(elevation_payload["rolling_3y"]),
        rolling_5y=_rolling_from_dict(elevation_payload["rolling_5y"]),
        rolling_7y=_rolling_from_dict(elevation_payload["rolling_7y"]),
        rolling_10y=_rolling_from_dict(elevation_payload["rolling_10y"]),
    )
    protection = ProtectionEvidence(**payload["protection"])
    return CompositionFingerprint.from_persisted(
        composition=composition,
        nav=nav,
        elevation=elevation,
        protection=protection,
    )


def has_fingerprint(root: Path, composition: Composition) -> bool:
    """Return whether a fingerprint checkpoint exists for a Composition."""
    return fingerprint_path(root, composition).is_file()
