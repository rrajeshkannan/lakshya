"""Run the LPS historical NAV acquisition pipeline for the family fund scope."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from lps.nav_pipeline import run_nav_pipeline
from lps.nav_source import MfapiNavSource, mfapi_http_transport

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCOPE_PATH = PROJECT_ROOT / "data" / "fund" / "funds_in_scope.csv"


def load_in_scope_isins(path: Path = SCOPE_PATH) -> list[str]:
    """Load the reviewer-maintained ISIN scope without interpreting fund attributes."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        isins = [row["isin"].strip() for row in rows if row.get("isin", "").strip()]

    if not isins:
        raise ValueError(f"No ISINs found in scope file: {path}")

    return list(dict.fromkeys(isins))


def main() -> None:
    isins = load_in_scope_isins()

    source = MfapiNavSource(transport=mfapi_http_transport)
    source.scheme_catalog = source.fetch_scheme_catalog()

    retrieved_at = datetime.now().astimezone().isoformat(timespec="seconds")
    results = run_nav_pipeline(
        isins=isins,
        nav_source=source,
        data_root=PROJECT_ROOT / "data",
        retrieved_at=retrieved_at,
        progress=print,
    )

    print(f"Funds in NAV scope: {len(isins)}")
    print()
    for result in results:
        if result["status"] == "success":
            print(f"{result['isin']}: SUCCESS (NAV {result['nav_action']})")
        else:
            print(f"{result['isin']}: FAILED — {result['error']}")

    failed = [result for result in results if result["status"] == "failed"]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
