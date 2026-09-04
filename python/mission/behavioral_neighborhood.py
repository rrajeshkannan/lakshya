"""Descriptive discovery of empirical behavioural neighbourhoods.

This experiment reads the already-produced behavioural-redundancy pairwise
artifact. It does not recalculate trajectories, impose a distance threshold,
cluster, score, rank, prune, or choose representatives.

A survivor's nearest neighbour is defined only by the existing
mean_abs_level_gap_pct_points metric. Mutual-nearest links and their natural
graph components are exposed as descriptive structure for inspection.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
PAIRWISE_PATH = OUTPUT_DIR / "behavioral_redundancy_pairwise.csv"


def _read_pairwise(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {
        "purpose", "composition_a", "composition_b", "same_fund_set",
        "mean_abs_level_gap_pct_points", "max_abs_level_gap_pct_points",
        "daily_return_correlation", "cagr_difference_pp", "max_drawdown_difference_pp",
    }
    missing = required - set(frame.columns)
    if missing or frame.empty:
        raise ValueError(f"Invalid behavioural redundancy pairwise artifact: {path}")
    return frame


def _nearest_for_purpose(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for purpose, group in frame.groupby("purpose", sort=True):
        neighbours = {}
        for composition in sorted(set(group["composition_a"]) | set(group["composition_b"])):
            candidates = group[
                (group["composition_a"] == composition) |
                (group["composition_b"] == composition)
            ].copy()
            candidates["neighbour"] = candidates.apply(
                lambda row: row["composition_b"] if row["composition_a"] == composition else row["composition_a"],
                axis=1,
            )
            candidates = candidates.sort_values(
                ["mean_abs_level_gap_pct_points", "neighbour"],
                kind="stable",
            )
            row = candidates.iloc[0]
            neighbours[composition] = row["neighbour"]
            rows.append({
                "purpose": purpose,
                "composition": composition,
                "nearest_composition": row["neighbour"],
                "mean_abs_level_gap_pct_points": float(row["mean_abs_level_gap_pct_points"]),
                "max_abs_level_gap_pct_points": float(row["max_abs_level_gap_pct_points"]),
                "daily_return_correlation": float(row["daily_return_correlation"]),
                "cagr_difference_pp": float(row["cagr_difference_pp"]),
                "max_drawdown_difference_pp": float(row["max_drawdown_difference_pp"]),
                "same_team": bool(row["same_fund_set"]),
                "mutual_nearest": False,
            })
        for row in rows:
            if row["purpose"] == purpose and neighbours.get(row["nearest_composition"]) == row["composition"]:
                row["mutual_nearest"] = True
    return pd.DataFrame(rows)


def _mutual_links(nearest: pd.DataFrame) -> pd.DataFrame:
    mutual = nearest[nearest["mutual_nearest"]].copy()
    if mutual.empty:
        return pd.DataFrame(columns=[
            "purpose", "composition_a", "composition_b", "mean_abs_level_gap_pct_points",
            "max_abs_level_gap_pct_points", "daily_return_correlation", "same_team",
        ])
    pairs = []
    for purpose, group in mutual.groupby("purpose", sort=True):
        seen = set()
        for row in group.sort_values(["composition", "nearest_composition"]).itertuples(index=False):
            pair = tuple(sorted((row.composition, row.nearest_composition)))
            key = (purpose, pair)
            if key in seen:
                continue
            seen.add(key)
            pairs.append({
                "purpose": purpose,
                "composition_a": pair[0],
                "composition_b": pair[1],
                "mean_abs_level_gap_pct_points": row.mean_abs_level_gap_pct_points,
                "max_abs_level_gap_pct_points": row.max_abs_level_gap_pct_points,
                "daily_return_correlation": row.daily_return_correlation,
                "same_team": row.same_team,
            })
    return pd.DataFrame(pairs)


def _components(nearest: pd.DataFrame) -> pd.DataFrame:
    """Find connected components of the mutual-nearest graph, with no threshold."""
    rows = []
    for purpose, group in nearest.groupby("purpose", sort=True):
        adjacency = {c: set() for c in set(group["composition"]) | set(group["nearest_composition"])}
        for row in group[group["mutual_nearest"]].itertuples(index=False):
            adjacency[row.composition].add(row.nearest_composition)
            adjacency[row.nearest_composition].add(row.composition)
        seen = set()
        component_id = 0
        for start in sorted(adjacency):
            if start in seen:
                continue
            component_id += 1
            stack = [start]
            members = []
            while stack:
                current = stack.pop()
                if current in seen:
                    continue
                seen.add(current)
                members.append(current)
                stack.extend(sorted(adjacency[current] - seen, reverse=True))
            for composition in sorted(members):
                rows.append({
                    "purpose": purpose,
                    "component_id": component_id,
                    "composition": composition,
                    "component_size": len(members),
                    "component_has_mutual_link": len(members) > 1,
                })
    return pd.DataFrame(rows)


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(path)


def run(
    pairwise_path: Path = PAIRWISE_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> tuple[Path, Path, Path]:
    pairwise = _read_pairwise(pairwise_path)
    nearest = _nearest_for_purpose(pairwise)
    links = _mutual_links(nearest)
    components = _components(nearest)

    summary_rows = []
    for purpose, group in nearest.groupby("purpose", sort=True):
        links_for_purpose = links[links["purpose"] == purpose]
        comps = components[components["purpose"] == purpose]
        summary_rows.append({
            "purpose": purpose,
            "survivor_count": len(group),
            "mutual_nearest_pair_count": len(links_for_purpose),
            "mutual_nearest_pair_pct": 100.0 * len(links_for_purpose) / len(group),
            "cross_team_mutual_pair_count": int((~links_for_purpose["same_team"]).sum()) if not links_for_purpose.empty else 0,
            "component_count": int(comps["component_id"].nunique()) if not comps.empty else 0,
            "multi_member_component_count": int((comps.groupby("component_id")["composition"].size() > 1).sum()) if not comps.empty else 0,
            "largest_component_size": int(comps["component_size"].max()) if not comps.empty else 0,
            "singleton_component_count": int((comps["component_size"] == 1).sum()) if not comps.empty else 0,
        })

    nearest_path = output_dir / "behavioral_neighborhood_nearest.csv"
    links_path = output_dir / "behavioral_neighborhood_links.csv"
    components_path = output_dir / "behavioral_neighborhood_components.csv"
    summary_path = output_dir / "behavioral_neighborhood_summary.csv"
    _atomic_csv(nearest_path, nearest)
    _atomic_csv(links_path, links)
    _atomic_csv(components_path, components)
    _atomic_csv(summary_path, pd.DataFrame(summary_rows))
    return nearest_path, links_path, components_path, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Map empirical behavioural neighbourhoods")
    parser.add_argument("--pairwise", type=Path, default=PAIRWISE_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    for path in run(args.pairwise, args.output_dir):
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
