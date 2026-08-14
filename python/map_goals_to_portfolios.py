"""
Step 8 of the portfolio pipeline: goal-mapping overlay.

One frontier (output/candidate_portfolios.csv, 5 named buckets from Step 7) serves
every goal — what differs is WHERE on it each goal sits, based on time horizon. A
goal 13 years out can absorb a bad stretch and recover; a goal 3 years out can't.

The horizon -> bucket thresholds below are a reasonable planning convention, not a law
of physics — adjust HORIZON_THRESHOLDS if your own risk appetite differs:
    >= 10 years  -> Very Aggressive
    7-10 years   -> Aggressive
    4-7  years   -> Moderate
    2-4  years   -> Conservative
    < 2  years   -> Very Conservative (see IMPORTANT caveat below)

IMPORTANT CAVEAT — read before trusting the < 2-4 year mappings: every fund in this
17-fund universe is an EQUITY fund. Even "Very Conservative" here (~14% annualized
volatility historically) is real market risk, not a safe parking spot. For a goal
genuinely inside 2-3 years, the honest answer is usually debt funds / FDs / liquid
funds — outside this equity-only pipeline entirely — not "the least-aggressive
equity bucket we happen to have." This script will still compute a mapping for
short-horizon goals so the number exists, but flags it loudly rather than pretending
an equity portfolio is a safe answer for near-term money.

Reads:   data/goals.csv                      (goal, target_date, notes)
         output/candidate_portfolios.csv      (5 buckets x 17 funds, from Step 7)
Writes:  output/goal_portfolio_mapping.csv    (one row per goal: bucket assigned,
                                                horizon, and the resulting fund weights)

Usage:
    python map_goals_to_portfolios.py
    python map_goals_to_portfolios.py --as-of 2026-08-13   # override "today" if needed
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
GOALS_CSV = ROOT / "data" / "goals.csv"
CANDIDATE_PORTFOLIOS_CSV = ROOT / "output" / "candidate_portfolios.csv"
OUTPUT_CSV = ROOT / "output" / "goal_portfolio_mapping.csv"

# (min_years_inclusive, bucket_name) — checked top-down, first match wins
HORIZON_THRESHOLDS = [
    (10, "very_aggressive"),
    (7, "aggressive"),
    (4, "moderate"),
    (2, "conservative"),
    (0, "very_conservative"),
]

DEFAULT_HORIZON_YEARS_IF_NO_DATE = {
    "Marriage_HomeLoan": 10.0,
    "Stitch_Kutti": 10.0,
}

BUCKET_ORDER = ["very_conservative", "conservative", "moderate", "aggressive", "very_aggressive"]


def assign_bucket(horizon_years: float, flexibility: str) -> tuple[str, str]:
    """
    Returns (final_bucket, horizon_implied_bucket) — kept separate so any adjustment
    is visible rather than silently baked into one number.

    A goal marked "high" flexibility (alternate funding sources available, and/or
    explicit tolerance for riding out a drawdown rather than being forced to sell)
    gets bumped one bucket more aggressive than horizon alone would suggest. This
    isn't free-floating judgment — it's a direct, transparent response to a real
    difference: horizon alone assumes the goal MUST be funded from this money on
    that exact date, which isn't true for every goal here.
    """
    horizon_bucket = "very_conservative"
    for min_years, bucket in HORIZON_THRESHOLDS:
        if horizon_years >= min_years:
            horizon_bucket = bucket
            break

    final_bucket = horizon_bucket
    if str(flexibility).strip().lower() == "high":
        idx = BUCKET_ORDER.index(horizon_bucket)
        final_bucket = BUCKET_ORDER[min(idx + 1, len(BUCKET_ORDER) - 1)]

    return final_bucket, horizon_bucket


def main() -> None:
    parser = argparse.ArgumentParser(description="Map goals to frontier buckets by horizon.")
    parser.add_argument("--as-of", type=str, default=None,
                         help="Override 'today' for horizon calculation, format YYYY-MM-DD")
    args = parser.parse_args()

    as_of = datetime.strptime(args.as_of, "%Y-%m-%d") if args.as_of else datetime.now()

    if not GOALS_CSV.exists():
        raise FileNotFoundError(f"{GOALS_CSV} not found")
    if not CANDIDATE_PORTFOLIOS_CSV.exists():
        raise FileNotFoundError(f"{CANDIDATE_PORTFOLIOS_CSV} not found — run select_candidate_portfolios.py first")

    goals = pd.read_csv(GOALS_CSV)
    candidates = pd.read_csv(CANDIDATE_PORTFOLIOS_CSV)

    weight_cols = [c for c in candidates.columns if c.endswith("_weight") and not c.startswith("bootstrap")]
    bucket_names = sorted({c.replace("_weight", "") for c in weight_cols})

    print(f"As-of date: {as_of.date()}")
    print(f"Available buckets: {bucket_names}\n")

    mapping_rows = []
    short_horizon_warnings = []

    for _, goal in goals.iterrows():
        name = goal["goal"]
        target_date_str = goal["target_date"]

        if pd.notna(target_date_str) and str(target_date_str).strip():
            target_date = datetime.strptime(str(target_date_str).strip(), "%Y-%m-%d")
            horizon_years = (target_date - as_of).days / 365.25
            date_source = "target_date in goals.csv"
        else:
            horizon_years = DEFAULT_HORIZON_YEARS_IF_NO_DATE.get(name, 7.0)
            date_source = f"no target_date on file — using default assumption of {horizon_years}y"

        bucket, horizon_bucket = assign_bucket(horizon_years, goal.get("flexibility", "low"))
        weight_col = f"{bucket}_weight"

        adjustment_note = "" if bucket == horizon_bucket else f" (bumped from horizon-implied '{horizon_bucket}' — high flexibility)"
        print(f"{name:20s} horizon={horizon_years:5.1f}y ({date_source}) -> bucket: {bucket}{adjustment_note}")

        if horizon_years < 4:
            short_horizon_warnings.append(
                f"  [caution] {name}: {horizon_years:.1f}y horizon mapped to an ALL-EQUITY bucket "
                f"('{bucket}'). Consider whether debt/FD instruments outside this pipeline are more "
                f"appropriate for money needed this soon."
            )

        mapping_rows.append({
            "goal": name, "horizon_years": round(horizon_years, 2),
            "horizon_implied_bucket": horizon_bucket, "bucket_assigned": bucket,
            "flexibility": goal.get("flexibility", ""), "date_confidence": goal.get("date_confidence", ""),
        })

    mapping_df = pd.DataFrame(mapping_rows).set_index("goal")

    # Attach the actual fund weights for each goal's assigned bucket
    detail_rows = []
    for goal_name, row in mapping_df.iterrows():
        bucket = row["bucket_assigned"]
        weight_col = f"{bucket}_weight"
        for _, fund_row in candidates.iterrows():
            w = fund_row[weight_col]
            if w > 0.001:
                detail_rows.append({
                    "goal": goal_name, "bucket": bucket, "isin": fund_row["isin"],
                    "name": fund_row["name"], "category": fund_row["category"], "weight": w,
                })

    detail_df = pd.DataFrame(detail_rows)
    OUTPUT_DIR = ROOT / "output"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mapping_df.to_csv(OUTPUT_DIR / "goal_bucket_assignment.csv")
    detail_df.to_csv(OUTPUT_CSV, index=False, float_format="%.4f")

    print(f"\nWrote {OUTPUT_DIR / 'goal_bucket_assignment.csv'}")
    print(f"Wrote {OUTPUT_CSV}")

    print("\n--- Fund allocation per goal ---")
    for goal_name in mapping_df.index:
        bucket = mapping_df.loc[goal_name, "bucket_assigned"]
        print(f"\n  {goal_name} (bucket: {bucket}):")
        goal_detail = detail_df[detail_df["goal"] == goal_name].sort_values("weight", ascending=False)
        for _, r in goal_detail.iterrows():
            print(f"    {r['name']:55s} {r['weight']*100:5.1f}%")

    if short_horizon_warnings:
        print("\n--- Short-horizon cautions ---")
        for w in short_horizon_warnings:
            print(w)


if __name__ == "__main__":
    main()
