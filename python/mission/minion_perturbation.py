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
import math
import os
from pathlib import Path

import pandas as pd

from team_analysis.composition_fingerprint_store import fingerprint_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
FINGERPRINT_DIR = PROJECT_ROOT / "data" / "fingerprints" / "composition"


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
    """Return the two exact two-fund boundary portfolios for one minion.

    The minion is removed and its entire weight is assigned to each of the
    other two members in turn. These are the two nearest 5%-grid boundary
    points along the two natural axes from the trio toward its pair edges.
    """
    members, weights = parse_composition_identity(identity)
    if len(members) != 3 or minion_isin not in weights:
        raise ValueError("boundary_twins requires a three-fund Composition and a member")
    others = [member for member in members if member != minion_isin]
    minion_weight = weights[minion_isin]
    if minion_weight <= 0:
        raise ValueError("Minion weight must be positive")

    twins: list[tuple[str, str]] = []
    for recipient in others:
        pair_weights = {
            isin: weights[isin]
            for isin in others
        }
        pair_weights[recipient] += minion_weight
        twins.append((recipient, make_identity(pair_weights)))
    return twins


def _load_nav(identity: str, root: Path = FINGERPRINT_DIR) -> pd.DataFrame:
    """Load the complete persisted Composite-NAV path without recomputation."""
    members, _ = parse_composition_identity(identity)
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

    # The twin is sampled as-of the trio's exact start date, then both paths
    # are restricted to their common observed dates. This prevents a longer
    # twin history from silently giving it an earlier starting advantage.
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


def _max_drawdown(norm: pd.Series) -> tuple[float, int, int | None]:
    """Return max drawdown, underwater days, and recovery days when observed."""
    running_max = norm.cummax()
    drawdown = norm / running_max - 1.0
    trough_idx = int(drawdown.idxmin())
    max_dd = float(drawdown.iloc[trough_idx])
    peak_before = float(running_max.iloc[trough_idx])
    trough_date = None
    underwater = 0
    recovery_days: int | None = None
    if max_dd < 0:
        peak_candidates = norm.iloc[: trough_idx + 1]
        peak_value = float(peak_candidates.max())
        peak_idx = int(peak_candidates.idxmax())
        trough_date = int((merged_placeholder := 0)) if False else None
        # The caller derives calendar durations from the returned indices.
        underwater = 1
        for idx in range(peak_idx, len(norm)):
            if float(norm.iloc[idx]) < peak_value:
                underwater += 1 if idx > peak_idx else 0
            else:
                if idx > trough_idx:
                    recovery_days = idx - trough_idx
                break
    return max_dd, underwater, recovery_days


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
        recovered = path.loc[trough_idx + 1 :].loc[path.loc[trough_idx + 1 :, f"norm_{prefix}"] >= peak_value]
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
        "underwater_days": int((end - peak_date).days) if recovery_idx is None else int((path.loc[recovery_idx, "date"] - peak_date).days),
        "recovery_days_from_max_trough": None if recovery_idx is None else int((path.loc[recovery_idx, "date"] - trough_date).days),
        "mean_abs_path_gap_pct": 100.0 * float((path["norm_trio"] - path["norm_twin"]).abs().mean()),
        "max_abs_path_gap_pct": 100.0 * float((path["norm_trio"] - path["norm_twin"]).abs().max()),
    }


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
    """Compare one trio with one exact two-fund boundary twin."""
    trio_nav = _load_nav(trio_identity, fingerprint_root)
    twin_nav = _load_nav(twin_identity, fingerprint_root)
    path = _aligned_paths(trio_nav, twin_nav, years)
    trio_metrics = _path_metrics(path, "trio")
    twin_metrics = _path_metrics(path, "twin")

    daily = path.dropna(subset=["daily_return_delta"])
    largest = daily.reindex(daily["daily_return_delta"].abs().sort_values(ascending=False).index).head(10)
    event_rows = []
    for row in largest.itertuples(index=False):
        event_rows.append({
            "purpose": purpose,
            "trio": trio_identity,
            "minion": minion_isin,
            "minion_weight_pct": 100.0 * parse_composition_identity(trio_identity)[1][minion_isin],
            "twin": twin_identity,
            "recipient": recipient_isin,
            "date": row.date.strftime("%Y-%m-%d"),
            "trio_daily_return_pct": 100.0 * row.daily_return_trio,
            "twin_daily_return_pct": 100.0 * row.daily_return_twin,
            "daily_return_delta_pct": 100.0 * row.daily_return_delta,
        })

    row = {
        "purpose": purpose,
        "trio": trio_identity,
        "minion": minion_isin,
        "minion_weight_pct": 100.0 * parse_composition_identity(trio_identity)[1][minion_isin],
        "twin": twin_identity,
        "recipient": recipient_isin,
        "twin_is_purpose_survivor": twin_identity in purpose_survivors,
        "horizon_years": years,
        **{f"trio_{key}": value for key, value in trio_metrics.items()},
        **{f"twin_{key}": value for key, value in twin_metrics.items()},
        "cagr_delta_pp": trio_metrics["cagr_pct"] - twin_metrics["cagr_pct"],
        "max_drawdown_delta_pp": trio_metrics["max_drawdown_pct"] - twin_metrics["max_drawdown_pct"],
        "recovery_days_delta": (
            None
            if trio_metrics["recovery_days_from_max_trough"] is None
            or twin_metrics["recovery_days_from_max_trough"] is None
            else trio_metrics["recovery_days_from_max_trough"] - twin_metrics["recovery_days_from_max_trough"]
        ),
    }
    return row, event_rows


def read_survivors(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "composition" not in rows[0]:
        raise ValueError(f"Invalid survivor file: {path}")
    return [row["composition"] for row in rows]


def run(
    purposes: list[str],
    max_minion_weight_pct: float = 10.0,
    output_dir: Path = OUTPUT_DIR,
    fingerprint_root: Path = FINGERPRINT_DIR,
    horizons: dict[str, int] | None = None,
) -> tuple[Path, Path]:
    """Run the historical minion experiment for selected Purpose survivors."""
    horizons = horizons or {"Edu_B": 3, "Home_Loan": 7, "Marriage": 7, "Retirement": 10, "Stitch": 7, "Kutti": 7}
    rows: list[dict] = []
    events: list[dict] = []

    for purpose in sorted(purposes):
        survivor_path = output_dir / f"mission_survivors_{purpose}.csv"
        survivors = read_survivors(survivor_path)
        survivor_set = set(survivors)
        for identity in survivors:
            members, weights = parse_composition_identity(identity)
            if len(members) != 3:
                continue
            for minion in members:
                weight_pct = 100.0 * weights[minion]
                if weight_pct > max_minion_weight_pct:
                    continue
                for recipient, twin in boundary_twins(identity, minion):
                    row, event_rows = compare_one(
                        purpose,
                        identity,
                        minion,
                        twin,
                        recipient,
                        survivor_set,
                        horizons[purpose],
                        fingerprint_root,
                    )
                    rows.append(row)
                    events.extend(event_rows)

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
    parser = argparse.ArgumentParser(description="Analyze historical perturbations from small Composition allocations")
    parser.add_argument("--purposes", nargs="+", default=["Retirement"], help="Purpose names; default: Retirement")
    parser.add_argument("--max-minion-weight", type=float, default=10.0)
    args = parser.parse_args()
    paths = run(args.purposes, args.max_minion_weight)
    for path in paths:
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
