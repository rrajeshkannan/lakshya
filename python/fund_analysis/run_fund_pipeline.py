from pathlib import Path

from fund_analysis.analyze_fund import analyze_fund
from fund_analysis.nav_evidence import NavEvidenceStore
from fund_analysis.fingerprint_evidence import (
    FingerprintEvidenceAlreadyExistsError,
)
from lakshya_core.nav_history import normalize_nav_history


def run_fund_pipeline(
    *,
    funds,
    nav_source,
    data_root: Path,
    generated_at: str,
    progress=None,
):
    """
    Acquire NAV evidence and run Fund-stage analysis for every Fund.

    This function is orchestration only. NAV acquisition, evidence
    persistence, and behavioural analysis remain delegated to their
    respective components.
    """

    data_root = Path(data_root)

    total = len(funds)

    results = []

    for index, fund in enumerate(funds, start=1):

        if progress:
            progress(
                f"[{index:02d}/{total}] "
                f"{fund.name} — fetching NAV..."
            )

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
            scheme_code = nav_source.resolve_scheme_code(
                fund.isin
            )

            raw_nav = nav_source.fetch_nav_history(
                scheme_code
            )

            nav = normalize_nav_history(raw_nav)

            nav_evidence_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            store = NavEvidenceStore(
                nav_evidence_path
            )

            if nav_evidence_path.exists():
                latest_date = store.latest_date()

                new_nav = nav[
                    nav["date"] > latest_date
                ]

                if not new_nav.empty:
                    store.update(
                        nav=new_nav,
                        retrieved_at=generated_at,
                    )

                    nav_action = "updated"
                else:
                    nav_action = "unchanged"

            else:
                store.create(
                    isin=fund.isin,
                    scheme_code=scheme_code,
                    source="mfapi.in",
                    nav=nav,
                    retrieved_at=generated_at,
                )

                nav_action = "created"

            if progress:
                progress(
                    f"[{index:02d}/{total}] "
                    f"{fund.name} — NAV {nav_action}"
                )

            try:
                analyze_fund(
                    fund=fund,
                    nav_evidence_path=nav_evidence_path,
                    fingerprint_evidence_path=fingerprint_evidence_path,
                    generated_at=generated_at,
                )

                fingerprint_action = "created"

            except FingerprintEvidenceAlreadyExistsError:
                fingerprint_action = "already_exists"

            if progress:
                progress(
                    f"[{index:02d}/{total}] "
                    f"{fund.name} — "
                    f"fingerprint {fingerprint_action}"
                )

            results.append(
                {
                    "isin": fund.isin,
                    "status": "success",
                    "nav_action": nav_action,
                    "fingerprint_action": fingerprint_action,
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
