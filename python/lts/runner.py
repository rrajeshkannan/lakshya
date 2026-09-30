"""Run the LTS cascade from canonical LPS inputs."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from fund_analysis.funds_in_scope import load_fund_scope_rows
from lps.position_persistence import read_positions
from lps.transaction_persistence import read_transactions

from .allocation_cascade import (
    AllocationCascade,
    build_allocation_cascade,
    export_cascade_review_csv,
    export_transition_slices_csv,
)
from .current_input import CurrentInput, classify_current_positions
from .formation_intent import build_formation_intent
from .fund_metadata import FundClassification, classify_scope_row
from .models import TargetFormation
from .position_bridge import LtsPosition, bridge_positions

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_PURPOSES_PATH = DATA_DIR / "purpose" / "purposes.csv"
DEFAULT_POSITIONS_PATH = DATA_DIR / "lps" / "positions.csv"
DEFAULT_TRANSACTIONS_PATH = DATA_DIR / "lps" / "transactions.csv"
DEFAULT_PURPOSE_SUMMARIES_PATH = DATA_DIR / "lfs" / "purpose_summaries.csv"
DEFAULT_FUND_SCOPE_PATH = DATA_DIR / "lps" / "funds_in_scope.csv"
DEFAULT_LTS_ROOT = DATA_DIR / "lts"
DEFAULT_TRANSITION_MANIFEST_PATH = DATA_DIR / "lps" / "transition_manifest.json"

ACTIVE_ARTIFACTS = (
    "materialized_transition_slices.csv",
    "cascade_review.csv",
    "execution_playbook.csv",
    "tax_preflight_report.txt",
    "manifest.json",
)


@dataclass(frozen=True)
class LtsRunResult:
    positions: tuple[LtsPosition, ...]
    current_input: CurrentInput
    formation: TargetFormation
    cascade: AllocationCascade
    as_of: date | None
    lot_locks_applied: bool


def _scope_classifications(
    fund_scope_path: Path,
    active_isins: set[str],
    *,
    positions_path: Path,
) -> dict[str, FundClassification] | None:
    """Return classifications when the scope file covers this book.

    A fixture book pointed at the production scope is left unlocked. A
    production book with a missing ISIN is an error.
    """
    if not fund_scope_path.is_file():
        if positions_path == DEFAULT_POSITIONS_PATH:
            raise ValueError(f"Fund scope file is missing: {fund_scope_path}")
        return None
    scope_rows = load_fund_scope_rows(fund_scope_path)
    scope_by_isin = {row["isin"]: row for row in scope_rows}
    missing = sorted(active_isins - set(scope_by_isin))
    if missing:
        if positions_path == DEFAULT_POSITIONS_PATH:
            raise ValueError(
                "Fund scope is missing active position ISINs: " + ", ".join(missing)
            )
        return None
    return {
        isin: classify_scope_row(scope_by_isin[isin])
        for isin in sorted(active_isins)
    }


def run_lts_transition(
    *,
    purposes_path: Path = DEFAULT_PURPOSES_PATH,
    positions_path: Path = DEFAULT_POSITIONS_PATH,
    transactions_path: Path = DEFAULT_TRANSACTIONS_PATH,
    purpose_summaries_path: Path = DEFAULT_PURPOSE_SUMMARIES_PATH,
    fund_scope_path: Path = DEFAULT_FUND_SCOPE_PATH,
    as_of: date | None = None,
) -> LtsRunResult:
    persisted_positions = read_positions(positions_path)
    current_input = classify_current_positions(persisted_positions)
    current_positions = bridge_positions(list(current_input.active_positions))
    active_isins = {position.id.isin for position in current_input.active_positions}
    classifications = _scope_classifications(
        fund_scope_path,
        active_isins,
        positions_path=positions_path,
    )
    lot_locks_applied = classifications is not None and transactions_path.is_file()
    valuation_date = as_of
    if lot_locks_applied and valuation_date is None:
        valuation_date = date.fromisoformat(_infer_as_of(purpose_summaries_path))
    formation = build_formation_intent(
        purposes_path=purposes_path,
        positions_path=positions_path,
        purpose_summaries_path=purpose_summaries_path,
        current_positions=current_input.active_positions,
    )
    cascade = build_allocation_cascade(
        current_positions,
        formation,
        transactions=read_transactions(transactions_path) if lot_locks_applied else None,
        classifications=classifications if lot_locks_applied else None,
        as_of=valuation_date if lot_locks_applied else None,
        existing_positions=persisted_positions,
    )
    return LtsRunResult(
        positions=tuple(current_positions),
        current_input=current_input,
        formation=formation,
        cascade=cascade,
        as_of=valuation_date,
        lot_locks_applied=lot_locks_applied,
    )


def _infer_as_of(purpose_summaries_path: Path) -> str:
    with purpose_summaries_path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        values = {str(row.get("as_of", "")).strip() for row in rows}
    values.discard("")
    if len(values) != 1:
        raise ValueError(
            f"Expected exactly one non-blank as_of value in {purpose_summaries_path}; found {sorted(values)}."
        )
    return values.pop()


def _write_text(destination: Path, text: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(destination)


def _portfolio_value(result: LtsRunResult) -> Decimal:
    return sum((item.market_value for item in result.cascade.slices), Decimal("0"))


def _write_manifest(
    result: LtsRunResult,
    destination: Path,
    *,
    as_of: str,
    artifacts: dict[str, str],
) -> None:
    locked = [item for item in result.cascade.slices if item.locked]
    payload = {
        "contract": "LTS_TRANSITION",
        "contract_version": 7,
        "as_of": as_of,
        "position_count": len(result.positions),
        "slice_count": len(result.cascade.slices),
        "review_count": len(result.cascade.review),
        "locked_slice_count": len(locked),
        "lot_locks_applied": result.lot_locks_applied,
        "portfolio_market_value": format(_portfolio_value(result), "f"),
        "artifacts": artifacts,
    }
    _write_text(destination, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def persist_lts_artifacts(
    result: LtsRunResult,
    *,
    as_of: str,
    lts_root: Path = DEFAULT_LTS_ROOT,
    transactions_path: Path = DEFAULT_TRANSACTIONS_PATH,
    fund_scope_path: Path = DEFAULT_FUND_SCOPE_PATH,
) -> dict[str, Path]:
    """Write the cascade book, its playbook, the tax sheet, and the manifest."""
    if not as_of.strip():
        raise ValueError("as_of must be non-blank.")
    slices_path = lts_root / "materialized_transition_slices.csv"
    review_path = lts_root / "cascade_review.csv"
    playbook_path = lts_root / "execution_playbook.csv"
    tax_path = lts_root / "tax_preflight_report.txt"
    manifest_path = lts_root / "manifest.json"

    _write_text(slices_path, export_transition_slices_csv(result.cascade.slices))
    _write_text(review_path, export_cascade_review_csv(result.cascade.review))

    from .execution_playbook import write_execution_playbook

    write_execution_playbook(slices_path, playbook_path)
    artifacts = {
        "materialized_transition_slices": slices_path.name,
        "cascade_review": review_path.name,
        "execution_playbook": playbook_path.name,
    }
    written = {
        "materialized_transition_slices": slices_path,
        "cascade_review": review_path,
        "execution_playbook": playbook_path,
    }
    if result.lot_locks_applied:
        from .tax_preflight import write_tax_preflight_report

        write_tax_preflight_report(
            slices_path=slices_path,
            transactions_path=transactions_path,
            fund_scope_path=fund_scope_path,
            as_of=date.fromisoformat(as_of),
            destination=tax_path,
        )
        artifacts["tax_preflight_report"] = tax_path.name
        written["tax_preflight_report"] = tax_path
    artifacts["manifest"] = manifest_path.name
    _write_manifest(result, manifest_path, as_of=as_of, artifacts=artifacts)
    written["manifest"] = manifest_path
    return written


def _print_runner_and_lock_audit() -> None:
    """Print the runner and tax-lock inspection. This does not validate."""
    print(
        "\n".join([
            "LTS runner topology",
            "  Executable entry point: python -m lts.runner (python/lts/runner.py).",
            "  python/lts has no __main__.py.",
            "",
            "STCG and ELSS tax-lock inspection",
            "  The cascade is the only allocation path:",
            "  - Equity STCG: a lot is locked when (as_of - acquired).days <= 365,",
            "    including the 365th day. ELSS: a lot is locked while as_of is",
            "    strictly before the third anniversary. The anniversary day itself",
            "    is unlocked. Debt and other asset classes are not locked.",
            "  - Locked units are split onto portions with locked=True.",
            "  - Those portions are drafted as disposition=RETAIN. REDEEM drafts",
            "    are built only from unlocked, non-chosen portions and carry locked=False.",
            "  - The cascade rejects a locked slice that is not RETAIN.",
            "  Calling the cascade without transactions marks the whole holding",
            "  unlocked. This runner supplies transactions when the fund scope",
            "  covers the book.",
            "",
        ])
    )


def write_transition_manifest(
    *,
    lts_manifest_path: Path,
    playbook_path: Path,
    destination: Path,
) -> Path:
    """Write the LPS transition manifest from the LTS manifest and playbook.

    ``as_of`` and ``contract_version`` are copied from the LTS manifest file.
    Every playbook row becomes a ``PENDING`` order.
    """
    payload = json.loads(lts_manifest_path.read_text(encoding="utf-8"))
    as_of = payload.get("as_of")
    if not isinstance(as_of, str) or not as_of.strip():
        raise ValueError(f"LTS manifest has no as_of date: {lts_manifest_path}")
    date.fromisoformat(as_of)
    contract_version = payload.get("contract_version")
    if isinstance(contract_version, bool) or not isinstance(contract_version, int):
        raise ValueError(
            f"LTS manifest contract_version must be an integer: {lts_manifest_path}"
        )

    orders: list[dict[str, object]] = []
    with playbook_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = (
            "source_investor",
            "source_folio",
            "source_isin",
            "units_to_redeem",
            "target_investor",
            "target_folio",
            "target_isin",
            "target_slice",
            "purpose",
        )
        missing = [field for field in required if field not in (reader.fieldnames or ())]
        if missing:
            raise ValueError(
                f"{playbook_path} is missing columns: {', '.join(missing)}"
            )
        for index, row in enumerate(reader, start=1):
            orders.append({
                "order_id": f"ORD-{index:03d}",
                "source_investor": row["source_investor"],
                "source_folio": row["source_folio"],
                "source_isin": row["source_isin"],
                "units_to_redeem": row["units_to_redeem"],
                "target_investor": row["target_investor"],
                "target_folio": row["target_folio"],
                "target_isin": row["target_isin"],
                "target_slice": row["target_slice"],
                "purpose": row["purpose"],
                "status": "PENDING",
                "settled_at": None,
            })

    document = {
        "as_of": as_of,
        "manifest_id": f"MAN-{as_of}-01",
        "contract_version": contract_version,
        "orders": orders,
    }
    _write_text(destination, json.dumps(document, indent=2) + "\n")
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", help="Optional valuation boundary; normally inferred from LFS summaries.")
    return parser


def main() -> None:
    args = _parser().parse_args()
    _print_runner_and_lock_audit()
    inferred_as_of = _infer_as_of(DEFAULT_PURPOSE_SUMMARIES_PATH)
    if args.as_of is not None and args.as_of != inferred_as_of:
        raise ValueError(
            f"Explicit --as-of {args.as_of} disagrees with the LFS summary boundary {inferred_as_of}."
        )
    result = run_lts_transition(as_of=date.fromisoformat(inferred_as_of))
    written = persist_lts_artifacts(result, as_of=inferred_as_of)
    print(f"Lot locks applied: {result.lot_locks_applied}")
    print(f"Positions: {len(result.positions)}")
    print(f"Slices: {len(result.cascade.slices)}")
    print(f"Cascade review rows: {len(result.cascade.review)}")
    for name in (
        "materialized_transition_slices",
        "cascade_review",
        "execution_playbook",
        "tax_preflight_report",
        "manifest",
    ):
        path = written.get(name)
        if path is not None:
            print(f"{name}: {path.relative_to(PROJECT_ROOT)}")
    from .execution_playbook import format_redemption_summary, read_transition_slice_rows, build_execution_playbook

    playbook_rows = build_execution_playbook(
        read_transition_slice_rows(written["materialized_transition_slices"])
    )
    print(format_redemption_summary(playbook_rows))
    tax_path = written.get("tax_preflight_report")
    if tax_path is not None:
        print(tax_path.read_text(encoding="utf-8"), end="")
        print(
            "Cost basis is FIFO acquisition amount on lots the lock rules leave "
            "sellable. Section 112A grandfathering is not applied."
        )
    transition_manifest = write_transition_manifest(
        lts_manifest_path=written["manifest"],
        playbook_path=written["execution_playbook"],
        destination=DEFAULT_TRANSITION_MANIFEST_PATH,
    )
    print(f"transition_manifest: {transition_manifest.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()


__all__ = [
    "ACTIVE_ARTIFACTS",
    "DEFAULT_LTS_ROOT",
    "DEFAULT_POSITIONS_PATH",
    "LtsRunResult",
    "DEFAULT_TRANSITION_MANIFEST_PATH",
    "persist_lts_artifacts",
    "run_lts_transition",
    "write_transition_manifest",
]
