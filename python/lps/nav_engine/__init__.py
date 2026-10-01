"""Fetch and cache NAV history for an observation date.

The engine talks to mfapi.in only when a fund's local history does not
already cover the requested date. Valuation stays in ``lps.valuator``.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from lps.nav_evidence import NavEvidenceStore
from lps.nav_pipeline import run_nav_pipeline
from lps.nav_source import MfapiNavSource, mfapi_http_transport


def ensure_nav_coverage(
    *,
    as_of: date,
    isins: list[str],
    data_root: Path,
    progress=print,
) -> list[dict]:
    """Ensure each ISIN has a stored NAV observation on or before ``as_of``.

    A fund whose newest stored print is already on or after ``as_of`` is left
    untouched. Every other fund is refreshed from mfapi.in.
    """
    data_root = Path(data_root)
    needed: list[str] = []
    covered: list[str] = []
    for isin in list(dict.fromkeys(isins)):
        store = NavEvidenceStore(data_root / "nav" / f"{isin}.json")
        if store.path.exists() and store.latest_date().date() >= as_of:
            covered.append(isin)
        else:
            needed.append(isin)

    if progress and covered:
        progress(
            f"NAV coverage already reaches {as_of.isoformat()} "
            f"for {len(covered)} fund(s)."
        )
    if not needed:
        return [{"isin": isin, "status": "success", "nav_action": "covered"} for isin in covered]

    if progress:
        progress(f"Fetching NAV from mfapi.in for {len(needed)} fund(s) through {as_of.isoformat()}.")
    source = MfapiNavSource(transport=mfapi_http_transport)
    source.scheme_catalog = source.fetch_scheme_catalog()
    results = run_nav_pipeline(
        isins=needed,
        nav_source=source,
        data_root=data_root,
        retrieved_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        progress=progress,
    )
    failed = [item for item in results if item["status"] == "failed"]
    if failed:
        raise RuntimeError(
            "NAV acquisition failed: "
            + "; ".join(f"{item['isin']}: {item['error']}" for item in failed)
        )
    return results


__all__ = ["ensure_nav_coverage"]
