from datetime import datetime
from pathlib import Path

from fund_analysis.analyze_fund import analyze_fund
from fund_analysis.universe import load_fund_universe


def main():
    funds = load_fund_universe()

    fund = next(
        fund
        for fund in funds
        if fund.isin == "INF846K01K35"
    )

    project_root = Path(__file__).resolve().parents[2]

    nav_evidence_path = (
        project_root
        / "data"
        / "nav"
        / f"{fund.isin}.json"
    )

    fingerprint_evidence_path = (
        project_root
        / "data"
        / "fingerprints"
        / f"{fund.isin}.json"
    )

    generated_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    fingerprint = analyze_fund(
        fund=fund,
        nav_evidence_path=nav_evidence_path,
        fingerprint_evidence_path=fingerprint_evidence_path,
        generated_at=generated_at,
    )

    print(f"Fund: {fund.name}")
    print(f"ISIN: {fund.isin}")
    print(f"Fingerprint: {fingerprint_evidence_path}")
    print("Fingerprint generated.")


if __name__ == "__main__":
    main()
