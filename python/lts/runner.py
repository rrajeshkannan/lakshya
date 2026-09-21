"""Run the LTS transition slice from the repository's canonical inputs."""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path

from lps.position_persistence import read_positions

from .current_input import CurrentInput, classify_current_positions
from .formation_intent import build_formation_intent
from .models import TargetFormation
from .position_bridge import LtsPosition, bridge_positions
from .purpose_transition import PurposeTransitionPlan, build_purpose_transition_plan
from .purpose_transition_report import PurposeTransitionReport, build_purpose_transition_report
from .transition_audit import audit_transition_mapping
from .transition_export import write_transition_mapping_csv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PURPOSES_PATH = PROJECT_ROOT / "data" / "purpose" / "purposes.csv"
DEFAULT_POSITIONS_PATH = PROJECT_ROOT / "data" / "lps" / "positions.csv"
DEFAULT_PURPOSE_SUMMARIES_PATH = PROJECT_ROOT / "data" / "lfs" / "purpose_summaries.csv"
DEFAULT_LTS_ROOT = PROJECT_ROOT / "data" / "lts"


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
    purposes_path: Path = DEFAULT_PURPOSES_PATH,
    positions_path: Path = DEFAULT_POSITIONS_PATH,
    purpose_summaries_path: Path = DEFAULT_PURPOSE_SUMMARIES_PATH,
) -> LtsRunResult:
    """Run the complete in-memory LTS transition slice.

    The runner consumes the repository's existing LFS/FINAL evidence. It does
    not rerun FINAL, calculate tax, execute transactions, or mutate persisted
    portfolio state.
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


def _write_manifest(result: LtsRunResult, destination: Path, *, as_of: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract": "LTS_TRANSITION",
        "contract_version": 2,
        "as_of": as_of,
        "position_count": len(result.positions),
        "purpose_report_count": len(result.reports),
        "portfolio_current_amount": format(result.plan.portfolio_current_amount, "f"),
        "portfolio_target_amount": format(result.plan.portfolio_target_amount, "f"),
        "mapping_count": len(result.plan.mappings),
        "is_balanced": result.plan.is_balanced,
        "all_purpose_reports_balanced": all(report.is_balanced for report in result.reports),
    }
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)


def _infer_as_of(purpose_summaries_path: Path) -> str:
    """Read the single analytical boundary recorded by the LFS summaries."""
    with purpose_summaries_path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        values = {str(row.get("as_of", "")).strip() for row in rows}

    values.discard("")
    if len(values) != 1:
        raise ValueError(
            "Expected exactly one non-blank as_of value in "
            f"{purpose_summaries_path}; found {sorted(values)}."
        )
    return values.pop()


def _write_atomic_mapping(result: LtsRunResult, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    write_transition_mapping_csv(result.plan, temporary)
    temporary.replace(destination)


def _write_atomic_reports(result: LtsRunResult, destination: Path) -> None:
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
    """Overwrite the latest canonical LTS snapshot in ``data/lts``.

    The files are written through temporary siblings before replacement so a
    failed write does not truncate an existing artifact in place.
    """
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
        help="Optional override; normally inferred from data/lfs/purpose_summaries.csv.",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    inferred_as_of = _infer_as_of(DEFAULT_PURPOSE_SUMMARIES_PATH)
    if args.as_of is not None and args.as_of != inferred_as_of:
        raise ValueError(
            f"Explicit --as-of {args.as_of} disagrees with the LFS summary boundary "
            f"{inferred_as_of}."
        )

    result = run_lts_transition()
    mapping_path, report_path, manifest_path = persist_lts_artifacts(
        result,
        as_of=inferred_as_of,
    )
    print(f"LTS transition balanced: {result.plan.is_balanced}")
    print(f"Purpose reports: {len(result.reports)}")
    print(f"Transition mapping: {mapping_path.relative_to(PROJECT_ROOT)}")
    print(f"Purpose reports CSV: {report_path.relative_to(PROJECT_ROOT)}")
    print(f"LTS manifest: {manifest_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()


__all__ = [
    "DEFAULT_LTS_ROOT",
    "DEFAULT_POSITIONS_PATH",
    "DEFAULT_PURPOSES_PATH",
    "DEFAULT_PURPOSE_SUMMARIES_PATH",
    "LtsRunResult",
    "persist_lts_artifacts",
    "run_lts_transition",
]
