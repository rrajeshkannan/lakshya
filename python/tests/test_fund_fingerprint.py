import json

import pytest

from fund_analysis.fingerprint_evidence import FingerprintEvidenceStore
from lakshya_core.models import ElevationEvidence, Fund, FundFingerprint, ProtectionEvidence, ResilienceEvidence


def test_fingerprint_evidence_store_creates_artifact(tmp_path):
    # A Fund fingerprint is persisted as evidence of what the Fund-stage
    # engine observed. It is not a score, rank, suitability judgement,
    # or recommendation.
    path = tmp_path / "INFTEST123.json"

    fingerprint = {
        "fund": {
            "name": "Test Fund",
            "isin": "INFTEST123",
            "category": "Flexi Cap",
        },
        "elevation": {
            "rolling_3y": {"median": 12.0},
            "rolling_5y": {"median": 13.0},
        },
        "protection": {
            "median_severity_pct": 10.0,
            "maximum_severity_pct": 25.0,
        },
        "resilience": {
            "episode_count": 4,
            "recovered_count": 3,
            "ongoing_count": 1,
        },
    }

    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=fingerprint,
        nav_artifact_version=1,
        generated_at="2026-08-17T16:00:00+05:30",
    )

    assert path.exists()

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert payload["artifact_version"] == 1
    assert payload["nav_artifact_version"] == 1
    assert payload["fund"]["isin"] == "INFTEST123"
    assert "elevation" in payload
    assert "protection" in payload
    assert "resilience" in payload


def test_fingerprint_evidence_store_preserves_nav_artifact_version(
    tmp_path,
):
    # A fingerprint must record which NAV evidence version produced it.
    # This creates an explicit lineage from source evidence to analysis.
    path = tmp_path / "INFTEST123.json"

    fingerprint = {
        "fund": {
            "name": "Test Fund",
            "isin": "INFTEST123",
            "category": "Flexi Cap",
        },
        "elevation": {},
        "protection": {},
        "resilience": {},
    }

    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=fingerprint,
        nav_artifact_version=7,
        generated_at="2026-08-17T16:00:00+05:30",
    )

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert payload["nav_artifact_version"] == 7


def test_fingerprint_evidence_store_rejects_overwrite(tmp_path):
    # A fingerprint artifact must not silently replace an existing
    # fingerprint derived from an earlier evidence state.
    path = tmp_path / "INFTEST123.json"

    fingerprint = {
        "fund": {
            "name": "Test Fund",
            "isin": "INFTEST123",
            "category": "Flexi Cap",
        },
        "elevation": {},
        "protection": {},
        "resilience": {},
    }

    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=fingerprint,
        nav_artifact_version=1,
        generated_at="2026-08-17T16:00:00+05:30",
    )

    with pytest.raises(ValueError, match="already exists"):
        store.create(
            fingerprint=fingerprint,
            nav_artifact_version=2,
            generated_at="2026-08-18T16:00:00+05:30",
        )


def test_fund_fingerprint_contains_three_compass_dimensions():
    # A fund's fingerprint contains three compass dimensions: elevation, protection, and resilience.
    elevation = ElevationEvidence(
        rolling_3y=None,
        rolling_5y=None,
        rolling_7y=None,
        rolling_10y=None,
    )

    protection = ProtectionEvidence(
        observations=100,
        median_severity_pct=5.0,
        percentile_75_severity_pct=10.0,
        percentile_90_severity_pct=15.0,
        percentile_95_severity_pct=20.0,
        percentile_99_severity_pct=30.0,
        maximum_severity_pct=40.0,
        days_at_or_above_threshold={
            5: 50,
            10: 25,
            15: 10,
            20: 5,
            25: 2,
            30: 1,
        },
        pct_days_at_or_above_threshold={
            5: 50.0,
            10: 25.0,
            15: 10.0,
            20: 5.0,
            25: 2.0,
            30: 1.0,
        },
    )

    resilience = ResilienceEvidence(
        episode_count=0,
        recovered_count=0,
        ongoing_count=0,
        median_depth_pct=None,
        worst_depth_pct=None,
        median_decline_days_recovered=None,
        median_recovery_days=None,
        median_underwater_days_recovered=None,
        median_underwater_days_ongoing=None,
        episodes=[],
    )

    fund = Fund(
        name="Example Fund",
        isin="EXAMPLE",
        category="Flexi Cap",
    )

    fingerprint = FundFingerprint(
        fund=fund,
        elevation=elevation,
        protection=protection,
        resilience=resilience,
    )

    assert fingerprint.fund == fund
    assert fingerprint.elevation is elevation
    assert fingerprint.protection is protection
    assert fingerprint.resilience is resilience


def test_fund_fingerprint_composes_three_evidence_dimensions():
    # The Fund Fingerprint is a composition of the three
    # independent Fund-stage compass dimensions.
    #
    # Composition does not calculate, score, rank, weight, or judge them.
    # It simply preserves the evidence produced by each dimension.
    #
    # The fund identity is retained alongside the three dimensions.

    fund = Fund(
        name="Test Fund",
        isin="TEST123",
        category="Flexi Cap",
    )

    elevation = ElevationEvidence(
        rolling_3y=None,
        rolling_5y=None,
        rolling_7y=None,
        rolling_10y=None,
    )

    protection = ProtectionEvidence(
        observations=0,
        median_severity_pct=0.0,
        percentile_75_severity_pct=0.0,
        percentile_90_severity_pct=0.0,
        percentile_95_severity_pct=0.0,
        percentile_99_severity_pct=0.0,
        maximum_severity_pct=0.0,
        days_at_or_above_threshold={},
        pct_days_at_or_above_threshold={},
    )

    resilience = ResilienceEvidence(
        episodes=[],
        episode_count=0,
        recovered_count=0,
        ongoing_count=0,
        median_depth_pct=None,
        worst_depth_pct=None,
        median_decline_days_recovered=None,
        median_recovery_days=None,
        median_underwater_days_recovered=None,
        median_underwater_days_ongoing=None,
    )

    fingerprint = FundFingerprint(
        fund=fund,
        elevation=elevation,
        protection=protection,
        resilience=resilience,
    )

    assert fingerprint.fund is fund
    assert fingerprint.elevation is elevation
    assert fingerprint.protection is protection
    assert fingerprint.resilience is resilience


def test_fingerprint_evidence_store_appends_new_nav_artifact_version(
    tmp_path,
):
    path = tmp_path / "INFTEST123.json"

    fingerprint_v1 = {
        "fund": {
            "name": "Test Fund",
            "isin": "INFTEST123",
            "category": "Flexi Cap",
        },
        "elevation": {},
        "protection": {},
        "resilience": {},
    }

    fingerprint_v2 = {
        "fund": {
            "name": "Test Fund",
            "isin": "INFTEST123",
            "category": "Flexi Cap",
        },
        "elevation": {
            "rolling_3y": {
                "median": 13.0,
            },
        },
        "protection": {},
        "resilience": {},
    }

    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=fingerprint_v1,
        nav_artifact_version=1,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    store.append(
        fingerprint=fingerprint_v2,
        nav_artifact_version=2,
        generated_at="2026-08-20T00:00:00+05:30",
    )

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert payload["artifact_version"] == 2
    assert payload["nav_artifact_version"] == 2
    assert payload["generated_at"] == (
        "2026-08-20T00:00:00+05:30"
    )

    assert payload["elevation"]["rolling_3y"]["median"] == 13.0


def test_fingerprint_evidence_store_rejects_append_at_same_nav_artifact_version(
    tmp_path,
):
    path = tmp_path / "INFTEST123.json"

    fingerprint = {
        "fund": {
            "name": "Test Fund",
            "isin": "INFTEST123",
            "category": "Flexi Cap",
        },
        "elevation": {},
        "protection": {},
        "resilience": {},
    }

    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=fingerprint,
        nav_artifact_version=2,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    with pytest.raises(
        ValueError,
        match="greater than the existing version",
    ):
        store.append(
            fingerprint=fingerprint,
            nav_artifact_version=2,
            generated_at="2026-08-20T00:00:00+05:30",
        )


def test_fingerprint_evidence_store_rejects_append_to_older_nav_artifact_version(
    tmp_path,
):
    path = tmp_path / "INFTEST123.json"

    fingerprint = {
        "fund": {
            "name": "Test Fund",
            "isin": "INFTEST123",
            "category": "Flexi Cap",
        },
        "elevation": {},
        "protection": {},
        "resilience": {},
    }

    store = FingerprintEvidenceStore(path)

    store.create(
        fingerprint=fingerprint,
        nav_artifact_version=2,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    with pytest.raises(
        ValueError,
        match="greater than the existing version",
    ):
        store.append(
            fingerprint=fingerprint,
            nav_artifact_version=1,
            generated_at="2026-08-20T00:00:00+05:30",
        )
