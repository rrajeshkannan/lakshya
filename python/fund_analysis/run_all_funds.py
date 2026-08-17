from datetime import datetime
from pathlib import Path

from fund_analysis.nav_source import (
    MfapiNavSource,
    mfapi_http_transport,
)
from fund_analysis.run_fund_pipeline import run_fund_pipeline
from fund_analysis.universe import load_fund_universe


def main():
    project_root = Path(__file__).resolve().parents[2]

    funds = load_fund_universe()

    source = MfapiNavSource(
        transport=mfapi_http_transport,
    )

    catalog = source.fetch_scheme_catalog()
    source.scheme_catalog = catalog

    generated_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    results = run_fund_pipeline(
        funds=funds,
        nav_source=source,
        data_root=project_root / "data",
        generated_at=generated_at,
        progress=print,
    )

    print(f"Funds in universe: {len(funds)}")
    print()

    for result in results:
        if result["status"] == "success":
            print(
                f"{result['isin']}: "
                f"SUCCESS "
                f"(NAV {result['nav_action']})"
            )
        else:
            print(
                f"{result['isin']}: "
                f"FAILED — {result['error']}"
            )


if __name__ == "__main__":
    main()
