"""Expose structural differences between empirically close compositions.

This is a bridge experiment between behavioural redundancy and any future
reduction decision. It does not score, rank, cluster, prune, or select a
representative. It simply joins behavioural nearest-neighbour links to the
native Composition identities and reports the structural delta between each
linked pair.

The input contract follows the canonical output of behavioral_neighborhood.py:
nearest relationships contain the full behavioural metrics, with
``mean_abs_level_gap_pct_points`` as the primary neighbourhood metric.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
NEAREST_PATH = OUTPUT_DIR / "behavioral_neighborhood_nearest.csv"
MAP_PATH = OUTPUT_DIR / "purpose_composition_map.csv"


def _read_required(path: Path, required: set[str], label: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = required - set(frame.columns)
    if missing or frame.empty:
        raise ValueError(f"Invalid or empty {label}: {path}")
    return frame


def _parse_composition(identity: str) -> dict[str, float]:
    try:
        members_part, weights_part = identity.split("|", 1)
        members = [value for value in members_part.split(",") if value]
        weights = {}
        for token in weights_part.split(","):
            fund, weight = token.split("=", 1)
            weights[fund] = float(weight)
        if set(members) != set(weights) or not members:
            raise ValueError
        return {fund: weights[fund] for fund in members}
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid Composition identity: {identity}") from exc


def _structural_row(
    purpose: str,
    left: str,
    right: str,
    metric: str,
    metric_value: float,
    metadata: dict,
) -> dict:
    a = _parse_composition(left)
    b = _parse_composition(right)
    funds_a = set(a)
    funds_b = set(b)
    shared = sorted(funds_a & funds_b)
    added = sorted(funds_b - funds_a)
    removed = sorted(funds_a - funds_b)
    all_funds = sorted(funds_a | funds_b)
    deltas = {fund: b.get(fund, 0.0) - a.get(fund, 0.0) for fund in all_funds}
    nonzero = {fund: delta for fund, delta in deltas.items() if abs(delta) > 1e-12}

    return {
        "purpose": purpose,
        "composition_a": left,
        "composition_b": right,
        "relationship_metric": metric,
        "behavioral_metric_value": float(metric_value),
        "same_team": bool(metadata.get("same_team", False)),
        "cardinality_a": len(funds_a),
        "cardinality_b": len(funds_b),
        "cardinality_changed": len(funds_a) != len(funds_b),
        "shared_fund_count": len(shared),
        "shared_funds": ",".join(shared),
        "funds_added_in_b": ",".join(added),
        "funds_removed_in_b": ",".join(removed),
        "weight_l1_difference_pp": float(sum(abs(value) for value in deltas.values())),
        "max_single_fund_weight_change_pp": float(max((abs(value) for value in deltas.values()), default=0.0)),
        "changed_fund_count": len(nonzero),
        "weight_deltas_pp": ",".join(f"{fund}={delta:+g}" for fund, delta in sorted(nonzero.items())),
        "weights_a": ",".join(f"{fund}={a[fund]:g}" for fund in sorted(a)),
        "weights_b": ",".join(f"{fund}={b[fund]:g}" for fund in sorted(b)),
    }


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(path)


def run(
    nearest_path: Path = NEAREST_PATH,
    composition_map_path: Path = MAP_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> tuple[Path, Path]:
    nearest = _read_required(
        nearest_path,
        {
            "purpose",
            "composition",
            "nearest_composition",
            "mean_abs_level_gap_pct_points",
            "same_team",
        },
        "behavioural neighbourhood artifact",
    )
    composition_map = _read_required(
        composition_map_path,
        {"purpose", "composition", "team"},
        "Purpose Composition Map",
    )

    team_index = {
        (row.purpose, row.composition): str(row.team)
        for row in composition_map.itertuples(index=False)
    }

    # Focus on the mean-path-gap neighbourhood: this is the primary metric
    # used by the descriptive neighbourhood experiment.
    nearest = nearest.copy()
    rows = []
    for row in nearest.itertuples(index=False):
        key_a = (row.purpose, row.composition)
        key_b = (row.purpose, row.nearest_composition)
        if key_a not in team_index or key_b not in team_index:
            raise ValueError(
                f"Composition missing from Purpose Composition Map: {key_a} or {key_b}"
            )
        metadata = {"same_team": bool(row.same_team)}
        record = _structural_row(
            row.purpose,
            row.composition,
            row.nearest_composition,
            "mean_abs_level_gap_pct_points",
            row.mean_abs_level_gap_pct_points,
            metadata,
        )
        record["team_a"] = team_index[key_a]
        record["team_b"] = team_index[key_b]
        record["team_changed"] = team_index[key_a] != team_index[key_b]
        rows.append(record)

    detail = pd.DataFrame(rows).sort_values(
        ["purpose", "behavioral_metric_value", "composition_a", "composition_b"],
        kind="stable",
    ).reset_index(drop=True)

    summary_rows = []
    for purpose, group in detail.groupby("purpose", sort=True):
        summary_rows.append(
            {
                "purpose": purpose,
                "nearest_link_count": len(group),
                "same_team_link_count": int(group["same_team"].sum()),
                "cross_team_link_count": int(group["team_changed"].sum()),
                "cardinality_change_count": int(group["cardinality_changed"].sum()),
                "median_weight_l1_difference_pp": float(group["weight_l1_difference_pp"].median()),
                "p90_weight_l1_difference_pp": float(group["weight_l1_difference_pp"].quantile(0.90)),
                "median_max_single_fund_weight_change_pp": float(group["max_single_fund_weight_change_pp"].median()),
                "max_single_fund_weight_change_pp": float(group["max_single_fund_weight_change_pp"].max()),
                "median_shared_fund_count": float(group["shared_fund_count"].median()),
            }
        )

    detail_path = output_dir / "behavioral_neighborhood_structure.csv"
    summary_path = output_dir / "behavioral_neighborhood_structure_summary.csv"
    _atomic_csv(detail_path, detail)
    _atomic_csv(summary_path, pd.DataFrame(summary_rows))
    return detail_path, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Describe structural differences between behavioural neighbours"
    )
    parser.add_argument("--nearest", type=Path, default=NEAREST_PATH)
    parser.add_argument("--composition-map", type=Path, default=MAP_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    for path in run(args.nearest, args.composition_map, args.output_dir):
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
