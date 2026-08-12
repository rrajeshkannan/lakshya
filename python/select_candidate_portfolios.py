"""
Step 7 of the portfolio pipeline: turn the frontier into named, concrete portfolios.

The frontier itself (output/frontier_points.csv) already has ~16-25 valid portfolios in
it — every point on that curve is a genuine efficient trade-off. This script doesn't
add new math; it just names N points along that curve so Step 8 (goal-mapping) has
something concrete and human-nameable to assign to each goal, rather than picking
blind between 16+ unlabeled numbers.

Five named buckets by default (Very Conservative -> Very Aggressive), spread evenly
by volatility rank across the frontier — but anchored on the three points that
actually mean something mathematically rather than picked arbitrarily:
  - Lowest-volatility point  = Global Minimum Variance (always the first bucket)
  - Highest-Sharpe point     = Max Sharpe / tangency portfolio (always included as
    one of the buckets — this is also the only point Step 6's bootstrap validated)
  - Highest-return point     = most return obtainable under your weight caps (last bucket)
  - Remaining buckets (if n_buckets > 3) fill in evenly by volatility rank between them.

Reads:   output/frontier_points.csv
         output/frontier_key_portfolios.csv
         output/frontier_bootstrap_stability.csv
         data/funds_universe.csv
Writes:  output/candidate_portfolios.csv   (one row per fund, one column per bucket)
         Prints a summary and the bootstrap stability cross-check (Max-Sharpe bucket only).

Usage:
    python select_candidate_portfolios.py
    python select_candidate_portfolios.py --n-buckets 3    # back to the original 3
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FRONTIER_POINTS_CSV = ROOT / "output" / "frontier_points.csv"
KEY_PORTFOLIOS_CSV = ROOT / "output" / "frontier_key_portfolios.csv"
STABILITY_CSV = ROOT / "output" / "frontier_bootstrap_stability.csv"
FUNDS_UNIVERSE_CSV = ROOT / "data" / "funds_universe.csv"
OUTPUT_CSV = ROOT / "output" / "candidate_portfolios.csv"

UNSTABLE_WEIGHT_THRESHOLD = 0.05
UNSTABLE_INCLUSION_THRESHOLD = 0.30

BUCKET_NAMES_5 = ["Very Conservative", "Conservative", "Moderate", "Aggressive", "Very Aggressive"]
BUCKET_NAMES_3 = ["Conservative", "Moderate", "Aggressive"]


def build_bucket_labels(n: int) -> list[str]:
    if n == 3:
        return BUCKET_NAMES_3
    if n == 5:
        return BUCKET_NAMES_5
    return [f"Bucket {i+1} of {n}" for i in range(n)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Name N concrete portfolios along the frontier.")
    parser.add_argument("--n-buckets", type=int, default=5, help="Number of named portfolios to select (default 5)")
    args = parser.parse_args()

    if not FRONTIER_POINTS_CSV.exists() or not KEY_PORTFOLIOS_CSV.exists():
        raise FileNotFoundError("Missing frontier outputs — run compute_frontier.py first.")

    universe = pd.read_csv(FUNDS_UNIVERSE_CSV, dtype=str).set_index("isin")
    key_portfolios = pd.read_csv(KEY_PORTFOLIOS_CSV)
    frontier_points = pd.read_csv(FRONTIER_POINTS_CSV)

    isins = [c for c in key_portfolios.columns if c not in ("portfolio", "return_pct", "volatility_pct", "sharpe")]

    gmv_row = key_portfolios[key_portfolios["portfolio"] == "Global Minimum Variance"].iloc[0]
    max_sharpe_row = key_portfolios[key_portfolios["portfolio"] == "Max Sharpe"].iloc[0]

    # Build one combined, deduplicated, volatility-sorted list of all available points:
    # the full frontier curve, plus the two named anchors (GMV, Max Sharpe) explicitly,
    # so they're guaranteed to be selectable exactly rather than approximated by whatever
    # frontier_points.csv happened to land near them.
    frontier_points = frontier_points.rename(columns={"target_return_pct": "return_pct"})
    combined = pd.concat([
        frontier_points[["return_pct", "volatility_pct", "sharpe"] + isins],
        gmv_row[["return_pct", "volatility_pct", "sharpe"] + isins].to_frame().T,
        max_sharpe_row[["return_pct", "volatility_pct", "sharpe"] + isins].to_frame().T,
    ], ignore_index=True)
    combined = combined.sort_values("volatility_pct").drop_duplicates(subset="volatility_pct").reset_index(drop=True)

    n = args.n_buckets
    idx = np.linspace(0, len(combined) - 1, n).round().astype(int)
    idx = sorted(set(idx))  # in case rounding collapsed two selections onto the same point
    selected = combined.iloc[idx].reset_index(drop=True)
    labels = build_bucket_labels(len(selected))

    # Which bucket, if any, is close to the Max Sharpe portfolio the bootstrap actually
    # validated? Used later to scope the stability cross-check correctly.
    max_sharpe_vol = max_sharpe_row["volatility_pct"]
    closest_to_max_sharpe = (selected["volatility_pct"] - max_sharpe_vol).abs().idxmin()
    max_sharpe_label = labels[closest_to_max_sharpe]

    print(f"--- {len(selected)} candidate portfolios (Max Sharpe = bootstrap-validated bucket: '{max_sharpe_label}') ---")
    for label, (_, row) in zip(labels, selected.iterrows()):
        print(f"  {label:20s} return={row['return_pct']:6.2f}%  vol={row['volatility_pct']:6.2f}%  sharpe={row['sharpe']:.3f}")

    # --- per-fund weights table ---
    fund_rows = []
    for isin in isins:
        row = {"isin": isin,
               "name": universe.loc[isin, "name"] if isin in universe.index else "?",
               "category": universe.loc[isin, "category"] if isin in universe.index else "?"}
        for label, (_, sel_row) in zip(labels, selected.iterrows()):
            col = label.lower().replace(" ", "_") + "_weight"
            row[col] = sel_row[isin]
        fund_rows.append(row)
    fund_df = pd.DataFrame(fund_rows).set_index("isin")

    max_sharpe_col = max_sharpe_label.lower().replace(" ", "_") + "_weight"

    # --- cross-check against bootstrap stability (Max Sharpe bucket only — see module docstring) ---
    warnings = []
    if STABILITY_CSV.exists():
        stability = pd.read_csv(STABILITY_CSV, index_col=0)
        fund_df["bootstrap_mean_weight"] = stability["mean_weight"].reindex(fund_df.index)
        fund_df["bootstrap_pct_samples_gt_1pct"] = stability["pct_samples_weight_gt_1pct"].reindex(fund_df.index)

        for isin, row in fund_df.iterrows():
            w = row[max_sharpe_col]
            incl = row["bootstrap_pct_samples_gt_1pct"]
            if pd.notna(w) and pd.notna(incl) and w > UNSTABLE_WEIGHT_THRESHOLD and incl < UNSTABLE_INCLUSION_THRESHOLD:
                warnings.append(
                    f"  [caution] {max_sharpe_label}: {row['name']} gets {w*100:.1f}% weight, but bootstrap only "
                    f"included it in {incl*100:.0f}% of resamples."
                )
        print(f"\n  [note] stability cross-check applies to '{max_sharpe_label}' only (the bootstrap-validated "
              "Max Sharpe bucket) — other buckets haven't been bootstrap-validated against their own objective.")
    else:
        print("\n  [note] no bootstrap stability file found — skipping the stability cross-check")

    sort_col = max_sharpe_col
    fund_df = fund_df.sort_values(sort_col, ascending=False)
    fund_df.to_csv(OUTPUT_CSV, float_format="%.4f")
    print(f"\nWrote {OUTPUT_CSV}")

    print("\n--- Non-trivial holdings per bucket (>1% weight) ---")
    for label, (_, _) in zip(labels, selected.iterrows()):
        col = label.lower().replace(" ", "_") + "_weight"
        held = fund_df[fund_df[col] > 0.01].sort_values(col, ascending=False)
        print(f"\n  {label}:")
        for isin, row in held.iterrows():
            print(f"    {row['name']:55s} {row[col]*100:5.1f}%")

    if warnings:
        print("\n--- Stability cautions ---")
        for w in warnings:
            print(w)


if __name__ == "__main__":
    main()

