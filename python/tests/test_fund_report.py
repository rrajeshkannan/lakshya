import json

from fund_analysis.report_fund_evidence import build_fund_evidence_views, load_fund_evidence_report, render_fund_evidence_report


def test_load_fund_evidence_report_reads_all_fingerprint_artifacts(
    tmp_path,
):
    fingerprints_dir = tmp_path / "fingerprints"
    fingerprints_dir.mkdir()

    (fingerprints_dir / "ISIN_A.json").write_text(
        json.dumps(
            {
                "fund": {
                    "name": "Fund A",
                    "isin": "ISIN_A",
                    "category": "Small Cap",
                },
                "elevation": {
                    "rolling_3y": {
                        "median": 15.0,
                    },
                    "rolling_5y": {
                        "median": 16.0,
                    },
                    "rolling_7y": {
                        "median": 17.0,
                    },
                    "rolling_10y": {
                        "median": 18.0,
                    },
                },
                "protection": {
                    "observations": 100,
                    "median_severity_pct": 3.0,
                    "percentile_90_severity_pct": 10.0,
                    "percentile_95_severity_pct": 15.0,
                    "percentile_99_severity_pct": 20.0,
                    "maximum_severity_pct": 25.0,
                },
                "resilience": {
                    "episode_count": 5,
                    "recovered_count": 4,
                    "ongoing_count": 1,
                    "median_depth_pct": 10.0,
                    "worst_depth_pct": 25.0,
                },
            }
        ),
        encoding="utf-8",
    )

    (fingerprints_dir / "ISIN_B.json").write_text(
        json.dumps(
            {
                "fund": {
                    "name": "Fund B",
                    "isin": "ISIN_B",
                    "category": "Flexi Cap",
                },
                "elevation": {
                    "rolling_3y": {
                        "median": 12.0,
                    },
                    "rolling_5y": {
                        "median": 13.0,
                    },
                    "rolling_7y": {
                        "median": 14.0,
                    },
                    "rolling_10y": {
                        "median": 15.0,
                    },
                },
                "protection": {
                    "observations": 100,
                    "median_severity_pct": 4.0,
                    "percentile_90_severity_pct": 12.0,
                    "percentile_95_severity_pct": 18.0,
                    "percentile_99_severity_pct": 23.0,
                    "maximum_severity_pct": 30.0,
                },
                "resilience": {
                    "episode_count": 7,
                    "recovered_count": 7,
                    "ongoing_count": 0,
                    "median_depth_pct": 12.0,
                    "worst_depth_pct": 30.0,
                },
            }
        ),
        encoding="utf-8",
    )

    report = load_fund_evidence_report(
        fingerprints_dir
    )

    assert len(report) == 2

    assert report[0]["fund"]["isin"] == "ISIN_A"
    assert report[1]["fund"]["isin"] == "ISIN_B"

    assert (
        report[0]["elevation"]["rolling_5y"]["median"]
        == 16.0
    )

    assert (
        report[1]["protection"]["maximum_severity_pct"]
        == 30.0
    )

    assert (
        report[0]["resilience"]["recovered_count"]
        == 4
    )


def test_fund_evidence_report_extracts_three_compass_views(
    tmp_path,
):
    fingerprints_dir = tmp_path / "fingerprints"
    fingerprints_dir.mkdir()

    payload = {
        "fund": {
            "name": "Fund A",
            "isin": "ISIN_A",
            "category": "Small Cap",
        },
        "elevation": {
            "rolling_3y": {"median": 15.0},
            "rolling_5y": {"median": 16.0},
            "rolling_7y": {"median": 17.0},
            "rolling_10y": {"median": 18.0},
        },
        "protection": {
            "observations": 100,
            "median_severity_pct": 3.0,
            "percentile_90_severity_pct": 10.0,
            "percentile_95_severity_pct": 15.0,
            "percentile_99_severity_pct": 20.0,
            "maximum_severity_pct": 25.0,
        },
        "resilience": {
            "episode_count": 5,
            "recovered_count": 4,
            "ongoing_count": 1,
            "median_depth_pct": 10.0,
            "worst_depth_pct": 25.0,
            "median_decline_days_recovered": 18.0,
            "median_recovery_days": 42.0,
            "median_underwater_days_recovered": 75.0,
            "median_underwater_days_ongoing": 120.0,
        },
    }

    (fingerprints_dir / "ISIN_A.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    report = load_fund_evidence_report(
        fingerprints_dir
    )

    views = build_fund_evidence_views(report)

    assert set(views) == {
        "elevation",
        "protection",
        "resilience",
    }

    assert views["elevation"][0]["fund"]["isin"] == "ISIN_A"
    assert (
        views["elevation"][0]["rolling_5y_median"]
        == 16.0
    )

    assert (
        views["protection"][0]["median_severity_pct"]
        == 3.0
    )

    assert (
        views["protection"][0]["percentile_95_severity_pct"]
        == 15.0
    )

    assert (
        views["resilience"][0]["episode_count"]
        == 5
    )

    assert (
        views["resilience"][0]["recovered_count"]
        == 4
    )

    assert (
        views["resilience"][0]["ongoing_count"]
        == 1
    )


def test_render_fund_evidence_report_contains_three_compass_sections():
    views = {
        "elevation": [
            {
                "fund": {
                    "name": "Fund A",
                    "isin": "ISIN_A",
                    "category": "Small Cap",
                },
                "rolling_3y_median": 15.0,
                "rolling_5y_median": 16.0,
                "rolling_7y_median": 17.0,
                "rolling_10y_median": 18.0,
            }
        ],
        "protection": [
            {
                "fund": {
                    "name": "Fund A",
                    "isin": "ISIN_A",
                    "category": "Small Cap",
                },
                "observations": 100,
                "median_severity_pct": 3.0,
                "percentile_90_severity_pct": 10.0,
                "percentile_95_severity_pct": 15.0,
                "percentile_99_severity_pct": 20.0,
                "maximum_severity_pct": 25.0,
            }
        ],
        "resilience": [
            {
                "fund": {
                    "name": "Fund A",
                    "isin": "ISIN_A",
                    "category": "Small Cap",
                },
                "episode_count": 5,
                "recovered_count": 4,
                "ongoing_count": 1,
                "median_depth_pct": 10.0,
                "median_decline_days_recovered": 18.0,
                "median_recovery_days": 42.0,
                "median_underwater_days_recovered": 75.0,
                "median_underwater_days_ongoing": 120.0,
                "worst_depth_pct": 25.0,
            }
        ],
    }

    report = render_fund_evidence_report(views)

    assert "ELEVATION" in report
    assert "PROTECTION" in report
    assert "RESILIENCE" in report

    assert "Fund A" in report
    assert "15.00%" in report
    assert "25.00%" in report


def test_fund_evidence_report_preserves_missing_elevation_horizon():
    report = [
        {
            "fund": {
                "name": "Short History Fund",
                "isin": "ISIN_SHORT",
                "category": "Small Cap",
            },
            "elevation": {
                "rolling_3y": {
                    "median": 15.0,
                },
                "rolling_5y": {
                    "median": 16.0,
                },
                "rolling_7y": None,
                "rolling_10y": None,
            },
            "protection": {
                "observations": 100,
                "median_severity_pct": 3.0,
                "percentile_90_severity_pct": 10.0,
                "percentile_95_severity_pct": 15.0,
                "percentile_99_severity_pct": 20.0,
                "maximum_severity_pct": 25.0,
            },
            "resilience": {
                "episode_count": 5,
                "recovered_count": 4,
                "ongoing_count": 1,
                "median_depth_pct": 10.0,
                "worst_depth_pct": 25.0,
                "median_decline_days_recovered": 18.0,
                "median_recovery_days": 42.0,
                "median_underwater_days_recovered": 75.0,
                "median_underwater_days_ongoing": 120.0,
            },
        }
    ]

    views = build_fund_evidence_views(report)

    assert (
        views["elevation"][0]["rolling_3y_median"]
        == 15.0
    )

    assert (
        views["elevation"][0]["rolling_5y_median"]
        == 16.0
    )

    assert (
        views["elevation"][0]["rolling_7y_median"]
        is None
    )

    assert (
        views["elevation"][0]["rolling_10y_median"]
        is None
    )


def test_render_fund_evidence_report_shows_na_for_missing_evidence():
    views = {
        "elevation": [
            {
                "fund": {
                    "name": "Short History Fund",
                    "isin": "ISIN_SHORT",
                    "category": "Small Cap",
                },
                "rolling_3y_median": 0.15,
                "rolling_5y_median": 0.16,
                "rolling_7y_median": None,
                "rolling_10y_median": None,
            }
        ],
        "protection": [],
        "resilience": [],
    }

    report = render_fund_evidence_report(views)

    assert "15.00%" in report
    assert "16.00%" in report
    assert "N/A" in report


def test_render_fund_evidence_report_converts_elevation_decimal_to_percent():
    views = {
        "elevation": [
            {
                "fund": {
                    "name": "Fund A",
                    "isin": "ISIN_A",
                    "category": "Small Cap",
                },
                "rolling_3y_median": 0.15,
                "rolling_5y_median": 0.20,
                "rolling_7y_median": 0.21,
                "rolling_10y_median": 0.22,
            }
        ],
        "protection": [],
        "resilience": [],
    }

    report = render_fund_evidence_report(views)

    assert "15.00%" in report
    assert "20.00%" in report
    assert "21.00%" in report
    assert "22.00%" in report


def test_fund_evidence_report_includes_resilience_duration_evidence():
    views = {
        "elevation": [],
        "protection": [],
        "resilience": [
            {
                "fund": {
                    "name": "Fund A",
                    "isin": "ISIN_A",
                    "category": "Small Cap",
                },
                "episode_count": 5,
                "recovered_count": 4,
                "ongoing_count": 1,
                "median_depth_pct": 10.0,
                "worst_depth_pct": 25.0,
                "median_decline_days_recovered": 18.0,
                "median_recovery_days": 42.0,
                "median_underwater_days_recovered": 75.0,
                "median_underwater_days_ongoing": 120.0,
            }
        ],
    }

    report = render_fund_evidence_report(views)

    assert "Median Decline Days" in report
    assert "Median Recovery Days" in report
    assert "Median Underwater Days" in report

    assert "18.0" in report
    assert "42.0" in report
    assert "75.0" in report
    assert "120.0" in report


def test_render_fund_evidence_report_shows_na_for_missing_resilience_duration():
    views = {
        "elevation": [],
        "protection": [],
        "resilience": [
            {
                "fund": {
                    "name": "Recovered Fund",
                    "isin": "ISIN_A",
                    "category": "Small Cap",
                },
                "episode_count": 5,
                "recovered_count": 5,
                "ongoing_count": 0,
                "median_depth_pct": 10.0,
                "worst_depth_pct": 25.0,
                "median_decline_days_recovered": 18.0,
                "median_recovery_days": 42.0,
                "median_underwater_days_recovered": 75.0,
                "median_underwater_days_ongoing": None,
            }
        ],
    }

    report = render_fund_evidence_report(views)

    assert "18.0" in report
    assert "42.0" in report
    assert "75.0" in report
    assert "N/A" in report
