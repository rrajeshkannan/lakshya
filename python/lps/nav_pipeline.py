"""Acquire, normalize, and persist historical NAV evidence for LPS."""

from __future__ import annotations

from pathlib import Path

from lps.nav_evidence import NavEvidenceStore
from lps.nav_history import normalize_nav_history


def run_nav_pipeline(
    *,
    isins,
    nav_source,
    data_root: Path,
    retrieved_at: str,
    progress=None,
):
    """Acquire/update persisted NAV evidence for each LPS fund identity."""
    data_root = Path(data_root)
    isins = list(isins)
    total = len(isins)
    results = []

    for index, isin in enumerate(isins, start=1):
        if progress:
            progress(f"[{index:02d}/{total:02d}] {isin} — fetching NAV...")

        nav_evidence_path = data_root / "lps" / "nav" / f"{isin}.json"

        try:
            scheme_code = nav_source.resolve_scheme_code(isin)
            raw_nav = nav_source.fetch_nav_history(scheme_code)
            nav = normalize_nav_history(raw_nav)

            nav_evidence_path.parent.mkdir(parents=True, exist_ok=True)
            store = NavEvidenceStore(nav_evidence_path)

            if nav_evidence_path.exists():
                latest_date = store.latest_date()
                new_nav = nav[nav["date"] > latest_date]

                if not new_nav.empty:
                    store.update(nav=new_nav, retrieved_at=retrieved_at)
                    nav_action = "updated"
                else:
                    nav_action = "unchanged"
            else:
                store.create(
                    isin=isin,
                    scheme_code=scheme_code,
                    source="mfapi.in",
                    nav=nav,
                    retrieved_at=retrieved_at,
                )
                nav_action = "created"

            if progress:
                progress(f"[{index:02d}/{total:02d}] {isin} — NAV {nav_action}")

            results.append(
                {
                    "isin": isin,
                    "status": "success",
                    "nav_action": nav_action,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "isin": isin,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return results


__all__ = ["run_nav_pipeline"]
