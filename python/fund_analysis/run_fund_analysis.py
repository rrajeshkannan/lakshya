from pathlib import Path

from fund_analysis.analyze_fund import analyze_fund


def run_fund_analysis(
    *,
    funds,
    data_root: Path,
    generated_at: str,
):
    """
    Run Fund-stage analysis for every Fund in the supplied universe.

    This is orchestration only. Individual Fund analysis remains
    delegated to analyze_fund().
    """

    data_root = Path(data_root)

    results = []

    for fund in funds:
        nav_evidence_path = (
            data_root
            / "nav"
            / f"{fund.isin}.json"
        )

        fingerprint_evidence_path = (
            data_root
            / "fingerprints"
            / f"{fund.isin}.json"
        )

        try:
            analyze_fund(
                fund=fund,
                nav_evidence_path=nav_evidence_path,
                fingerprint_evidence_path=fingerprint_evidence_path,
                generated_at=generated_at,
            )

            results.append(
                {
                    "isin": fund.isin,
                    "status": "success",
                }
            )

        except Exception as exc:
            results.append(
                {
                    "isin": fund.isin,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return results
