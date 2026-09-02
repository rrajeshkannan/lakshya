"""Durable persistence for COMPOSITION-stage behavioural evidence."""

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
    protection = asdict(fingerprint.protection)
    # JSON object keys are strings. Preserve integer threshold keys explicitly
    # so loading restores the domain object's exact key types.
    protection["days_at_or_above_threshold"] = {
        str(key): value
        for key, value in fingerprint.protection.days_at_or_above_threshold.items()
    }
    protection["pct_days_at_or_above_threshold"] = {
        str(key): value
        for key, value in fingerprint.protection.pct_days_at_or_above_threshold.items()
    }
    return {
        "schema_version": FINGERPRINT_SCHEMA_VERSION,
        "kind": "composition_fingerprint",
        "composition": composition_identity(composition),
        "members": [member.isin for member in composition.team.members],
        "weights": {isin: float(composition.weights[isin]) for isin in sorted(composition.weights)},
        "nav": _nav_to_records(fingerprint.nav),
        "elevation": {
            "rolling_3y": _rolling_to_dict(fingerprint.elevation.rolling_3y),
            "rolling_5y": _rolling_to_dict(fingerprint.elevation.rolling_5y),
            "rolling_7y": _rolling_to_dict(fingerprint.elevation.rolling_7y),
            "rolling_10y": _rolling_to_dict(fingerprint.elevation.rolling_10y),
        },
        "protection": protection,
    }


def persist_fingerprint(fingerprint: CompositionFingerprint, root: Path) -> Path:
    """Atomically persist one complete Composition fingerprint."""
    root.mkdir(parents=True, exist_ok=True)
    destination = fingerprint_path(root, fingerprint.composition)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(fingerprint_to_payload(fingerprint), handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(destination)
    return destination


def _rolling_from_dict(value: dict | None) -> RollingReturnEvidence | None:
    return None if value is None else RollingReturnEvidence(**value)


def load_fingerprint(path: Path, composition: Composition) -> CompositionFingerprint:
    """Load a persisted fingerprint without recalculating any metrics."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("schema_version") != FINGERPRINT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported Composition fingerprint schema in {path}: {payload.get('schema_version')}"
        )
    if payload.get("kind") != "composition_fingerprint":
        raise ValueError(f"Invalid Composition fingerprint kind in {path}: {payload.get('kind')!r}")

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
    protection_payload = dict(payload["protection"])
    protection_payload["days_at_or_above_threshold"] = {
        int(key): value for key, value in protection_payload["days_at_or_above_threshold"].items()
    }
    protection_payload["pct_days_at_or_above_threshold"] = {
        int(key): value for key, value in protection_payload["pct_days_at_or_above_threshold"].items()
    }
    protection = ProtectionEvidence(**protection_payload)
    return CompositionFingerprint.from_persisted(
        composition=composition, nav=nav, elevation=elevation, protection=protection
    )


def has_fingerprint(root: Path, composition: Composition) -> bool:
    """Return whether a valid fingerprint checkpoint exists for a Composition.

    Existence alone is not a safe checkpoint criterion: a crash can leave a
    truncated/corrupt JSON artifact behind. Validate the small checkpoint
    envelope and stable identity here so the resilient runner treats such an
    artifact as missing and recomputes only that work unit.
    """
    path = fingerprint_path(root, composition)
    if not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return False
    return (
        payload.get("schema_version") == FINGERPRINT_SCHEMA_VERSION
        and payload.get("kind") == "composition_fingerprint"
        and payload.get("composition") == composition_identity(composition)
    )
