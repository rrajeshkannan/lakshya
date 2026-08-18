from datetime import datetime

from fund_analysis.nav_evidence import NavEvidenceStore
from fund_analysis.nav_source import (
    MfapiNavSource,
    mfapi_http_transport,
)
from fund_analysis.universe import load_fund_universe
from lakshya_core.nav_history import normalize_nav_history


def main():
    funds = load_fund_universe()

    # First real-fund smoke test: Axis Small Cap.
    fund = next(
        fund
        for fund in funds
        if fund.isin == "INF846K01K35"
    )

    source = MfapiNavSource(
        transport=mfapi_http_transport,
    )

    catalog = source.fetch_scheme_catalog()
    source.scheme_catalog = catalog

    scheme_code = source.resolve_scheme_code(fund.isin)

    raw_nav = source.fetch_nav_history(scheme_code)
    nav = normalize_nav_history(raw_nav)

    evidence_path = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "data"
        / "nav"
        / f"{fund.isin}.json"
    )

    store = NavEvidenceStore(evidence_path)

    retrieved_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    if evidence_path.exists():
        latest_date = store.latest_date()

        new_nav = nav[
            nav["date"] > latest_date
        ]

        if new_nav.empty:
            print("No new NAV observations.")
            return

        store.update(
            nav=new_nav,
            retrieved_at=retrieved_at,
        )
        action = "updated"

    else:
        store.create(
            isin=fund.isin,
            scheme_code=scheme_code,
            source="mfapi.in",
            nav=nav,
            retrieved_at=retrieved_at,
        )
        action = "created"

    print(f"Fund: {fund.name}")
    print(f"ISIN: {fund.isin}")
    print(f"Scheme code: {scheme_code}")
    print(f"Observations fetched: {len(nav)}")
    print(f"First date: {nav['date'].min().date()}")
    print(f"Latest date: {nav['date'].max().date()}")
    print(f"Evidence: {evidence_path}")
    print(f"Evidence {action}.")


if __name__ == "__main__":
    main()
