import pandas as pd

from fund_analysis.run_fund_pipeline import run_fund_pipeline
from fund_analysis.run_fund_analysis import run_fund_analysis
from lakshya_core.models import Fund


def test_run_fund_analysis_processes_entire_fund_universe(
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

    processed = []

    def fake_analyze_fund(
        *,
        fund,
        nav_evidence_path,
        fingerprint_evidence_path,
        generated_at,
    ):
        processed.append(
            {
                "fund": fund,
                "nav_path": nav_evidence_path,
                "fingerprint_path": fingerprint_evidence_path,
            }
        )

    monkeypatch.setattr(
        "fund_analysis.run_fund_analysis.analyze_fund",
        fake_analyze_fund,
    )

    results = run_fund_analysis(
        funds=funds,
        data_root=tmp_path,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    assert len(processed) == 2

    assert processed[0]["fund"] is funds[0]
    assert processed[1]["fund"] is funds[1]

    assert processed[0]["nav_path"] == (
        tmp_path / "nav" / "ISIN_A.json"
    )

    assert processed[0]["fingerprint_path"] == (
        tmp_path / "fingerprints" / "ISIN_A.json"
    )

    assert processed[1]["nav_path"] == (
        tmp_path / "nav" / "ISIN_B.json"
    )

    assert processed[1]["fingerprint_path"] == (
        tmp_path / "fingerprints" / "ISIN_B.json"
    )

    assert len(results) == 2


def test_run_fund_analysis_reports_failure_without_silently_skipping_fund(
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

    processed = []

    def fake_analyze_fund(
        *,
        fund,
        nav_evidence_path,
        fingerprint_evidence_path,
        generated_at,
    ):
        processed.append(fund.isin)

        if fund.isin == "ISIN_B":
            raise ValueError("synthetic analysis failure")

    monkeypatch.setattr(
        "fund_analysis.run_fund_analysis.analyze_fund",
        fake_analyze_fund,
    )

    results = run_fund_analysis(
        funds=funds,
        data_root=tmp_path,
        generated_at="2026-08-18T00:00:00+05:30",
    )

    assert processed == [
        "ISIN_A",
        "ISIN_B",
        "ISIN_C",
    ]

    assert len(results) == 3

    assert results[0]["status"] == "success"

    assert results[1]["status"] == "failed"
    assert results[1]["isin"] == "ISIN_B"
    assert "synthetic analysis failure" in results[1]["error"]

    assert results[2]["status"] == "success"


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


def test_run_fund_pipeline_treats_existing_fingerprint_as_success(
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
        raise ValueError(
            "Fingerprint evidence artifact already exists: "
            "synthetic/path.json"
        )

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

    assert results[0]["status"] == "success"
    assert results[0]["fingerprint_action"] == "already_exists"


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
        lambda **kwargs: None,
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
