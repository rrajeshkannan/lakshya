"""Run the LTS transition slice from canonical LPS inputs."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lps.nav_evidence import NavEvidenceStore
from lps.position_persistence import read_positions
from lps.transaction_persistence import read_transactions

from .availability_report import build_holding_availability_report
from .constraint_factory import holding_constraint_for_fund
from .current_input import CurrentInput, classify_current_positions
from .evidence import TransitionEvidence, build_transition_evidence
from .formation_intent import build_formation_intent
from .fund_metadata import classify_fund
from .models import TargetFormation
from .position_bridge import LtsPosition, bridge_positions
from .purpose_transition import PurposeTransitionPlan, build_purpose_transition_plan
from .purpose_transition_report import PurposeTransitionReport, build_purpose_transition_report
from .transition_audit import audit_transition_mapping
from .transition_export import write_transition_mapping_csv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_PURPOSES_PATH = DATA_DIR / "purpose" / "purposes.csv"
DEFAULT_POSITIONS_PATH = DATA_DIR / "lps" / "positions.csv"
DEFAULT_TRANSACTIONS_PATH = DATA_DIR / "lps" / "transactions.csv"
DEFAULT_NAV_ROOT = DATA_DIR / "lps" / "nav"
DEFAULT_PURPOSE_SUMMARIES_PATH = DATA_DIR / "lfs" / "purpose_summaries.csv"
DEFAULT_LTS_ROOT = DATA_DIR / "lts"


@dataclass(frozen=True)
class LtsRunResult:
    positions: tuple[LtsPosition, ...]
    current_input: CurrentInput
    evidence: TransitionEvidence
    availability: tuple
    formation: TargetFormation
    plan: PurposeTransitionPlan
    reports: tuple[PurposeTransitionReport, ...]


def _nav_stores(isins: set[str], nav_root: Path) -> dict[str, NavEvidenceStore]:
    return {isin: NavEvidenceStore(nav_root / f"{isin}.json") for isin in sorted(isins)}


def _evidence_inputs_available(
    *,
    active_isins: set[str],
    transactions_path: Path,
    nav_root: Path,
) -> bool:
    """Return whether the optional transaction/NAV evidence is complete."""
    return transactions_path.is_file() and all(
        (nav_root / f"{isin}.json").is_file() for isin in active_isins
    )


def _locked_position_ids(availability: tuple) -> set:
    return {
        report.holding_id
        for report in availability
        if report.locked_lots
    }


def run_lts_transition(
    *,
    purposes_path: Path = DEFAULT_PURPOSES_PATH,
    positions_path: Path = DEFAULT_POSITIONS_PATH,
    transactions_path: Path = DEFAULT_TRANSACTIONS_PATH,
    nav_root: Path = DEFAULT_NAV_ROOT,
    purpose_summaries_path: Path = DEFAULT_PURPOSE_SUMMARIES_PATH,
    as_of: date | None = None,
    transaction_through_date: date | None = None,
) -> LtsRunResult:
    persisted_positions = read_positions(positions_path)
    current_input = classify_current_positions(persisted_positions)
    current_positions = bridge_positions(list(current_input.active_positions))

    active_isins = {
        position.id.isin for position in current_input.active_positions
    }
    evidence_available = _evidence_inputs_available(
        active_isins=active_isins,
        transactions_path=transactions_path,
        nav_root=nav_root,
    )

    if evidence_available:
        valuation_date = as_of or date.fromisoformat(
            _infer_as_of(purpose_summaries_path)
        )
        transactions = read_transactions(transactions_path)
        stores = _nav_stores(active_isins, nav_root)
        evidence = build_transition_evidence(
            list(current_input.active_positions),
            transactions,
            stores,
            valuation_date,
            transaction_through_date=transaction_through_date,
        )
        classifications = {
            metadata.isin: classify_fund(metadata)
            for metadata in evidence.fund_metadata
        }
        constraints = {
            isin: holding_constraint_for_fund(classification)
            for isin, classification in classifications.items()
        }
        availability_as_of = transaction_through_date or valuation_date
        availability = build_holding_availability_report(
            evidence,
            availability_as_of,
            constraints,
        )
    else:
        evidence = TransitionEvidence(
            positions=(),
            transactions=(),
            fund_metadata=(),
        )
        availability = ()

    locked_ids = _locked_position_ids(availability)

    formation = build_formation_intent(
        purposes_path=purposes_path,
        positions_path=positions_path,
        purpose_summaries_path=purpose_summaries_path,
        current_positions=current_input.active_positions,
    )
    plan = build_purpose_transition_plan(
        current_positions,
        formation,
        locked_position_ids={
            position_id
            for position_id in locked_ids
            for position in current_positions
            if position.id.investor == position_id.investor
            and position.id.folio == position_id.folio
            and position.id.isin == position_id.isin
        },
    )
    audit_transition_mapping(current_positions, formation, plan)
    reports = build_purpose_transition_report(current_positions, formation, plan)
    return LtsRunResult(
        positions=tuple(current_positions),
        current_input=current_input,
        evidence=evidence,
        availability=availability,
        formation=formation,
        plan=plan,
        reports=tuple(reports),
    )


def _write_reports_csv(reports, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([
            "purpose", "current_amount", "target_amount", "retained_amount",
            "redemption_amount", "locked_redemption_amount",
            "investment_by_destination", "is_balanced",
        ])
        for report in reports:
            writer.writerow([
                report.purpose,
                format(report.current_amount, "f"),
                format(report.target_amount, "f"),
                format(report.retained_amount, "f"),
                format(report.redemption_amount, "f"),
                format(report.locked_redemption_amount, "f"),
                ";".join(
                    f"{isin}={format(amount, 'f')}"
                    for isin, amount in report.investment_by_destination
                ),
                str(report.is_balanced).lower(),
            ])


def _write_manifest(result: LtsRunResult, destination: Path, *, as_of: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract": "LTS_TRANSITION",
        "contract_version": 3,
        "as_of": as_of,
        "position_count": len(result.positions),
        "purpose_report_count": len(result.reports),
        "availability_count": len(result.availability),
        "locked_position_count": len(_locked_position_ids(result.availability)),
        "portfolio_current_amount": format(result.plan.portfolio_current_amount, "f"),
        "portfolio_target_amount": format(result.plan.portfolio_target_amount, "f"),
        "mapping_count": len(result.plan.mappings),
        "is_balanced": result.plan.is_balanced,
        "all_purpose_reports_balanced": all(
            report.is_balanced for report in result.reports
        ),
    }
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def _infer_as_of(purpose_summaries_path: Path) -> str:
    with purpose_summaries_path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        values = {str(row.get("as_of", "")).strip() for row in rows}
    values.discard("")
    if len(values) != 1:
        raise ValueError(
            f"Expected exactly one non-blank as_of value in "
            f"{purpose_summaries_path}; found {sorted(values)}."
        )
    return values.pop()


def _write_atomic_mapping(result, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    write_transition_mapping_csv(result.plan, temporary)
    temporary.replace(destination)


def _write_atomic_reports(result, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    _write_reports_csv(result.reports, temporary)
    temporary.replace(destination)


def persist_lts_artifacts(
    result: LtsRunResult,
    *,
    as_of: str,
    lts_root: Path = DEFAULT_LTS_ROOT,
) -> tuple[Path, Path, Path]:
    if not as_of.strip():
        raise ValueError("as_of must be non-blank.")
    mapping_path = lts_root / "transition_mappings.csv"
    report_path = lts_root / "purpose_reports.csv"
    manifest_path = lts_root / "manifest.json"
    _write_atomic_mapping(result, mapping_path)
    _write_atomic_reports(result, report_path)
    _write_manifest(result, manifest_path, as_of=as_of)
    return mapping_path, report_path, manifest_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        help="Optional valuation boundary; normally inferred from LFS summaries.",
    )
    parser.add_argument(
        "--transaction-through-date",
        help=(
            "Optional historical transaction boundary (YYYY-MM-DD). "
            "Transactions after this date are excluded from ELSS lock-in analysis."
        ),
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    inferred_as_of = _infer_as_of(DEFAULT_PURPOSE_SUMMARIES_PATH)
    if args.as_of is not None and args.as_of != inferred_as_of:
        raise ValueError(
            f"Explicit --as-of {args.as_of} disagrees with the LFS summary "
            f"boundary {inferred_as_of}."
        )
    transaction_through_date = (
        date.fromisoformat(args.transaction_through_date)
        if args.transaction_through_date is not None
        else None
    )
    result = run_lts_transition(
        as_of=date.fromisoformat(inferred_as_of),
        transaction_through_date=transaction_through_date,
    )
    mapping_path, report_path, manifest_path = persist_lts_artifacts(
        result,
        as_of=inferred_as_of,
    )
    print(f"LTS transition balanced: {result.plan.is_balanced}")
    print(f"Purpose reports: {len(result.reports)}")
    print(f"Availability reports: {len(result.availability)}")
    for availability in result.availability:
        print(
            f"Availability {availability.holding_id}: "
            f"locked_units={availability.locked_units} "
            f"unlocked_units={availability.unlocked_units} "
            f"as_of={availability.as_of}"
        )
    print(f"Transition mapping: {mapping_path.relative_to(PROJECT_ROOT)}")
    print(f"Purpose reports CSV: {report_path.relative_to(PROJECT_ROOT)}")
    print(f"LTS manifest: {manifest_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()


__all__ = [
    "DEFAULT_LTS_ROOT",
    "DEFAULT_POSITIONS_PATH",
    "LtsRunResult",
    "persist_lts_artifacts",
    "run_lts_transition",
]
