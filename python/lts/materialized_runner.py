"""Execute and persist the explicit LTS materialized-slice representation."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .runner import (
    DEFAULT_FUND_SCOPE_PATH,
    DEFAULT_LTS_ROOT,
    DEFAULT_NAV_ROOT,
    DEFAULT_POSITIONS_PATH,
    DEFAULT_PURPOSES_PATH,
    DEFAULT_PURPOSE_SUMMARIES_PATH,
    DEFAULT_TRANSACTIONS_PATH,
    LtsRunResult,
    _infer_as_of,
    persist_lts_artifacts,
    run_lts_transition,
)
from .slice_materialization import MaterializedSlice, materialize_transition_slices


@dataclass(frozen=True)
class MaterializedLtsRunResult:
    """LTS result together with its conservation-balanced virtual slices."""

    result: LtsRunResult
    slices: tuple[MaterializedSlice, ...]


def run_lts_transition_materialized(
    *,
    purposes_path: Path = DEFAULT_PURPOSES_PATH,
    positions_path: Path = DEFAULT_POSITIONS_PATH,
    transactions_path: Path = DEFAULT_TRANSACTIONS_PATH,
    nav_root: Path = DEFAULT_NAV_ROOT,
    purpose_summaries_path: Path = DEFAULT_PURPOSE_SUMMARIES_PATH,
    fund_scope_path: Path = DEFAULT_FUND_SCOPE_PATH,
    as_of: date | None = None,
) -> MaterializedLtsRunResult:
    """Run the LTS pipeline and materialize every source mapping into slices."""
    result = run_lts_transition(
        purposes_path=purposes_path,
        positions_path=positions_path,
        transactions_path=transactions_path,
        nav_root=nav_root,
        purpose_summaries_path=purpose_summaries_path,
        fund_scope_path=fund_scope_path,
        as_of=as_of,
    )
    slices = materialize_transition_slices(list(result.positions), result.plan)
    return MaterializedLtsRunResult(result=result, slices=slices)


def _write_materialized_slices_csv(
    slices: tuple[MaterializedSlice, ...], destination: Path
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "investor",
                "folio",
                "isin",
                "slice",
                "source_investor",
                "source_folio",
                "source_isin",
                "source_slice",
                "destination_isin",
                "purpose",
                "disposition",
                "locked",
                "percentage",
                "units",
                "nav",
                "market_value",
                "source_amount",
                "ownership_source",
            ]
        )
        for item in slices:
            writer.writerow(
                [
                    item.id.investor,
                    item.id.folio,
                    item.id.isin,
                    item.id.slice,
                    item.source_position_id.investor,
                    item.source_position_id.folio,
                    item.source_position_id.isin,
                    item.source_position_id.slice,
                    item.destination_isin,
                    item.purpose,
                    item.disposition.value,
                    str(item.locked).lower(),
                    format(item.percentage, "f"),
                    format(item.units, "f"),
                    "" if item.nav is None else format(item.nav, "f"),
                    format(item.market_value, "f"),
                    format(item.source_amount, "f"),
                    item.ownership_source,
                ]
            )
    temporary.replace(destination)


def persist_materialized_lts_artifacts(
    result: MaterializedLtsRunResult,
    *,
    as_of: str,
    lts_root: Path = DEFAULT_LTS_ROOT,
) -> tuple[Path, Path, Path, Path, Path, Path]:
    """Persist legacy LTS artifacts plus the authoritative materialized slices."""
    mapping_path, report_path, availability_path, summary_path, manifest_path = (
        persist_lts_artifacts(result.result, as_of=as_of, lts_root=lts_root)
    )
    slices_path = lts_root / "materialized_slices.csv"
    _write_materialized_slices_csv(result.slices, slices_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["materialized_slice_count"] = len(result.slices)
    manifest["artifacts"]["materialized_slices"] = slices_path.name
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)
    return (
        mapping_path,
        report_path,
        availability_path,
        summary_path,
        slices_path,
        manifest_path,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", help="Optional valuation boundary; normally inferred from LFS summaries.")
    return parser


def main() -> None:
    args = _parser().parse_args()
    inferred_as_of = _infer_as_of(DEFAULT_PURPOSE_SUMMARIES_PATH)
    if args.as_of is not None and args.as_of != inferred_as_of:
        raise ValueError(
            f"Explicit --as-of {args.as_of} disagrees with the LFS summary boundary {inferred_as_of}."
        )
    materialized = run_lts_transition_materialized(as_of=date.fromisoformat(inferred_as_of))
    paths = persist_materialized_lts_artifacts(materialized, as_of=inferred_as_of)
    print(f"LTS transition balanced: {materialized.result.plan.is_balanced}")
    print(f"Purpose reports: {len(materialized.result.reports)}")
    print(f"Availability reports: {len(materialized.result.availability)}")
    print(f"Materialized slices: {len(materialized.slices)}")
    print(f"Materialized slices CSV: {paths[4].relative_to(Path(__file__).resolve().parents[2])}")
    print(f"LTS manifest: {paths[5].relative_to(Path(__file__).resolve().parents[2])}")


if __name__ == "__main__":
    main()


__all__ = [
    "MaterializedLtsRunResult",
    "persist_materialized_lts_artifacts",
    "run_lts_transition_materialized",
]
