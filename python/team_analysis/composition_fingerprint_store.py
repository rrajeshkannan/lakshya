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
EVIDENCE_SCHEMA_VERSION = 1


def fingerprint_path(root: Path, composition: Composition) -> Path:
    """Return the stable on-disk path for one Composition fingerprint."""
    return root / f"{composition_identity(composition)}.json"


def evidence_path(root: Path, composition: Composition) -> Path:
    """Return the compact MISSION evidence path for one Composition."""
    return root / f"{composition_identity(composition)}.evidence.json"


def _rolling_to_dict(value: RollingReturnEvidence | None) -> dict | None:
    return None if value is None else asdict(value)


def _nav_to_records(nav: pd.DataFrame) -> list[dict[str, Any]]:
    frame = nav.copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def _evidence_to_payload(
    composition: Composition,
    elevation: ElevationEvidence,
    protection: ProtectionEvidence,
) -> dict[str, Any]:
    protection_payload = asdict(protection)
    protection_payload["days_at_or_above_threshold"] = {
        str(key): value for key, value in protection.days_at_or_above_threshold.items()
    }
    protection_payload["pct_days_at_or_above_threshold"] = {
        str(key): value for key, value in protection.pct_days_at_or_above_threshold.items()
    }
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "kind": "composition_evidence",
        "composition": composition_identity(composition),
        "elevation": {
            "rolling_3y": _rolling_to_dict(elevation.rolling_3y),
            "rolling_5y": _rolling_to_dict(elevation.rolling_5y),
            "rolling_7y": _rolling_to_dict(elevation.rolling_7y),
            "rolling_10y": _rolling_to_dict(elevation.rolling_10y),
        },
        "protection": protection_payload,
    }


def fingerprint_to_payload(fingerprint: CompositionFingerprint) -> dict[str, Any]:
    """Convert the complete Composition evidence to a JSON-safe payload."""
    composition = fingerprint.composition
    protection = asdict(fingerprint.protection)
    protection["days_at_or_above_threshold"] = {
        str(key): value for key, value in fingerprint.protection.days_at_or_above_threshold.items()
    }
    protection["pct_days_at_or_above_threshold"] = {
        str(key): value for key, value in fingerprint.protection.pct_days_at_or_above_threshold.items()
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


def _write_json_atomic(destination: Path, payload: dict[str, Any]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(destination)
    return destination


def persist_fingerprint_evidence(fingerprint: CompositionFingerprint, root: Path) -> Path:
    """Persist the compact evidence surface consumed by downstream MISSION."""
    destination = evidence_path(root, fingerprint.composition)
    return _write_json_atomic(
        destination,
        _evidence_to_payload(
            fingerprint.composition,
            fingerprint.elevation,
            fingerprint.protection,
        ),
    )


def persist_fingerprint(fingerprint: CompositionFingerprint, root: Path) -> Path:
    """Atomically persist one complete Composition fingerprint and its MISSION evidence."""
    destination = _write_json_atomic(
        fingerprint_path(root, fingerprint.composition),
        fingerprint_to_payload(fingerprint),
    )
    persist_fingerprint_evidence(fingerprint, root)
    return destination


def _rolling_from_dict(value: dict | None) -> RollingReturnEvidence | None:
    return None if value is None else RollingReturnEvidence(**value)


def _elevation_from_payload(payload: dict[str, Any]) -> ElevationEvidence:
    return ElevationEvidence(
        rolling_3y=_rolling_from_dict(payload["rolling_3y"]),
        rolling_5y=_rolling_from_dict(payload["rolling_5y"]),
        rolling_7y=_rolling_from_dict(payload["rolling_7y"]),
        rolling_10y=_rolling_from_dict(payload["rolling_10y"]),
    )


def _protection_from_payload(payload: dict[str, Any]) -> ProtectionEvidence:
    protection_payload = dict(payload)
    protection_payload["days_at_or_above_threshold"] = {
        int(key): value for key, value in protection_payload["days_at_or_above_threshold"].items()
    }
    protection_payload["pct_days_at_or_above_threshold"] = {
        int(key): value for key, value in protection_payload["pct_days_at_or_above_threshold"].items()
    }
    return ProtectionEvidence(**protection_payload)


def _validate_envelope(
    payload: dict[str, Any],
    *,
    path: Path,
    kind: str,
    schema_version: int,
    composition: Composition,
) -> None:
    if payload.get("schema_version") != schema_version:
        raise ValueError(
            f"Unsupported Composition evidence schema in {path}: {payload.get('schema_version')}"
        )
    if payload.get("kind") != kind:
        raise ValueError(f"Invalid Composition evidence kind in {path}: {payload.get('kind')!r}")
    if payload.get("composition") != composition_identity(composition):
        raise ValueError(f"Composition identity mismatch in {path}")


def load_fingerprint_evidence(
    path: Path,
    composition: Composition,
) -> tuple[ElevationEvidence, ProtectionEvidence]:
    """Load only the persisted Elevation and Protection evidence needed by MISSION.

    Existing complete fingerprints are accepted as a one-time migration source
    when the compact sidecar is absent. The sidecar is then persisted so later
    MISSION runs never deserialize the large Composition NAV trajectory.
    """
    sidecar = path.with_name(path.stem + ".evidence.json")
    try:
        with sidecar.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        with path.open("r", encoding="utf-8") as handle:
            full_payload = json.load(handle)
        _validate_envelope(
            full_payload,
            path=path,
            kind="composition_fingerprint",
            schema_version=FINGERPRINT_SCHEMA_VERSION,
            composition=composition,
        )
        elevation = _elevation_from_payload(full_payload["elevation"])
        protection = _protection_from_payload(full_payload["protection"])
        _write_json_atomic(
            sidecar,
            _evidence_to_payload(composition, elevation, protection),
        )
        return elevation, protection

    _validate_envelope(
        payload,
        path=sidecar,
        kind="composition_evidence",
        schema_version=EVIDENCE_SCHEMA_VERSION,
        composition=composition,
    )
    return (
        _elevation_from_payload(payload["elevation"]),
        _protection_from_payload(payload["protection"]),
    )


def load_fingerprint(path: Path, composition: Composition) -> CompositionFingerprint:
    """Load a persisted complete fingerprint without recalculating any metrics."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    _validate_envelope(
        payload,
        path=path,
        kind="composition_fingerprint",
        schema_version=FINGERPRINT_SCHEMA_VERSION,
        composition=composition,
    )

    nav = pd.DataFrame(payload["nav"])
    if "date" in nav.columns:
        nav["date"] = pd.to_datetime(nav["date"])

    elevation = _elevation_from_payload(payload["elevation"])
    protection = _protection_from_payload(payload["protection"])
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
