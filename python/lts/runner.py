"""Complete LTS orchestration boundary for a known LFS evidence set."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from lps.position_persistence import read_positions

from .current_input import CurrentInput, classify_current_positions
from .formation_intent import build_formation_intent
from .models import TargetFormation
from .position_bridge import LtsPosition, bridge_positions
from .purpose_transition import PurposeTransitionPlan, build_purpose_transition_plan
from .purpose_transition_report import PurposeTransitionReport, build_purpose_transition_report
from .transition_audit import audit_transition_mapping
from .transition_export import persist_transition_mapping_csv


@dataclass(frozen=True)
class LtsRunResult:
    """Validated analytical result produced by one LTS runner invocation."""

    positions: tuple[LtsPosition, ...]
    current_input: CurrentInput
    formation: TargetFormation
    plan: PurposeTransitionPlan
    reports: tuple[PurposeTransitionReport, ...]


def run_lts_transition(
    *,
    purposes_path: Path,
    positions_path: Path,
    purpose_summaries_path: Path,
) -> LtsRunResult:
    """Run the complete in-memory LTS transition slice.

    The runner consumes existing LFS/FINAL evidence. It does not rerun FINAL,
    calculate tax, execute transactions, or mutate persisted portfolio state.
    """
    persisted_positions = read_positions(positions_path)
    current_input = classify_current_positions(persisted_positions)
    current_positions = bridge_positions(list(current_input.active_positions))

    formation = build_formation_intent(
        purposes_path=purposes_path,
        positions_path=positions_path,
        purpose_summaries_path=purpose_summaries_path,
        current_positions=current_input.active_positions,
    )
    plan = build_purpose_transition_plan(current_positions, formation)
    audit_transition_mapping(current_positions, formation, plan)
    reports = build_purpose_transition_report(current_positions, formation, plan)
    return LtsRunResult(
        positions=tuple(current_positions),
        current_input=current_input,
        formation=formation,
        plan=plan,
        reports=tuple(reports),
    )


def _write_reports_csv(reports: tuple[PurposeTransitionReport, ...], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "purpose",
                "current_amount",
                "target_amount",
                "retained_amount",
                "redemption_amount",
                "locked_redemption_amount",
                "investment_by_destination",
                "is_balanced",
            ]
        )
        for report in reports:
            destinations = ";".join(
                f"{isin}={format(amount, 'f')}"
                for isin, amount in report.investment_by_destination
            )
            writer.writerow(
                [
                    report.purpose,
                    format(report.current_amount, "f"),
                    format(report.target_amount, "f"),
                    format(report.retained_amount, "f"),
                    format(report.redemption_amount, "f"),
                    format(report.locked_redemption_amount, "f"),
                    destinations,
                    str(report.is_balanced).lower(),
                ]
            )


def _write_manifest(result: LtsRunResult, destination: Path, *, as_of: str, run_id: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract": "LTS_TRANSITION",
        "contract_version": 1,
        "as_of": as_of,
        "run_id": run_id,
        "position_count": len(result.positions),
        "purpose_report_count": len(result.reports),
        "portfolio_current_amount": format(result.plan.portfolio_current_amount, "f"),
        "portfolio_target_amount": format(result.plan.portfolio_target_amount, "f"),
        "mapping_count": len(result.plan.mappings),
        "is_balanced": result.plan.is_balanced,
        "all_purpose_reports_balanced": all(report.is_balanced for report in result.reports),
    }
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def persist_lts_run_artifacts(
    result: LtsRunResult,
    *,
    as_of: str,
    run_id: str,
    temporal_root: Path,
) -> tuple[Path, Path, Path]:
    """Persist the mapping, Purpose report, and run manifest for one LTS run."""
    if not as_of.strip() or not run_id.strip():
        raise ValueError("as_of and run_id must be non-blank.")
    if Path(as_of).name != as_of or Path(run_id).name != run_id:
        raise ValueError("as_of and run_id must be single path-safe components.")

    mapping_path = persist_transition_mapping_csv(
        result.plan,
        as_of=as_of,
        run_id=run_id,
        root=temporal_root,
    )
    report_path = temporal_root / "purpose_reports" / f"{as_of}_{run_id}.csv"
    manifest_path = temporal_root / "manifests" / f"{as_of}_{run_id}.json"
    _write_reports_csv(result.reports, report_path)
    _write_manifest(result, manifest_path, as_of=as_of, run_id=run_id)
    return mapping_path, report_path, manifest_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purposes", type=Path, required=True)
    parser.add_argument("--positions", type=Path, required=True)
    parser.add_argument("--purpose-summaries", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--temporal-root", type=Path, default=Path("data/lts"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_lts_transition(
        purposes_path=args.purposes,
        positions_path=args.positions,
        purpose_summaries_path=args.purpose_summaries,
    )
    mapping_path, report_path, manifest_path = persist_lts_run_artifacts(
        result,
        as_of=args.as_of,
        run_id=args.run_id,
        temporal_root=args.temporal_root,
    )
    print(f"LTS transition balanced: {result.plan.is_balanced}")
    print(f"Purpose reports: {len(result.reports)}")
    print(f"Transition mapping: {mapping_path}")
    print(f"Purpose reports CSV: {report_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()


__all__ = ["LtsRunResult", "persist_lts_run_artifacts", "run_lts_transition"]
