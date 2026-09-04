"""Descriptive discovery of behavioural duplication among MISSION survivors.

This experiment asks only how different surviving Composition trajectories
actually are. It does not use minion perturbations, scores, clustering
thresholds, ranking, pruning, or a reduction decision.

The first pass deliberately emits pairwise behavioural evidence so that any
later redundancy gate can be derived from observed structure rather than
imposed in advance.
"""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from .trajectory_observation import observe_trajectory, select_observable_horizon
from .observation_horizon import nearest_supported_horizon

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
FINGERPRINT_DIR = PROJECT_ROOT / "data" / "fingerprints" / "composition"


def _read_survivors(path: Path) -> list[str]:
    frame = pd.read_csv(path)
    if "composition" not in frame.columns or frame.empty:
        raise ValueError(f"Invalid or empty MISSION survivor file: {path}")
    identities = frame["composition"].astype(str).tolist()
    if len(identities) != len(set(identities)):
        raise ValueError(f"Duplicate Composition identities in {path}")
    return identities


def _load_nav(identity: str, root: Path = FINGERPRINT_DIR) -> pd.DataFrame:
    path = root / f"{identity}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Persisted Composition fingerprint missing: {identity}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("composition") != identity or payload.get("kind") != "composition_fingerprint":
        raise ValueError(f"Invalid persisted Composition fingerprint: {path}")
    nav = pd.DataFrame(payload.get("nav", []))
    if set(nav.columns) != {"date", "nav"} or nav.empty:
        raise ValueError(f"Invalid persisted NAV path: {path}")
    nav["date"] = pd.to_datetime(nav["date"])
    nav["nav"] = pd.to_numeric(nav["nav"], errors="raise")
    if nav["nav"].isna().any() or (nav["nav"] <= 0).any():
        raise ValueError(f"Invalid persisted NAV values: {path}")
    return nav.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)


def _prepare_path(nav: pd.DataFrame, nominal_horizon: int) -> pd.DataFrame | None:
    selected = select_observable_horizon(nav, nominal_horizon)
    if selected is None:
        return None
    observation = observe_trajectory(nav, selected)
    return pd.DataFrame(
        {
            "date": [point.date for point in observation.points],
            "elapsed_days": [point.elapsed_days for point in observation.points],
            "normalized_nav": [point.normalized_nav for point in observation.points],
        }
    )


def _align_paths(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    """Compare normalized paths on common elapsed-day observations."""
    left = left[["elapsed_days", "normalized_nav"]].rename(columns={"normalized_nav": "nav_a"})
    right = right[["elapsed_days", "normalized_nav"]].rename(columns={"normalized_nav": "nav_b"})
    common = left.merge(right, on="elapsed_days", how="inner").sort_values("elapsed_days")
    if len(common) < 2:
        raise ValueError("Need at least two common elapsed-day observations")
    return common.reset_index(drop=True)


def _metrics(left: pd.DataFrame, right: pd.DataFrame) -> dict[str, float | int]:
    path = _align_paths(left, right)
    gap = path["nav_a"] - path["nav_b"]
    daily_a = path["nav_a"].pct_change().dropna()
    daily_b = path["nav_b"].pct_change().dropna()

    years = max(float(path["elapsed_days"].iloc[-1]) / 365.2425, 1e-12)
    cagr_a = float(path["nav_a"].iloc[-1]) ** (1.0 / years) - 1.0
    cagr_b = float(path["nav_b"].iloc[-1]) ** (1.0 / years) - 1.0

    def max_drawdown(series: pd.Series) -> float:
        return float((series / series.cummax() - 1.0).min())

    return {
        "common_days": int(len(path)),
        "elapsed_years": years,
        "end_gap_pct_points": 100.0 * float(gap.iloc[-1]),
        "mean_abs_level_gap_pct_points": 100.0 * float(gap.abs().mean()),
        "max_abs_level_gap_pct_points": 100.0 * float(gap.abs().max()),
        "level_correlation": float(path["nav_a"].corr(path["nav_b"])),
        "daily_return_correlation": float(daily_a.corr(daily_b)),
        "cagr_difference_pp": 100.0 * (cagr_a - cagr_b),
        "max_drawdown_difference_pp": 100.0 * (max_drawdown(path["nav_a"]) - max_drawdown(path["nav_b"])),
    }


def parse_members(identity: str) -> tuple[str, ...]:
    return tuple(value for value in identity.split("|", 1)[0].split(",") if value)


def _pair_row(task: tuple[str, str, str, pd.DataFrame, pd.DataFrame]) -> dict:
    """Compute one independent pair comparison."""
    purpose, left, right, left_path, right_path = task
    metrics = _metrics(left_path, right_path)
    left_members = parse_members(left)
    right_members = parse_members(right)
    return {
        "purpose": purpose,
        "composition_a": left,
        "composition_b": right,
        "cardinality_a": len(left_members),
        "cardinality_b": len(right_members),
        "same_fund_set": left_members == right_members,
        **metrics,
    }


def _default_workers() -> int:
    """Choose a bounded default suitable for pandas-heavy pair comparisons."""
    return min(32, max(1, (os.cpu_count() or 1)))


def build_pairwise_rows(
    purpose: str,
    survivor_identities: list[str],
    paths: dict[str, pd.DataFrame],
    workers: int | None = None,
) -> list[dict]:
    """Compare each unique survivor pair, optionally in parallel.

    Executor.map preserves input order, so the resulting artifact remains
    deterministic regardless of worker count.
    """
    if workers is None:
        workers = _default_workers()
    if workers < 1:
        raise ValueError("workers must be at least 1")

    identities = sorted(paths)
    tasks = [
        (purpose, left, right, paths[left], paths[right])
        for left, right in combinations(identities, 2)
    ]
    if not tasks:
        return []
    if workers == 1:
        return [_pair_row(task) for task in tasks]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(_pair_row, tasks))


def build_nearest_rows(pairwise: list[dict]) -> list[dict]:
    """Expose nearest relationships separately for each descriptive metric."""
    rows: list[dict] = []
    metrics = [
        "mean_abs_level_gap_pct_points",
        "max_abs_level_gap_pct_points",
        "daily_return_correlation",
        "cagr_difference_pp",
        "max_drawdown_difference_pp",
    ]
    for metric in metrics:
        source: dict[str, list[tuple[float, str, str]]] = {}
        for row in pairwise:
            value = row[metric]
            if pd.isna(value):
                continue
            source.setdefault(row["composition_a"], []).append((float(value), row["composition_a"], row["composition_b"]))
            source.setdefault(row["composition_b"], []).append((float(value), row["composition_b"], row["composition_a"]))
        for composition, values in source.items():
            if metric == "daily_return_correlation":
                values.sort(key=lambda item: (-item[0], item[2]))
            elif metric in {"cagr_difference_pp", "max_drawdown_difference_pp"}:
                values.sort(key=lambda item: (abs(item[0]), item[2]))
            else:
                values.sort(key=lambda item: (abs(item[0]), item[2]))
            if values:
                value, _, neighbour = values[0]
                rows.append(
                    {
                        "purpose": next(row["purpose"] for row in pairwise if row["composition_a"] == composition or row["composition_b"] == composition),
                        "composition": composition,
                        "relationship_metric": metric,
                        "nearest_composition": neighbour,
                        "metric_value": value,
                    }
                )
    return rows


def _atomic_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pd.DataFrame(rows).to_csv(temporary, index=False)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(path)


def run(
    purposes: list[str] | None = None,
    output_dir: Path = OUTPUT_DIR,
    fingerprint_root: Path = FINGERPRINT_DIR,
    workers: int | None = None,
) -> tuple[Path, Path, Path]:
    files = sorted(OUTPUT_DIR.glob("mission_survivors_*.csv"))
    if purposes:
        files = [OUTPUT_DIR / f"mission_survivors_{purpose}.csv" for purpose in sorted(set(purposes))]
    if not files:
        raise ValueError("No MISSION survivor files found")
    missing = [path for path in files if not path.is_file()]
    if missing:
        raise ValueError("Missing MISSION survivor file(s): " + ", ".join(str(path) for path in missing))

    all_pairs: list[dict] = []
    summary: list[dict] = []
    for path in files:
        purpose = path.stem.removeprefix("mission_survivors_")
        identities = _read_survivors(path)
        # Purpose determines only the upper analytical horizon; each Composition
        # retains its own selected observable horizon.
        purpose_horizons = {
            "Edu_B": 4,
            "Home_Loan": 9,
            "Marriage": 9,
            "Retirement": 12,
            "Stitch": 0,
            "Kutti": 0,
        }
        purpose_horizon = purpose_horizons.get(purpose)
        if purpose_horizon is None:
            raise ValueError(f"Unknown Purpose horizon: {purpose}")
        if purpose_horizon <= 0:
            continue
        nominal = nearest_supported_horizon(purpose_horizon)
        if nominal is None:
            continue
        paths: dict[str, pd.DataFrame] = {}
        for identity in identities:
            nav = _load_nav(identity, fingerprint_root)
            prepared = _prepare_path(nav, nominal)
            if prepared is not None:
                paths[identity] = prepared
        pairs = build_pairwise_rows(purpose, identities, paths, workers=workers)
        all_pairs.extend(pairs)
        values = pd.DataFrame(pairs)
        summary.append(
            {
                "purpose": purpose,
                "survivor_count": len(identities),
                "trajectory_observed_count": len(paths),
                "trajectory_missing_count": len(identities) - len(paths),
                "nominal_horizon_years": nominal,
                "pair_count": len(pairs),
                "exact_identity_duplicates": 0,
                "median_mean_abs_level_gap_pct_points": float(values["mean_abs_level_gap_pct_points"].median()) if not values.empty else np.nan,
                "p90_mean_abs_level_gap_pct_points": float(values["mean_abs_level_gap_pct_points"].quantile(0.90)) if not values.empty else np.nan,
                "minimum_mean_abs_level_gap_pct_points": float(values["mean_abs_level_gap_pct_points"].min()) if not values.empty else np.nan,
                "median_daily_return_correlation": float(values["daily_return_correlation"].median()) if not values.empty else np.nan,
                "maximum_daily_return_correlation": float(values["daily_return_correlation"].max()) if not values.empty else np.nan,
            }
        )

    pairwise_path = output_dir / "behavioral_redundancy_pairwise.csv"
    nearest_path = output_dir / "behavioral_redundancy_nearest.csv"
    summary_path = output_dir / "behavioral_redundancy_summary.csv"
    _atomic_csv(pairwise_path, all_pairs)
    _atomic_csv(nearest_path, build_nearest_rows(all_pairs))
    _atomic_csv(summary_path, summary)
    return pairwise_path, nearest_path, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover behavioural duplication among MISSION survivors")
    parser.add_argument("--purposes", nargs="+")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel pair-comparison workers (default: CPU count, capped at 32)")
    args = parser.parse_args()
    for path in run(args.purposes, workers=args.workers):
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
