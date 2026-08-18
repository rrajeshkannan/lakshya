import json

import pandas as pd
import pytest

from fund_analysis.nav_evidence import NavEvidenceStore
from lakshya_core.nav_history import normalize_nav_history


def test_nav_evidence_store_creates_new_artifact(tmp_path):
    # A new fund gets a persistent evidence artifact containing the
    # observations actually retrieved from the source.
    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-03",
                    "2026-08-02",
                    "2026-08-01",
                ]
            ),
            "nav": [103.0, 102.0, 101.0],
        }
    )

    path = tmp_path / "INFTEST123_nav.json"

    store = NavEvidenceStore(path)

    store.create(
        isin="INFTEST123",
        scheme_code=12345,
        source="mfapi.in",
        nav=nav,
        retrieved_at="2026-08-17T16:00:00+05:30",
    )

    assert path.exists()

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["isin"] == "INFTEST123"
    assert payload["scheme_code"] == 12345
    assert payload["source"] == "mfapi.in"
    assert payload["artifact_version"] == 1
    assert len(payload["observations"]) == 3

    # Persist newest observation first.
    assert payload["observations"][0]["date"] == "2026-08-03"


def test_nav_evidence_store_prepends_new_observations(tmp_path):
    # Persisted observations are newest-first, so an incremental update
    # prepends genuinely new observations to the existing evidence.
    path = tmp_path / "INFTEST123_nav.json"

    initial = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-03",
                    "2026-08-02",
                    "2026-08-01",
                ]
            ),
            "nav": [103.0, 102.0, 101.0],
        }
    )

    store = NavEvidenceStore(path)

    store.create(
        isin="INFTEST123",
        scheme_code=12345,
        source="mfapi.in",
        nav=initial,
        retrieved_at="2026-08-04T16:00:00+05:30",
    )

    new = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-05",
                    "2026-08-04",
                ]
            ),
            "nav": [105.0, 104.0],
        }
    )

    store.update(
        nav=new,
        retrieved_at="2026-08-06T16:00:00+05:30",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["artifact_version"] == 2

    assert [
        observation["date"]
        for observation in payload["observations"]
    ] == [
        "2026-08-05",
        "2026-08-04",
        "2026-08-03",
        "2026-08-02",
        "2026-08-01",
    ]


def test_nav_evidence_store_rejects_observations_not_strictly_newer(
    tmp_path,
):
    # Existing history ends at 2026-08-03.
    # An update containing 2026-08-03 is not an incremental update.
    # We reject it rather than silently overwriting or deduplicating history.
    path = tmp_path / "INFTEST123_nav.json"

    initial = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-03",
                    "2026-08-02",
                ]
            ),
            "nav": [103.0, 102.0],
        }
    )

    store = NavEvidenceStore(path)

    store.create(
        isin="INFTEST123",
        scheme_code=12345,
        source="mfapi.in",
        nav=initial,
        retrieved_at="2026-08-04T16:00:00+05:30",
    )

    overlapping = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-04",
                    "2026-08-03",
                ]
            ),
            "nav": [104.0, 999.0],
        }
    )

    with pytest.raises(ValueError, match="strictly newer"):
        store.update(
            nav=overlapping,
            retrieved_at="2026-08-05T16:00:00+05:30",
        )


def test_nav_evidence_store_rejects_identity_change(tmp_path):
    # An evidence artifact belongs permanently to one Fund identity.
    path = tmp_path / "INFTEST123_nav.json"

    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-08-03"]),
            "nav": [103.0],
        }
    )

    store = NavEvidenceStore(path)

    store.create(
        isin="INFTEST123",
        scheme_code=12345,
        source="mfapi.in",
        nav=nav,
        retrieved_at="2026-08-04T16:00:00+05:30",
    )

    with pytest.raises(ValueError, match="identity"):
        store.update(
            nav=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2026-08-04"]),
                    "nav": [104.0],
                }
            ),
            retrieved_at="2026-08-05T16:00:00+05:30",
            isin="DIFFERENT123",
        )


def test_nav_evidence_can_be_created_from_normalized_history(tmp_path):
    # The persistent evidence layer consumes the canonical NAV
    # representation produced by the NAV history gate.
    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-03",
                    "2026-08-02",
                    "2026-08-01",
                ]
            ),
            "nav": [103.0, 102.0, 101.0],
        }
    )

    normalized = normalize_nav_history(nav)

    path = tmp_path / "INFTEST123_nav.json"

    store = NavEvidenceStore(path)

    store.create(
        isin="INFTEST123",
        scheme_code=12345,
        source="mfapi.in",
        nav=normalized,
        retrieved_at="2026-08-17T16:00:00+05:30",
    )

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert payload["artifact_version"] == 1
    assert payload["observations"][0]["date"] == "2026-08-03"
    assert payload["observations"][-1]["date"] == "2026-08-01"


def test_nav_evidence_store_returns_no_new_observations_when_history_is_current(
    tmp_path,
):
    path = tmp_path / "INFTEST123.json"

    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-03",
                    "2026-08-02",
                    "2026-08-01",
                ]
            ),
            "nav": [103.0, 102.0, 101.0],
        }
    )

    store = NavEvidenceStore(path)

    store.create(
        isin="INFTEST123",
        scheme_code=12345,
        source="mfapi.in",
        nav=nav,
        retrieved_at="2026-08-04T16:00:00+05:30",
    )

    incoming = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-03",
                    "2026-08-02",
                ]
            ),
            "nav": [999.0, 998.0],
        }
    )

    latest_date = store.latest_date()

    new_observations = incoming[
        incoming["date"] > latest_date
    ]

    assert new_observations.empty


def test_nav_evidence_store_reports_latest_observation_date(tmp_path):
    path = tmp_path / "INFTEST123.json"

    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-03",
                    "2026-08-02",
                    "2026-08-01",
                ]
            ),
            "nav": [103.0, 102.0, 101.0],
        }
    )

    store = NavEvidenceStore(path)

    store.create(
        isin="INFTEST123",
        scheme_code=12345,
        source="mfapi.in",
        nav=nav,
        retrieved_at="2026-08-04T16:00:00+05:30",
    )

    assert store.latest_date() == pd.Timestamp("2026-08-03")
