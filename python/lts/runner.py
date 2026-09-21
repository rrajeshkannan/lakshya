"""Thin LTS orchestration boundary for a known LFS evidence set."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from lps.position_persistence import read_positions

from .formation_intent import build_formation_intent
from .position_bridge import LtsPosition, bridge_positions
from .purpose_transition import PurposeTransitionPlan, build_purpose_transition_plan
from .purpose_transition_report import PurposeTransitionReport, build_purpose_transition_report
from .transition_audit import audit_transition_mapping
from .transition_export import persist_transition_mapping_csv


@dataclass(frozen=True)
class LtsRunResult:
    """Validated analytical result produced by one LTS runner invocation."""

    positions: tuple[LtsPosition, ...]
    formation: object
    plan: PurposeTransitionPlan
    reports: tuple[PurposeTransitionReport, ...]


def run_lts_transition(
    *,
    purposes_path: Path,
    positions_path: Path,
    purpose_summaries_path: Path,
) -> LtsRunResult:
    """Run the smallest complete LTS transition slice.

    The runner consumes existing LFS/FINAL evidence. It does not rerun FINAL,
    calculate tax, execute transactions, or mutate persisted portfolio state.
    """
    current_positions = bridge_positions(read_positions(positions_path))
    formation = build_formation_intent(
        purposes_path=purposes_path,
        positions_path=positions_path,
        purpose_summaries_path=purpose_summaries_path,
    )
    plan = build_purpose_transition_plan(current_positions, formation)
    audit_transition_mapping(current_positions, formation, plan)
    reports = build_purpose_transition_report(current_positions, formation, plan)
    return LtsRunResult(
        positions=tuple(current_positions),
        formation=formation,
        plan=plan,
        reports=reports,
    )


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
    artifact = persist_transition_mapping_csv(
        result.plan,
        as_of=args.as_of,
        run_id=args.run_id,
        root=args.temporal_root,
    )
    print(f"LTS transition balanced: {result.plan.is_balanced}")
    print(f"Purpose reports: {len(result.reports)}")
    print(f"Transition mapping: {artifact}")


if __name__ == "__main__":
    main()


__all__ = ["LtsRunResult", "run_lts_transition"]
