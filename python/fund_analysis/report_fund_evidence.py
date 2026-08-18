import json
from pathlib import Path


def load_fund_evidence_report(
    fingerprints_dir: Path,
) -> list[dict]:
    """
    Load all Fund behavioural fingerprint evidence artifacts.

    This is a read-only reporting boundary. It does not modify,
    score, rank, or interpret the evidence.
    """

    fingerprints_dir = Path(fingerprints_dir)

    if not fingerprints_dir.exists():
        raise ValueError(
            f"Fingerprint evidence directory does not exist: "
            f"{fingerprints_dir}"
        )

    artifacts = []

    for path in sorted(
        fingerprints_dir.glob("*.json")
    ):
        with path.open(
            "r",
            encoding="utf-8",
        ) as f:
            artifacts.append(json.load(f))

    return artifacts


def _median(evidence):
    if evidence is None:
        return None

    return evidence["median"]


def build_fund_evidence_views(
    report: list[dict],
) -> dict[str, list[dict]]:
    """
    Reshape Fund fingerprint evidence into the three Compass views.

    This function does not score, rank, judge, or interpret the evidence.
    """

    elevation = []
    protection = []
    resilience = []

    for artifact in report:
        fund = artifact["fund"]

        elevation_evidence = artifact["elevation"]
        protection_evidence = artifact["protection"]
        resilience_evidence = artifact["resilience"]

        elevation.append(
            {
                "fund": fund,
                "rolling_3y_median": _median(
                    elevation_evidence["rolling_3y"]
                ),
                "rolling_5y_median": _median(
                    elevation_evidence["rolling_5y"]
                ),
                "rolling_7y_median": _median(
                    elevation_evidence["rolling_7y"]
                ),
                "rolling_10y_median": _median(
                    elevation_evidence["rolling_10y"]
                ),
            }
        )

        protection.append(
            {
                "fund": fund,
                "observations": (
                    protection_evidence["observations"]
                ),
                "median_severity_pct": (
                    protection_evidence[
                        "median_severity_pct"
                    ]
                ),
                "percentile_90_severity_pct": (
                    protection_evidence[
                        "percentile_90_severity_pct"
                    ]
                ),
                "percentile_95_severity_pct": (
                    protection_evidence[
                        "percentile_95_severity_pct"
                    ]
                ),
                "percentile_99_severity_pct": (
                    protection_evidence[
                        "percentile_99_severity_pct"
                    ]
                ),
                "maximum_severity_pct": (
                    protection_evidence[
                        "maximum_severity_pct"
                    ]
                ),
            }
        )

        resilience.append(
            {
                "fund": fund,
                "episode_count": (
                    resilience_evidence["episode_count"]
                ),
                "recovered_count": (
                    resilience_evidence["recovered_count"]
                ),
                "ongoing_count": (
                    resilience_evidence["ongoing_count"]
                ),
                "median_depth_pct": (
                    resilience_evidence["median_depth_pct"]
                ),
                "worst_depth_pct": (
                    resilience_evidence["worst_depth_pct"]
                ),
                "median_decline_days_recovered": (
                    resilience_evidence[
                        "median_decline_days_recovered"
                    ]
                ),
                "median_recovery_days": (
                    resilience_evidence[
                        "median_recovery_days"
                    ]
                ),
                "median_underwater_days_recovered": (
                    resilience_evidence[
                        "median_underwater_days_recovered"
                    ]
                ),
                "median_underwater_days_ongoing": (
                    resilience_evidence[
                        "median_underwater_days_ongoing"
                    ]
                ),
            }
        )

    return {
        "elevation": elevation,
        "protection": protection,
        "resilience": resilience,
    }


def _format_pct(value):
    if value is None:
        return "N/A"

    return f"{value:.2f}%"


def _format_return(value):
    if value is None:
        return "N/A"

    return f"{value * 100:.2f}%"


def _format_days(value):
    if value is None:
        return "N/A"

    return f"{value:.1f}"


def render_fund_evidence_report(
    views: dict[str, list[dict]],
) -> str:
    """
    Render the three Fund Compass evidence views as plain text.

    This function is descriptive only. It does not score, rank,
    judge, or interpret the evidence.
    """

    lines = []

    lines.append("ELEVATION")
    lines.append("")
    lines.append(
        "Fund | 3Y | 5Y | 7Y | 10Y"
    )
    lines.append(
        "-----|----|----|----|-----"
    )

    for row in views["elevation"]:
        fund = row["fund"]

        lines.append(
            f"{fund['name']} | "
            + _format_return(row["rolling_3y_median"]) + " | "
            + _format_return(row["rolling_5y_median"]) + " | "
            + _format_return(row["rolling_7y_median"]) + " | "
            + _format_return(row["rolling_10y_median"])
        )

    lines.append("")
    lines.append("")
    lines.append("PROTECTION")
    lines.append("")
    lines.append(
        "Fund | Median | P90 | P95 | P99 | Max"
    )
    lines.append(
        "-----|--------|-----|-----|-----|----"
    )

    for row in views["protection"]:
        fund = row["fund"]

        lines.append(
            f"{fund['name']} | "
            f"{_format_pct(row['median_severity_pct'])} | "
            f"{_format_pct(row['percentile_90_severity_pct'])} | "
            f"{_format_pct(row['percentile_95_severity_pct'])} | "
            f"{_format_pct(row['percentile_99_severity_pct'])} | "
            f"{_format_pct(row['maximum_severity_pct'])}"
        )

    lines.append("")
    lines.append("")
    lines.append("RESILIENCE")
    lines.append("")
    lines.append(
        "Fund | Episodes | Recovered | Ongoing | "
        "Median Depth | Worst Depth | "
        "Median Decline Days | Median Recovery Days | "
        "Median Underwater Days Recovered | "
        "Median Underwater Days Ongoing"
    )
    lines.append(
        "-----|----------|-----------|---------|--------------|------------|"
        "--------------------|---------------------|"
        "---------------------------------|"
        "-------------------------------"
    )

    for row in views["resilience"]:
        fund = row["fund"]

        lines.append(
            f"{fund['name']} | "
            f"{row['episode_count']} | "
            f"{row['recovered_count']} | "
            f"{row['ongoing_count']} | "
            f"{row['median_depth_pct']:.2f}% | "
            f"{row['worst_depth_pct']:.2f}% | "
            + _format_days(
                row["median_decline_days_recovered"]
            ) + " | "
            + _format_days(
                row["median_recovery_days"]
            ) + " | "
            + _format_days(
                row["median_underwater_days_recovered"]
            ) + " | "
            + _format_days(
                row["median_underwater_days_ongoing"]
            )
        )

    return "\n".join(lines)


def main():
    project_root = Path(__file__).resolve().parents[2]

    fingerprints_dir = (
        project_root
        / "data"
        / "fingerprints"
    )

    report = load_fund_evidence_report(
        fingerprints_dir
    )

    views = build_fund_evidence_views(
        report
    )

    print(
        render_fund_evidence_report(
            views
        )
    )


if __name__ == "__main__":
    main()
