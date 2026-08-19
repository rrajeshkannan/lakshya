import json

import pandas as pd

from fund_analysis.run_fund_pipeline import run_fund_pipeline
from lakshya_core.models import Fund
from fund_analysis.nav_evidence import NavEvidenceStore


def test_run_fund_pipeline_acquires_nav_and_analyzes_each_fund(
    tmp_path,
    monkeypatch,
):
    funds = [
        Fund(
            name="Fund A",
            isin="ISIN_A",
            category="Small Cap",
        ),
        Fund(
            name="Fund B",
            isin="ISIN_B",
            category="Flexi Cap",
        ),
    ]

    class FakeNavSource:
        def resolve_scheme_code(self, isin):
            return {
                "ISIN_A": 111,
                "ISIN_B": 222,
            }[isin]

        def fetch_nav_history(self, scheme_code):
            return pd.DataFrame(
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

    analyzed = []

    def fake_analyze_fund(
        *,
        fund,
        nav_evidence_path,
        fingerprint_evidence_path,
        generated_at,
    ):
        analyzed.append(fund.isin)
        return None, "created"

    monkeypatch.setattr(
        "fund_analysis.run_fund_pipeline.analyze_fund",
        fake_analyze_fund,
    )

    results = run_fund_pipeline(
        funds=funds,
        nav_source=FakeNavSource(),
        data_root=tmp_path,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    assert analyzed == [
        "ISIN_A",
        "ISIN_B",
    ]

    assert len(results) == 2

    assert all(
        result["status"] == "success"
        for result in results
    )


def test_run_fund_pipeline_reports_source_failure_and_continues(
    tmp_path,
    monkeypatch,
):
    funds = [
        Fund(
            name="Fund A",
            isin="ISIN_A",
            category="Small Cap",
        ),
        Fund(
            name="Fund B",
            isin="ISIN_B",
            category="Flexi Cap",
        ),
        Fund(
            name="Fund C",
            isin="ISIN_C",
            category="Large Cap",
        ),
    ]

    class FakeNavSource:
        def resolve_scheme_code(self, isin):
            if isin == "ISIN_B":
                raise ValueError("synthetic MFAPI failure")

            return 123

        def fetch_nav_history(self, scheme_code):
            return pd.DataFrame(
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

    analyzed = []

    def fake_analyze_fund(
        *,
        fund,
        nav_evidence_path,
        fingerprint_evidence_path,
        generated_at,
    ):
        analyzed.append(fund.isin)
        return None, "created"

    monkeypatch.setattr(
        "fund_analysis.run_fund_pipeline.analyze_fund",
        fake_analyze_fund,
    )

    results = run_fund_pipeline(
        funds=funds,
        nav_source=FakeNavSource(),
        data_root=tmp_path,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    assert analyzed == [
        "ISIN_A",
        "ISIN_C",
    ]

    assert results[0]["status"] == "success"

    assert results[1]["status"] == "failed"
    assert results[1]["isin"] == "ISIN_B"
    assert "synthetic MFAPI failure" in results[1]["error"]

    assert results[2]["status"] == "success"


def test_run_fund_pipeline_reports_progress(
    tmp_path,
    monkeypatch,
):
    funds = [
        Fund(
            name="Fund A",
            isin="ISIN_A",
            category="Small Cap",
        ),
    ]

    class FakeNavSource:
        def resolve_scheme_code(self, isin):
            return 123

        def fetch_nav_history(self, scheme_code):
            return pd.DataFrame(
                {
                    "date": pd.to_datetime(
                        ["2026-08-03", "2026-08-02", "2026-08-01"]
                    ),
                    "nav": [103.0, 102.0, 101.0],
                }
            )

    monkeypatch.setattr(
        "fund_analysis.run_fund_pipeline.analyze_fund",
        lambda **kwargs: (None, "created"),
    )

    messages = []

    results = run_fund_pipeline(
        funds=funds,
        nav_source=FakeNavSource(),
        data_root=tmp_path,
        generated_at="2026-08-18T00:00:00+05:30",
        progress=messages.append,
    )

    assert results[0]["status"] == "success"
    assert messages


def test_run_fund_pipeline_reports_analysis_value_error_as_failure(
    tmp_path,
    monkeypatch,
):
    fund = Fund(
        name="Fund A",
        isin="ISIN_A",
        category="Small Cap",
    )

    class FakeNavSource:
        def resolve_scheme_code(self, isin):
            return 123

        def fetch_nav_history(self, scheme_code):
            return pd.DataFrame(
                {
                    "date": pd.to_datetime(
                        ["2026-08-03", "2026-08-02", "2026-08-01"]
                    ),
                    "nav": [103.0, 102.0, 101.0],
                }
            )

    def fake_analyze_fund(**kwargs):
        raise ValueError("some genuine analysis failure")

    monkeypatch.setattr(
        "fund_analysis.run_fund_pipeline.analyze_fund",
        fake_analyze_fund,
    )

    results = run_fund_pipeline(
        funds=[fund],
        nav_source=FakeNavSource(),
        data_root=tmp_path,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    assert results[0]["status"] == "failed"
    assert "some genuine analysis failure" in results[0]["error"]


def test_run_fund_pipeline_regenerates_fingerprint_when_nav_advances(
    tmp_path,
):
    fund = Fund(
        name="Fund A",
        isin="ISIN_A",
        category="Small Cap",
    )

    nav_path = (
        tmp_path
        / "nav"
        / "ISIN_A.json"
    )

    fingerprint_path = (
        tmp_path
        / "fingerprints"
        / "ISIN_A.json"
    )

    nav_store = NavEvidenceStore(nav_path)

    # Existing NAV evidence is already at version 1.
    nav_v1 = pd.DataFrame(
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

    nav_store.create(
        isin="ISIN_A",
        scheme_code=123,
        source="mfapi.in",
        nav=nav_v1,
        retrieved_at="2026-08-18T00:00:00+05:30",
    )

    # The existing fingerprint was produced from NAV artifact v1.
    fingerprint_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fingerprint_path.write_text(
        """
{
  "artifact_version": 1,
  "nav_artifact_version": 1
}
""".strip(),
        encoding="utf-8",
    )

    class FakeNavSource:
        def resolve_scheme_code(self, isin):
            return 123

        def fetch_nav_history(self, scheme_code):
            return pd.DataFrame(
                {
                    "date": pd.to_datetime(
                        [
                            "2026-08-04",
                            "2026-08-03",
                            "2026-08-02",
                            "2026-08-01",
                        ]
                    ),
                    "nav": [104.0, 103.0, 102.0, 101.0],
                }
            )

    results = run_fund_pipeline(
        funds=[fund],
        nav_source=FakeNavSource(),
        data_root=tmp_path,
        generated_at="2026-08-20T00:00:00+05:30",
    )

    assert results[0]["status"] == "success"

    assert results[0]["nav_action"] == "updated"

    assert results[0]["fingerprint_action"] == "appended"

    payload = json.loads(
        fingerprint_path.read_text(
            encoding="utf-8"
        )
    )

    assert payload["nav_artifact_version"] == 2
