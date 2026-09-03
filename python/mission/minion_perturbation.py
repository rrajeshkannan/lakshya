"""Historical perturbation analysis for small allocations in survivor Compositions.

This is an experimental, descriptive layer. It asks a narrow question:

    When a small member is present, what historical path behaviour appears
    that is absent from the corresponding two-fund boundary portfolios?

No simulation, score, ranking, pruning, or role label is introduced. The
experiment uses already-persisted Composition fingerprints, whose complete
NAV paths are durable evidence, and compares each surviving trio with the two
nearest exact two-fund boundary Compositions obtained by assigning the small
member's weight to either remaining member.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
FINGERPRINT_DIR = PROJECT_ROOT / "data" / "fingerprints" / "composition"

DEFAULT_HORIZONS = {
    "Edu_B": 3,
    "Home_Loan": 7,
    "Marriage": 7,
    "Retirement": 10,
    "Stitch": 7,
    "Kutti": 7,
}


def parse_composition_identity(identity: str) -> tuple[tuple[str, ...], dict[str, float]]:
    """Parse the canonical Composition identity used by Lakshya."""
    members_raw, weights_raw = identity.split("|", 1)
    members = tuple(value for value in members_raw.split(",") if value)
    weights: dict[str, float] = {}
    for token in weights_raw.split(","):
        isin, value = token.split("=", 1)
        weights[isin] = float(value)
    if set(members) != set(weights) or not members:
        raise ValueError(f"Invalid Composition identity: {identity}")
    return members, weights


def make_identity(weights: dict[str, float]) -> str:
    """Build the canonical identity for a positive-weight Composition."""
    members = sorted(weights)
    return (
        ",".join(members)
        + "|"
        + ",".join(f"{isin}={weights[isin]:.4f}" for isin in members)
    )


def boundary_twins(
    identity: str,
    minion_isin: str,
) -> list[tuple[str, str]]:
    """Return the two exact two-fund boundary portfolios for one minion."""
    members, weights = parse_composition_identity(identity)
    if len(members) != 3 or minion_isin not in weights:
        raise ValueError("boundary_twins requires a three-fund Composition and a member")
    others = [member for member in members if member != minion_isin]
    minion_weight = weights[minion_isin]
    if minion_weight <= 0:
        raise ValueError("Minion weight must be positive")

    twins: list[tuple[str, str]] = []
    for recipient in others:
        pair_weights = {isin: weights[isin] for isin in others}
        pair_weights[recipient] += minion_weight
        twins.append((recipient, make_identity(pair_weights)))
    return twins


def _load_nav(identity: str, root: Path = FINGERPRINT_DIR) -> pd.DataFrame:
    """Load the complete persisted Composite-NAV path without recomputation."""
    path = root / f"{identity}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Persisted fingerprint missing for {identity}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("composition") != identity:
        raise ValueError(f"Persisted identity mismatch in {path}")
    if payload.get("kind") != "composition_fingerprint":
        raise ValueError(f"Invalid fingerprint kind in {path}")
    nav = pd.DataFrame(payload.get("nav", []))
    if set(nav.columns) != {"date", "nav"}:
        raise ValueError(f"Invalid persisted NAV path in {path}")
    nav["date"] = pd.to_datetime(nav["date"])
    nav["nav"] = pd.to_numeric(nav["nav"], errors="raise")
    if nav.empty or nav["nav"].isna().any() or (nav["nav"] <= 0).any():
        raise ValueError(f"Invalid persisted NAV values in {path}")
    return nav.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)


def _window(nav: pd.DataFrame, end_date: pd.Timestamp, years: int) -> pd.DataFrame:
    """Take the requested trailing horizon using the existing time convention."""
    target_start = end_date - pd.DateOffset(years=years)
    eligible = nav.loc[nav["date"] <= target_start]
    if eligible.empty:
        raise ValueError(f"Insufficient history for {years}-year comparison")
    start_date = eligible["date"].iloc[-1]
    return nav.loc[nav["date"] >= start_date].copy()


def _aligned_paths(
    trio_nav: pd.DataFrame,
    twin_nav: pd.DataFrame,
    years: int,
) -> pd.DataFrame:
    """Align two paths on the trio's observable horizon and common dates."""
    end_date = min(trio_nav["date"].max(), twin_nav["date"].max())
    trio = _window(trio_nav, end_date, years)
    target_start = trio["date"].iloc[0]
    twin = twin_nav.loc[twin_nav["date"] >= target_start].copy()
    merged = trio.merge(
        twin,
        on="date",
        how="inner",
        suffixes=("_trio", "_twin"),
    )
    if merged.empty:
        raise ValueError("No common dates between trio and boundary twin")
    merged = merged.sort_values("date").reset_index(drop=True)
    base_trio = float(merged["nav_trio"].iloc[0])
    base_twin = float(merged["nav_twin"].iloc[0])
    merged["norm_trio"] = merged["nav_trio"] / base_trio
    merged["norm_twin"] = merged["nav_twin"] / base_twin
    merged["daily_return_trio"] = merged["norm_trio"].pct_change()
    merged["daily_return_twin"] = merged["norm_twin"].pct_change()
    merged["daily_return_delta"] = (
        merged["daily_return_trio"] - merged["daily_return_twin"]
    )
    return merged


def _path_metrics(path: pd.DataFrame, prefix: str) -> dict[str, float | int | str | None]:
    """Summarize a normalized observed path without reducing it to one score."""
    norm = path[f"norm_{prefix}"]
    start = path["date"].iloc[0]
    end = path["date"].iloc[-1]
    elapsed_days = max(int((end - start).days), 1)
    years = elapsed_days / 365.2425
    end_value = float(norm.iloc[-1])
    cagr = end_value ** (1.0 / years) - 1.0

    running_max = norm.cummax()
    drawdown = norm / running_max - 1.0
    trough_idx = int(drawdown.idxmin())
    max_dd = float(drawdown.iloc[trough_idx])
    peak_value = float(running_max.iloc[trough_idx])
    peak_indices = running_max.iloc[: trough_idx + 1]
    peak_idx = int(peak_indices[peak_indices == peak_value].index[0])
    trough_date = path.loc[trough_idx, "date"]
    peak_date = path.loc[peak_idx, "date"]

    recovery_idx = None
    if max_dd < 0:
        recovered = path.loc[trough_idx + 1 :].loc[
            path.loc[trough_idx + 1 :, f"norm_{prefix}"] >= peak_value
        ]
        if not recovered.empty:
            recovery_idx = int(recovered.index[0])

    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "common_days": len(path),
        "end_normalized_nav": end_value,
        "cagr_pct": 100.0 * cagr,
        "max_drawdown_pct": 100.0 * max_dd,
        "max_drawdown_date": trough_date.strftime("%Y-%m-%d"),
        "peak_before_max_drawdown_date": peak_date.strftime("%Y-%m-%d"),
        "underwater_days": (
            int((end - peak_date).days)
            if recovery_idx is None
            else int((path.loc[recovery_idx, "date"] - peak_date).days)
        ),
        "recovery_days_from_max_trough": (
            None
            if recovery_idx is None
            else int((path.loc[recovery_idx, "date"] - trough_date).days)
        ),
        "mean_abs_path_gap_pct": 100.0 * float(
            (path["norm_trio"] - path["norm_twin"]).abs().mean()
        ),
        "max_abs_path_gap_pct": 100.0 * float(
            (path["norm_trio"] - path["norm_twin"]).abs().max()
        ),
    }


def _compare_from_cache(
    task: tuple[str, str, str, str, str, set[str], int],
    nav_cache: dict[str, pd.DataFrame],
) -> tuple[dict, list[dict]]:
    """Compare one trio/twin pair using already-loaded NAV paths."""
    (
        purpose,
        trio_identity,
        minion_isin,
        twin_identity,
        recipient_isin,
        purpose_survivors,
        years,
    ) = task
    trio_nav = nav_cache[trio_identity]
    twin_nav = nav_cache[twin_identity]
    path = _aligned_paths(trio_nav, twin_nav, years)
    trio_metrics = _path_metrics(path, "trio")
    twin_metrics = _path_metrics(path, "twin")
    minion_weight_pct = 100.0 * parse_composition_identity(trio_identity)[1][minion_isin]

    daily = path.dropna(subset=["daily_return_delta"])
    largest = daily.reindex(
        daily["daily_return_delta"].abs().sort_values(ascending=False).index
    ).head(10)
    event_rows = [
        {
            "purpose": purpose,
            "trio": trio_identity,
            "minion": minion_isin,
            "minion_weight_pct": minion_weight_pct,
            "twin": twin_identity,
            "recipient": recipient_isin,
            "date": row.date.strftime("%Y-%m-%d"),
            "trio_daily_return_pct": 100.0 * row.daily_return_trio,
            "twin_daily_return_pct": 100.0 * row.daily_return_twin,
            "daily_return_delta_pct": 100.0 * row.daily_return_delta,
        }
        for row in largest.itertuples(index=False)
    ]

    row = {
        "purpose": purpose,
        "trio": trio_identity,
        "minion": minion_isin,
        "minion_weight_pct": minion_weight_pct,
        "twin": twin_identity,
        "recipient": recipient_isin,
        "twin_is_purpose_survivor": twin_identity in purpose_survivors,
        "horizon_years": years,
        **{f"trio_{key}": value for key, value in trio_metrics.items()},
        **{f"twin_{key}": value for key, value in twin_metrics.items()},
        "cagr_delta_pp": trio_metrics["cagr_pct"] - twin_metrics["cagr_pct"],
        "max_drawdown_delta_pp": (
            trio_metrics["max_drawdown_pct"] - twin_metrics["max_drawdown_pct"]
        ),
        "recovery_days_delta": (
            None
            if trio_metrics["recovery_days_from_max_trough"] is None
            or twin_metrics["recovery_days_from_max_trough"] is None
            else (
                trio_metrics["recovery_days_from_max_trough"]
                - twin_metrics["recovery_days_from_max_trough"]
            )
        ),
    }
    return row, event_rows


def compare_one(
    purpose: str,
    trio_identity: str,
    minion_isin: str,
    twin_identity: str,
    recipient_isin: str,
    purpose_survivors: set[str],
    years: int,
    fingerprint_root: Path = FINGERPRINT_DIR,
) -> tuple[dict, list[dict]]:
    """Compare one trio with one exact two-fund boundary twin.

    Kept as a small public helper for direct callers/tests. The main batch
    runner uses a shared NAV cache instead of repeatedly loading JSON files.
    """
    nav_cache = {
        trio_identity: _load_nav(trio_identity, fingerprint_root),
        twin_identity: _load_nav(twin_identity, fingerprint_root),
    }
    return _compare_from_cache(
        (
            purpose,
            trio_identity,
            minion_isin,
            twin_identity,
            recipient_isin,
            purpose_survivors,
            years,
        ),
        nav_cache,
    )


def read_survivors(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "composition" not in rows[0]:
        raise ValueError(f"Invalid survivor file: {path}")
    return [row["composition"] for row in rows]


def _build_tasks(
    purposes: list[str],
    max_minion_weight_pct: float,
    output_dir: Path,
    horizons: dict[str, int],
) -> tuple[list[tuple], dict[str, set[str]]]:
    """Build deterministic comparison tasks and Purpose survivor sets."""
    tasks: list[tuple] = []
    survivor_sets: dict[str, set[str]] = {}
    for purpose in sorted(purposes):
        survivor_path = output_dir / f"mission_survivors_{purpose}.csv"
        survivors = read_survivors(survivor_path)
        survivor_set = set(survivors)
        survivor_sets[purpose] = survivor_set
        for identity in survivors:
            members, weights = parse_composition_identity(identity)
            if len(members) != 3:
                continue
            for minion in members:
                weight_pct = 100.0 * weights[minion]
                if weight_pct > max_minion_weight_pct:
                    continue
                for recipient, twin in boundary_twins(identity, minion):
                    tasks.append(
                        (
                            purpose,
                            identity,
                            minion,
                            twin,
                            recipient,
                            survivor_set,
                            horizons[purpose],
                        )
                    )
    return tasks, survivor_sets


def _load_required_navs(
    tasks: list[tuple],
    fingerprint_root: Path,
) -> dict[str, pd.DataFrame]:
    """Load each unique persisted NAV path exactly once."""
    identities = sorted({task[1] for task in tasks} | {task[3] for task in tasks})
    return {identity: _load_nav(identity, fingerprint_root) for identity in identities}


def run(
    purposes: list[str],
    max_minion_weight_pct: float = 10.0,
    output_dir: Path = OUTPUT_DIR,
    fingerprint_root: Path = FINGERPRINT_DIR,
    horizons: dict[str, int] | None = None,
    workers: int | None = None,
) -> tuple[Path, Path]:
    """Run the historical minion experiment for selected Purpose survivors.

    Persisted NAV paths are loaded once into a shared in-process cache. The
    independent comparisons then run concurrently in a ThreadPoolExecutor.
    Threads are deliberate here: they share the cached DataFrames, avoiding
    both repeated disk I/O and large inter-process DataFrame serialization.
    """
    horizons = horizons or DEFAULT_HORIZONS
    tasks, _survivor_sets = _build_tasks(
        purposes,
        max_minion_weight_pct,
        output_dir,
        horizons,
    )
    nav_cache = _load_required_navs(tasks, fingerprint_root)

    if not tasks:
        results: list[tuple[dict, list[dict]]] = []
    else:
        worker_count = workers or min(32, max(1, (os.cpu_count() or 1)))
        worker_count = max(1, min(worker_count, len(tasks)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = list(executor.map(lambda task: _compare_from_cache(task, nav_cache), tasks))

    rows = [row for row, _events in results]
    events = [event for _row, event_rows in results for event in event_rows]

    comparison_path = output_dir / "minion_perturbation_comparison.csv"
    events_path = output_dir / "minion_perturbation_events.csv"
    _atomic_csv(comparison_path, rows)
    _atomic_csv(events_path, events)
    return comparison_path, events_path


def _atomic_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame = pd.DataFrame(rows)
    frame.to_csv(temporary, index=False)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze historical perturbations from small Composition allocations"
    )
    parser.add_argument(
        "--purposes",
        nargs="+",
        default=["Retirement"],
        help="Purpose names; default: Retirement",
    )
    parser.add_argument("--max-minion-weight", type=float, default=10.0)
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Concurrent comparison workers; default uses available CPU count, capped at 32",
    )
    args = parser.parse_args()
    if args.workers is not None and args.workers < 1:
        parser.error("--workers must be at least 1")
    paths = run(args.purposes, args.max_minion_weight, workers=args.workers)
    for path in paths:
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
