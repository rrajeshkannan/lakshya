"""Descriptive Purpose Composition Map for MISSION survivors.

The analysis deliberately stops at native Lakshya identities:

    exact Composition -> Fund set / Team -> Fund exposure

It does not score, rank, or invent a continuous similarity metric. Team
identity is membership-only, so fund-set identity and Team identity are
equivalent by construction in the current model.
"""

from __future__ import annotations

import argparse
import csv
import os
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from statistics import mean, median

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"


def parse_composition_identity(identity: str) -> tuple[tuple[str, ...], dict[str, float]]:
    """Return canonical member ISINs and weights from a Composition identity."""
    members_raw, weights_raw = identity.split("|", 1)
    members = tuple(value for value in members_raw.split(",") if value)
    weights: dict[str, float] = {}
    for token in weights_raw.split(","):
        isin, value = token.split("=", 1)
        weights[isin] = float(value)
    if set(members) != set(weights):
        raise ValueError(f"Invalid Composition identity: {identity}")
    return members, weights


def _read_survivors(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "composition" not in rows[0]:
        raise ValueError(f"Invalid or empty MISSION survivor file: {path}")
    identities = [row["composition"] for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError(f"Duplicate Composition identities in {path}")
    return identities


def _atomic_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def build_purpose_composition_map(
    survivor_identities: dict[str, list[str]],
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Build composition, structural, fund-exposure, and overlap rows."""
    if not survivor_identities:
        raise ValueError("At least one Purpose is required")

    parsed: dict[str, dict[str, tuple[tuple[str, ...], dict[str, float]]]] = {}
    for purpose, identities in survivor_identities.items():
        if not identities:
            raise ValueError(f"Purpose has no MISSION survivors: {purpose}")
        if len(identities) != len(set(identities)):
            raise ValueError(f"Duplicate Composition identities for Purpose: {purpose}")
        parsed[purpose] = {
            identity: parse_composition_identity(identity) for identity in identities
        }

    map_rows: list[dict] = []
    summary_rows: list[dict] = []
    exposure_rows: list[dict] = []
    fund_stats: dict[tuple[str, str], list[float]] = defaultdict(list)

    for purpose in sorted(parsed):
        identities = parsed[purpose]
        team_counts = Counter(members for members, _ in identities.values())
        cardinalities = Counter(len(members) for members, _ in identities.values())
        funds: set[str] = set()
        for identity, (members, weights) in sorted(identities.items()):
            team_key = ",".join(members)
            map_rows.append({
                "purpose": purpose,
                "composition": identity,
                "team": team_key,
                "fund_set": team_key,
                "cardinality": len(members),
                "weights": ",".join(f"{isin}={weights[isin]:.4f}" for isin in members),
            })
            for isin in members:
                funds.add(isin)
                fund_stats[(purpose, isin)].append(weights[isin])

        summary_rows.append({
            "purpose": purpose,
            "survivor_count": len(identities),
            "unique_exact_compositions": len(identities),
            "unique_fund_sets": len(team_counts),
            "unique_teams": len(team_counts),
            "unique_funds": len(funds),
            "singleton_count": cardinalities[1],
            "pair_count": cardinalities[2],
            "trio_count": cardinalities[3],
            "fund_set_equals_team_identity": True,
        })

    for (purpose, isin), weights in sorted(fund_stats.items()):
        survivor_count = len(parsed[purpose])
        exposure_rows.append({
            "purpose": purpose,
            "isin": isin,
            "survivor_count": survivor_count,
            "presence_pct": 100.0 * len(weights) / survivor_count,
            "mean_weight_pct": 100.0 * mean(weights),
            "median_weight_pct": 100.0 * median(weights),
            "minimum_weight_pct": 100.0 * min(weights),
            "maximum_weight_pct": 100.0 * max(weights),
        })

    overlap_rows: list[dict] = []
    for left, right in combinations(sorted(parsed), 2):
        left_exact = set(parsed[left])
        right_exact = set(parsed[right])
        left_sets = {members for members, _ in parsed[left].values()}
        right_sets = {members for members, _ in parsed[right].values()}
        exact_intersection = len(left_exact & right_exact)
        set_intersection = len(left_sets & right_sets)
        overlap_rows.append({
            "purpose_a": left,
            "purpose_b": right,
            "survivors_a": len(left_exact),
            "survivors_b": len(right_exact),
            "exact_composition_overlap": exact_intersection,
            "fund_set_overlap": set_intersection,
            "team_overlap": set_intersection,
            "fund_set_equals_team_identity": True,
            "exact_overlap_pct_of_a": 100.0 * exact_intersection / len(left_exact),
            "exact_overlap_pct_of_b": 100.0 * exact_intersection / len(right_exact),
            "fund_set_overlap_pct_of_a": 100.0 * set_intersection / len(left_sets),
            "fund_set_overlap_pct_of_b": 100.0 * set_intersection / len(right_sets),
        })

    return map_rows, summary_rows, exposure_rows, overlap_rows


def write_purpose_composition_map(
    survivor_identities: dict[str, list[str]],
    output_dir: Path = OUTPUT_DIR,
) -> tuple[Path, Path, Path, Path]:
    """Persist deterministic descriptive Purpose Composition Map artifacts."""
    map_rows, summary_rows, exposure_rows, overlap_rows = build_purpose_composition_map(
        survivor_identities
    )
    map_path = output_dir / "purpose_composition_map.csv"
    summary_path = output_dir / "purpose_composition_summary.csv"
    exposure_path = output_dir / "purpose_fund_exposure.csv"
    overlap_path = output_dir / "purpose_overlap.csv"

    _atomic_csv(
        map_path,
        ["purpose", "composition", "team", "fund_set", "cardinality", "weights"],
        map_rows,
    )
    _atomic_csv(
        summary_path,
        [
            "purpose", "survivor_count", "unique_exact_compositions", "unique_fund_sets",
            "unique_teams", "unique_funds", "singleton_count", "pair_count", "trio_count",
            "fund_set_equals_team_identity",
        ],
        summary_rows,
    )
    _atomic_csv(
        exposure_path,
        [
            "purpose", "isin", "survivor_count", "presence_pct", "mean_weight_pct",
            "median_weight_pct", "minimum_weight_pct", "maximum_weight_pct",
        ],
        exposure_rows,
    )
    _atomic_csv(
        overlap_path,
        [
            "purpose_a", "purpose_b", "survivors_a", "survivors_b",
            "exact_composition_overlap", "fund_set_overlap", "team_overlap",
            "fund_set_equals_team_identity", "exact_overlap_pct_of_a", "exact_overlap_pct_of_b",
            "fund_set_overlap_pct_of_a", "fund_set_overlap_pct_of_b",
        ],
        overlap_rows,
    )
    return map_path, summary_path, exposure_path, overlap_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the descriptive MISSION Purpose Composition Map"
    )
    parser.add_argument(
        "--purposes", nargs="+", help="Purpose names to include; default: all available survivor files"
    )
    args = parser.parse_args()

    files = sorted(OUTPUT_DIR.glob("mission_survivors_*.csv"))
    if args.purposes:
        files = [
            OUTPUT_DIR / f"mission_survivors_{purpose}.csv"
            for purpose in sorted(set(args.purposes))
        ]
    if not files:
        raise SystemExit("No MISSION survivor files found")
    missing = [path for path in files if not path.is_file()]
    if missing:
        raise SystemExit("Missing MISSION survivor file(s): " + ", ".join(str(p) for p in missing))

    survivors = {
        path.stem.removeprefix("mission_survivors_"): _read_survivors(path)
        for path in files
    }
    paths = write_purpose_composition_map(survivors)
    for path in paths:
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
