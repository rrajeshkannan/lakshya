import json

import pandas as pd

from fund_analysis.analyze_fund import analyze_fund
from fund_analysis.nav_evidence import NavEvidenceStore
from lakshya_core.fund_fingerprint import build_fund_behavioural_fingerprint
from lakshya_core.models import Fund


def test_analyze_fund_builds_fingerprint_from_persisted_nav(
    tmp_path,
):
    fund = Fund(
        name="Test Fund",
        isin="TEST123",
        category="Flexi Cap",
    )

    nav = pd.DataFrame(
        {
            "date": pd.date_range(
                "2010-01-01",
                periods=4500,
                freq="D",
            ),
            "nav": list(range(100, 4600)),
        }
    )

    nav_path = tmp_path / "TEST123.json"
    nav_store = NavEvidenceStore(nav_path)
    nav_store.create(
        isin=fund.isin,
        scheme_code=12345,
        source="mfapi.in",
        nav=nav,
        retrieved_at="2026-08-17T16:00:00+05:30",
    )

    fingerprint_path = tmp_path / "fingerprint.json"

    fingerprint, action = analyze_fund(
        fund=fund,
        nav_evidence_path=nav_path,
        fingerprint_evidence_path=fingerprint_path,
        generated_at="2026-08-17T16:00:00+05:30",
    )

    assert action == "created"
    assert fingerprint.fund is fund
    assert fingerprint.elevation is not None
    assert fingerprint.protection is not None
    assert fingerprint_path.exists()

    payload = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    assert payload["fund"]["isin"] == "TEST123"
    assert payload["nav_artifact_version"] == 1


def test_fund_behavioural_fingerprint_can_be_built_from_nav_history():
    # The Fund-stage engine assembles the active behavioural dimensions from
    # the same observed NAV history. No scoring, ranking, suitability
    # judgement, or benchmark comparison happens at this boundary.
    fund = Fund(
        name="Test Fund",
        isin="TEST123",
        category="Flexi Cap",
    )

    dates = pd.date_range("2010-01-01", periods=4500, freq="D")
    values = list(range(100, 4600))

    drawdown_start = 3000
    drawdown_trough = 3100
    recovery_end = 3300
    peak_value = values[drawdown_start]
    trough_value = 2500

    for i in range(drawdown_start, drawdown_trough):
        progress = (i - drawdown_start) / (drawdown_trough - drawdown_start)
        values[i] = peak_value - ((peak_value - trough_value) * progress)

    values[drawdown_trough] = trough_value

    for i in range(drawdown_trough + 1, recovery_end):
        progress = (i - drawdown_trough) / (recovery_end - drawdown_trough)
        values[i] = trough_value + ((peak_value - trough_value) * progress)

    values[recovery_end] = peak_value

    nav = pd.DataFrame({"date": dates, "nav": values})

    fingerprint = build_fund_behavioural_fingerprint(
        fund=fund,
        nav=nav,
    )

    assert fingerprint.fund is fund
    assert fingerprint.elevation.rolling_3y is not None
    assert fingerprint.elevation.rolling_5y is not None
    assert fingerprint.elevation.rolling_7y is not None
    assert fingerprint.elevation.rolling_10y is not None
    assert fingerprint.protection.observations == len(nav)


def test_analyze_fund_appends_fingerprint_when_nav_version_advances(
    tmp_path,
):
    fund = Fund(
        name="Test Fund",
        isin="TEST123",
        category="Flexi Cap",
    )

    nav_path = tmp_path / "TEST123.json"
    fingerprint_path = tmp_path / "fingerprint.json"

    nav_v1 = pd.DataFrame(
        {
            "date": pd.date_range(
                "2010-01-01",
                periods=4500,
                freq="D",
            ),
            "nav": list(range(100, 4600)),
        }
    )

    nav_store = NavEvidenceStore(nav_path)
    nav_store.create(
        isin=fund.isin,
        scheme_code=12345,
        source="mfapi.in",
        nav=nav_v1,
        retrieved_at="2026-08-18T00:00:00+05:30",
    )

    analyze_fund(
        fund=fund,
        nav_evidence_path=nav_path,
        fingerprint_evidence_path=fingerprint_path,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    first_payload = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    assert first_payload["artifact_version"] == 1
    assert first_payload["nav_artifact_version"] == 1

    nav_v2 = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-08-20"]),
            "nav": [4700.0],
        }
    )

    nav_store.update(
        nav=nav_v2,
        retrieved_at="2026-08-20T00:00:00+05:30",
    )

    analyze_fund(
        fund=fund,
        nav_evidence_path=nav_path,
        fingerprint_evidence_path=fingerprint_path,
        generated_at="2026-08-20T00:00:00+05:30",
    )

    second_payload = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    assert second_payload["artifact_version"] == 2
    assert second_payload["nav_artifact_version"] == 2


def test_analyze_fund_does_not_append_when_fingerprint_is_current(
    tmp_path,
):
    fund = Fund(
        name="Test Fund",
        isin="TEST123",
        category="Flexi Cap",
    )

    nav_path = tmp_path / "TEST123.json"
    fingerprint_path = tmp_path / "fingerprint.json"

    nav = pd.DataFrame(
        {
            "date": pd.date_range(
                "2010-01-01",
                periods=4500,
                freq="D",
            ),
            "nav": list(range(100, 4600)),
        }
    )

    nav_store = NavEvidenceStore(nav_path)
    nav_store.create(
        isin=fund.isin,
        scheme_code=12345,
        source="mfapi.in",
        nav=nav,
        retrieved_at="2026-08-20T00:00:00+05:30",
    )

    fingerprint, action = analyze_fund(
        fund=fund,
        nav_evidence_path=nav_path,
        fingerprint_evidence_path=fingerprint_path,
        generated_at="2026-08-20T00:00:00+05:30",
    )

    assert action == "created"

    first_payload = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    assert first_payload["artifact_version"] == 1
    assert first_payload["nav_artifact_version"] == 1

    fingerprint, action = analyze_fund(
        fund=fund,
        nav_evidence_path=nav_path,
        fingerprint_evidence_path=fingerprint_path,
        generated_at="2026-08-20T01:00:00+05:30",
    )

    assert action == "current"

    second_payload = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    assert second_payload["artifact_version"] == 1
    assert second_payload["nav_artifact_version"] == 1
    assert second_payload["generated_at"] == "2026-08-20T00:00:00+05:30"
