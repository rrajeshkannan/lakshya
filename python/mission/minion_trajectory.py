"""Historical trajectory comparison for the minion absence shock.

This is an experimental, descriptive layer. The minion is treated as a
catalyst, not as a survivor candidate. For every trio/minion case we compare
the observed trio trajectory with two counterfactual absence trajectories:
the minion weight is transferred entirely to each of the two neighbours.

Primary evidence is the trajectory itself. Frontier survival is deliberately
not used as a decision variable here.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import numpy as np

from mission.minion_perturbation import (
    DEFAULT_HORIZONS,
    FINGERPRINT_DIR,
    FUND_NAV_DIR,
    OUTPUT_DIR,
    _build_tasks,
    _load_required_navs,
    parse_composition_identity,
    boundary_twins,
)


def _three_way_path(
    trio_nav: pd.DataFrame,
    twin_a_nav: pd.DataFrame,
    twin_b_nav: pd.DataFrame,
    years: int,
) -> pd.DataFrame:
    """Align trio and both absence counterfactuals on one common observed path."""
    end_date = min(trio_nav["date"].max(), twin_a_nav["date"].max(), twin_b_nav["date"].max())
    target_start = end_date - pd.DateOffset(years=years)
    trio_candidates = trio_nav.loc[trio_nav["date"] <= target_start]
    if trio_candidates.empty:
        raise ValueError(f"Insufficient trio history for {years}-year comparison")
    start_date = trio_candidates["date"].iloc[-1]

    def trim(nav: pd.DataFrame) -> pd.DataFrame:
        return nav.loc[(nav["date"] >= start_date) & (nav["date"] <= end_date), ["date", "nav"]].copy()

    trio = trim(trio_nav).rename(columns={"nav": "nav_trio"})
    twin_a = trim(twin_a_nav).rename(columns={"nav": "nav_twin_a"})
    twin_b = trim(twin_b_nav).rename(columns={"nav": "nav_twin_b"})
    path = trio.merge(twin_a, on="date", how="inner").merge(twin_b, on="date", how="inner")
    if path.empty:
        raise ValueError("No common dates across trio and both boundary twins")
    path = path.sort_values("date").reset_index(drop=True)
    for label in ("trio", "twin_a", "twin_b"):
        path[f"norm_{label}"] = path[f"nav_{label}"] / float(path[f"nav_{label}"].iloc[0])
        path[f"daily_return_{label}"] = path[f"norm_{label}"].pct_change()

    # Trajectory residual = presence path minus counterfactual absence path.
    # Keep both normalized-level and relative residuals; neither is a score.
    for twin in ("a", "b"):
        path[f"residual_{twin}_pct_points"] = 100.0 * (path["norm_trio"] - path[f"norm_twin_{twin}"])
        path[f"residual_{twin}_relative_pct"] = 100.0 * (
            path["norm_trio"] / path[f"norm_twin_{twin}"] - 1.0
        )
        path[f"daily_return_residual_{twin}_pp"] = 100.0 * (
            path["daily_return_trio"] - path[f"daily_return_twin_{twin}"]
        )

    lower = path[["norm_twin_a", "norm_twin_b"]].min(axis=1)
    upper = path[["norm_twin_a", "norm_twin_b"]].max(axis=1)
    path["trio_inside_twin_envelope"] = path["norm_trio"].between(lower, upper)
    path["envelope_excursion_pct_points"] = np.where(
        path["norm_trio"] < lower,
        100.0 * (path["norm_trio"] - lower),
        np.where(path["norm_trio"] > upper, 100.0 * (path["norm_trio"] - upper), 0.0),
    )
    return path


def _case_summary(
    purpose: str,
    trio: str,
    minion: str,
    minion_weight_pct: float,
    twin_a: str,
    recipient_a: str,
    twin_b: str,
    recipient_b: str,
    path: pd.DataFrame,
    source_a: str,
    source_b: str,
) -> dict:
    """Describe one three-way trajectory experiment without ranking it."""
    def residual_stats(twin: str) -> dict[str, float]:
        rel = path[f"residual_{twin}_relative_pct"].dropna()
        pp = path[f"residual_{twin}_pct_points"].dropna()
        return {
            f"final_residual_{twin}_relative_pct": float(rel.iloc[-1]),
            f"mean_residual_{twin}_relative_pct": float(rel.mean()),
            f"mean_abs_residual_{twin}_relative_pct": float(rel.abs().mean()),
            f"max_abs_residual_{twin}_relative_pct": float(rel.abs().max()),
            f"final_residual_{twin}_pct_points": float(pp.iloc[-1]),
            f"max_positive_residual_{twin}_relative_pct": float(rel.max()),
            f"max_negative_residual_{twin}_relative_pct": float(rel.min()),
        }

    inside = path["trio_inside_twin_envelope"]
    excursion = path["envelope_excursion_pct_points"]
    nonzero = excursion[excursion != 0]
    return {
        "purpose": purpose,
        "trio": trio,
        "minion": minion,
        "minion_weight_pct": minion_weight_pct,
        "twin_a": twin_a,
        "recipient_a": recipient_a,
        "twin_a_source": source_a,
        "twin_b": twin_b,
        "recipient_b": recipient_b,
        "twin_b_source": source_b,
        "horizon_years": int((path["date"].iloc[-1] - path["date"].iloc[0]).days / 365.2425),
        "start_date": path["date"].iloc[0].strftime("%Y-%m-%d"),
        "end_date": path["date"].iloc[-1].strftime("%Y-%m-%d"),
        "common_days": len(path),
        **residual_stats("a"),
        **residual_stats("b"),
        "trio_inside_envelope_pct": 100.0 * float(inside.mean()),
        "trio_outside_envelope_pct": 100.0 * float((~inside).mean()),
        "mean_abs_envelope_excursion_pct_points": float(nonzero.abs().mean()) if not nonzero.empty else 0.0,
        "max_abs_envelope_excursion_pct_points": float(nonzero.abs().max()) if not nonzero.empty else 0.0,
        "envelope_upper_breaches": int((excursion > 0).sum()),
        "envelope_lower_breaches": int((excursion < 0).sum()),
    }


def _build_case_groups(purposes: list[str], max_minion_weight_pct: float, output_dir: Path, horizons: dict[str, int]):
    tasks, _ = _build_tasks(purposes, max_minion_weight_pct, output_dir, horizons)
    grouped: dict[tuple, list[tuple]] = {}
    for task in tasks:
        key = task[:3]
        grouped.setdefault(key, []).append(task)
    cases = []
    for key in sorted(grouped):
        members = grouped[key]
        if len(members) != 2:
            raise ValueError(f"Expected exactly two twins for {key}, found {len(members)}")
        cases.append(members)
    return cases


def _atomic_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pd.DataFrame(rows).to_csv(temporary, index=False)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(path)


def run(
    purposes: list[str],
    max_minion_weight_pct: float = 10.0,
    output_dir: Path = OUTPUT_DIR,
    fingerprint_root: Path = FINGERPRINT_DIR,
    fund_nav_root: Path = FUND_NAV_DIR,
    horizons: dict[str, int] | None = None,
    workers: int | None = None,
) -> tuple[Path, Path]:
    """Run the full historical trajectory comparison for every minion case."""
    horizons = horizons or DEFAULT_HORIZONS
    cases = _build_case_groups(purposes, max_minion_weight_pct, output_dir, horizons)
    tasks = [task for case in cases for task in case]
    nav_cache, nav_sources = _load_required_navs(tasks, fingerprint_root, fund_nav_root)

    def run_case(case):
        first, second = case
        purpose, trio, minion, twin_a, recipient_a, _, years = first
        _, _, _, twin_b, recipient_b, _, _ = second
        # Sort twins by recipient for deterministic A/B labels.
        pairs = sorted([(recipient_a, twin_a), (recipient_b, twin_b)], key=lambda x: x[0])
        recipient_a, twin_a = pairs[0]
        recipient_b, twin_b = pairs[1]
        path = _three_way_path(nav_cache[trio], nav_cache[twin_a], nav_cache[twin_b], years)
        minion_weight_pct = 100.0 * parse_composition_identity(trio)[1][minion]
        summary = _case_summary(
            purpose, trio, minion, minion_weight_pct, twin_a, recipient_a, twin_b, recipient_b,
            path, nav_sources[twin_a], nav_sources[twin_b]
        )
        path_rows = []
        for row in path.itertuples(index=False):
            path_rows.append({
                "purpose": purpose, "trio": trio, "minion": minion,
                "minion_weight_pct": minion_weight_pct,
                "twin_a": twin_a, "recipient_a": recipient_a,
                "twin_b": twin_b, "recipient_b": recipient_b,
                "date": row.date.strftime("%Y-%m-%d"),
                "norm_trio": row.norm_trio, "norm_twin_a": row.norm_twin_a, "norm_twin_b": row.norm_twin_b,
                "residual_a_pct_points": row.residual_a_pct_points,
                "residual_a_relative_pct": row.residual_a_relative_pct,
                "residual_b_pct_points": row.residual_b_pct_points,
                "residual_b_relative_pct": row.residual_b_relative_pct,
                "daily_return_residual_a_pp": row.daily_return_residual_a_pp,
                "daily_return_residual_b_pp": row.daily_return_residual_b_pp,
                "trio_inside_twin_envelope": row.trio_inside_twin_envelope,
                "envelope_excursion_pct_points": row.envelope_excursion_pct_points,
            })
        return summary, path_rows

    worker_count = workers or min(32, max(1, os.cpu_count() or 1))
    worker_count = max(1, min(worker_count, len(cases) or 1))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(executor.map(run_case, cases)) if cases else []

    summaries = [summary for summary, _ in results]
    paths = [row for _, rows in results for row in rows]
    summary_path = output_dir / "minion_trajectory_case_summary.csv"
    path_path = output_dir / "minion_trajectory_paths.csv"
    _atomic_csv(summary_path, summaries)
    _atomic_csv(path_path, paths)
    return summary_path, path_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare minion-present and minion-absent historical trajectories")
    parser.add_argument("--purposes", nargs="+", default=["Retirement"])
    parser.add_argument("--max-minion-weight", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()
    for path in run(args.purposes, args.max_minion_weight, workers=args.workers):
        print(path.relative_to(Path(__file__).resolve().parents[2]))


if __name__ == "__main__":
    main()
