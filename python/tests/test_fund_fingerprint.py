import json

import pytest

from fund_analysis.fingerprint_evidence import FingerprintEvidenceStore


def _fingerprint(*, elevation=None, protection=None):
    return {
        "fund": {
            "name": "Test Fund",
            "isin": "INFTEST123",
            "category": "Flexi Cap",
        },
        "elevation": elevation or {},
        "protection": protection or {},
    }


def test_fingerprint_evidence_store_creates_artifact(tmp_path):
    path = tmp_path / "INFTEST123.json"

    store = FingerprintEvidenceStore(path)
    store.create(
        fingerprint=_fingerprint(
            elevation={"rolling_3y": {"median": 12.0}},
            protection={"median_severity_pct": 10.0},
        ),
        nav_artifact_version=1,
        generated_at="2026-08-17T16:00:00+05:30",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["artifact_version"] == 1
    assert payload["nav_artifact_version"] == 1
    assert payload["fund"]["isin"] == "INFTEST123"
    assert "elevation" in payload
    assert "protection" in payload
    assert "resilience" not in payload


def test_fingerprint_evidence_store_preserves_nav_artifact_version(tmp_path):
    path = tmp_path / "INFTEST123.json"

    store = FingerprintEvidenceStore(path)
    store.create(
        fingerprint=_fingerprint(),
        nav_artifact_version=7,
        generated_at="2026-08-17T16:00:00+05:30",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["nav_artifact_version"] == 7


def test_fingerprint_evidence_store_rejects_overwrite(tmp_path):
    path = tmp_path / "INFTEST123.json"
    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=_fingerprint(),
        nav_artifact_version=1,
        generated_at="2026-08-17T16:00:00+05:30",
    )

    with pytest.raises(ValueError, match="already exists"):
        store.create(
            fingerprint=_fingerprint(),
            nav_artifact_version=2,
            generated_at="2026-08-18T16:00:00+05:30",
        )


def test_fund_fingerprint_evidence_contains_only_active_dimensions():
    fingerprint = _fingerprint(
        elevation={"rolling_3y": {"median": 12.0}},
        protection={"maximum_severity_pct": 25.0},
    )

    assert set(fingerprint) == {"fund", "elevation", "protection"}
    assert "resilience" not in fingerprint


def test_fingerprint_evidence_store_appends_new_nav_artifact_version(tmp_path):
    path = tmp_path / "INFTEST123.json"
    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=_fingerprint(),
        nav_artifact_version=1,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    store.append(
        fingerprint=_fingerprint(elevation={"rolling_3y": {"median": 13.0}}),
        nav_artifact_version=2,
        generated_at="2026-08-20T00:00:00+05:30",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["artifact_version"] == 2
    assert payload["nav_artifact_version"] == 2
    assert payload["generated_at"] == "2026-08-20T00:00:00+05:30"
    assert payload["elevation"]["rolling_3y"]["median"] == 13.0
    assert "resilience" not in payload


def test_fingerprint_evidence_store_rejects_append_at_same_nav_artifact_version(tmp_path):
    path = tmp_path / "INFTEST123.json"
    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=_fingerprint(),
        nav_artifact_version=2,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    with pytest.raises(ValueError, match="greater than the existing version"):
        store.append(
            fingerprint=_fingerprint(),
            nav_artifact_version=2,
            generated_at="2026-08-20T00:00:00+05:30",
        )


def test_fingerprint_evidence_store_rejects_append_to_older_nav_artifact_version(tmp_path):
    path = tmp_path / "INFTEST123.json"
    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=_fingerprint(),
        nav_artifact_version=2,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    with pytest.raises(ValueError, match="greater than the existing version"):
        store.append(
            fingerprint=_fingerprint(),
            nav_artifact_version=1,
            generated_at="2026-08-20T00:00:00+05:30",
        )
