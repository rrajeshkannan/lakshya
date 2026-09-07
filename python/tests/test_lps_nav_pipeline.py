import pandas as pd

from lps.nav_evidence import NavEvidenceStore
from lps.nav_pipeline import run_nav_pipeline


class FakeNavSource:
    def __init__(self, failing=None):
        self.failing = set(failing or [])

    def resolve_scheme_code(self, isin):
        if isin in self.failing:
            raise ValueError(f"synthetic failure for {isin}")
        return 100 + len(isin)

    def fetch_nav_history(self, scheme_code):
        return pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-08-03", "2026-08-02", "2026-08-01"]),
                "nav": [103.0, 102.0, 101.0],
            }
        )


def test_run_nav_pipeline_creates_evidence(tmp_path):
    results = run_nav_pipeline(
        isins=["ISIN_A", "ISIN_B"],
        nav_source=FakeNavSource(),
        data_root=tmp_path,
        retrieved_at="2026-08-18T00:00:00+05:30",
    )

    assert [result["status"] for result in results] == ["success", "success"]
    assert [result["nav_action"] for result in results] == ["created", "created"]

    store = NavEvidenceStore(tmp_path / "nav" / "ISIN_A.json")
    assert store.latest_date().date().isoformat() == "2026-08-03"


def test_run_nav_pipeline_updates_only_new_observations(tmp_path):
    path = tmp_path / "nav" / "ISIN_A.json"
    store = NavEvidenceStore(path)
    store.create(
        isin="ISIN_A",
        scheme_code=123,
        source="mfapi.in",
        nav=pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-08-02", "2026-08-01"]),
                "nav": [102.0, 101.0],
            }
        ),
        retrieved_at="2026-08-18T00:00:00+05:30",
    )

    class AdvancingSource(FakeNavSource):
        def fetch_nav_history(self, scheme_code):
            return pd.DataFrame(
                {
                    "date": pd.to_datetime(
                        ["2026-08-04", "2026-08-03", "2026-08-02", "2026-08-01"]
                    ),
                    "nav": [104.0, 103.0, 102.0, 101.0],
                }
            )

    results = run_nav_pipeline(
        isins=["ISIN_A"],
        nav_source=AdvancingSource(),
        data_root=tmp_path,
        retrieved_at="2026-08-20T00:00:00+05:30",
    )

    assert results[0]["status"] == "success"
    assert results[0]["nav_action"] == "updated"
    assert NavEvidenceStore(path).latest_date().date().isoformat() == "2026-08-04"


def test_run_nav_pipeline_leaves_unchanged_evidence_unchanged(tmp_path):
    path = tmp_path / "nav" / "ISIN_A.json"
    store = NavEvidenceStore(path)
    store.create(
        isin="ISIN_A",
        scheme_code=123,
        source="mfapi.in",
        nav=pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-08-03", "2026-08-02", "2026-08-01"]),
                "nav": [103.0, 102.0, 101.0],
            }
        ),
        retrieved_at="2026-08-18T00:00:00+05:30",
    )

    results = run_nav_pipeline(
        isins=["ISIN_A"],
        nav_source=FakeNavSource(),
        data_root=tmp_path,
        retrieved_at="2026-08-20T00:00:00+05:30",
    )

    assert results[0]["nav_action"] == "unchanged"
    assert NavEvidenceStore(path).artifact_version() == 1


def test_run_nav_pipeline_reports_failure_and_continues(tmp_path):
    results = run_nav_pipeline(
        isins=["ISIN_A", "ISIN_B", "ISIN_C"],
        nav_source=FakeNavSource(failing={"ISIN_B"}),
        data_root=tmp_path,
        retrieved_at="2026-08-18T00:00:00+05:30",
    )

    assert [result["status"] for result in results] == [
        "success",
        "failed",
        "success",
    ]
    assert "synthetic failure" in results[1]["error"]


def test_run_nav_pipeline_reports_progress(tmp_path):
    messages = []

    results = run_nav_pipeline(
        isins=["ISIN_A"],
        nav_source=FakeNavSource(),
        data_root=tmp_path,
        retrieved_at="2026-08-18T00:00:00+05:30",
        progress=messages.append,
    )

    assert results[0]["status"] == "success"
    assert messages[0].startswith("[01/01] ISIN_A")
    assert any("NAV created" in message for message in messages)
