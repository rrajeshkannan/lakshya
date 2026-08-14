"""
Step 10 of the portfolio pipeline: the annual re-run + drift test.

This is the code version of your own annual-review framework (from the pasted
protocol early in this project): re-run the analysis on fresh data every year, then
ask not "did we beat the market" but "does the current architecture still deserve its
seat, or has something changed enough to investigate."

Deliberately narrow scope — this answers ONE question: has the TARGET allocation
itself moved year-over-year (this year's optimal vs last year's optimal), not whether
you've actually rebalanced to match it. That second question — current holdings vs
current target — is what Step 9 (compute_transition.py) already answers. Keeping
these separate mirrors your own mental model: Step 10 is "does the architecture still
deserve its seat," Step 9 is "what would it cost to act on that."

Three outcomes per goal, same three as your own framework:
  🟢 GREEN  — bucket unchanged, no fund's target weight moved more than
              --drift-threshold. Nothing to do. This is the default outcome in a
              healthy year — the annual review should mostly say this.
  🟡 YELLOW — bucket unchanged, but at least one fund's target weight moved beyond
              the threshold (including a fund entering or leaving the target
              entirely, which shows up as a large delta from/to zero). Worth a look,
              not necessarily worth acting on — investigate WHY it moved before
              deciding anything.
  🔴 RED    — the goal's assigned BUCKET itself changed (e.g. horizon crossed a
              threshold, or the frontier shifted enough to change which bucket best
              fits). This is the one that actually warrants rebuilding that goal's
              allocation.

How the year-over-year comparison works: every run of this script saves today's
output/goal_portfolio_mapping.csv into data/snapshots/{date}.csv (never overwritten,
never deleted — you get a full audit trail over the years, in keeping with how
meticulously you already track everything in Lakshya). The NEXT run compares against
whichever snapshot is most recent at that time. On the very first run ever, there's
nothing to compare against — it just establishes the baseline and says so plainly
rather than fabricating a drift result from nothing.

Reads:   output/goal_portfolio_mapping.csv     (this run's target, from Step 8)
         data/snapshots/*.csv                   (prior runs' targets, if any exist)
Writes:  data/snapshots/{today}.csv             (this run's snapshot, for NEXT year)
         output/drift_report.csv                (the Green/Yellow/Red classification
                                                   + fund-level deltas)

Usage:
    python annual_drift_check.py
    python annual_drift_check.py --drift-threshold 0.03   # 3pp instead of default 5pp
    python annual_drift_check.py --as-of 2026-08-13
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
GOAL_MAPPING_CSV = ROOT / "output" / "goal_portfolio_mapping.csv"
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
DRIFT_REPORT_CSV = ROOT / "output" / "drift_report.csv"

DEFAULT_DRIFT_THRESHOLD = 0.05  # 5 percentage points


def find_prior_snapshot(as_of: datetime) -> Path | None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    today_str = as_of.strftime("%Y-%m-%d")
    candidates = sorted(
        [p for p in SNAPSHOTS_DIR.glob("*.csv") if p.stem != today_str],
        reverse=True,
    )
    return candidates[0] if candidates else None


def classify_goal(goal: str, current: pd.DataFrame, prior: pd.DataFrame, threshold: float) -> dict:
    cur_bucket = current["bucket"].iloc[0] if not current.empty else None
    prior_bucket = prior["bucket"].iloc[0] if not prior.empty else None

    cur_weights = current.set_index("isin")["weight"].to_dict()
    prior_weights = prior.set_index("isin")["weight"].to_dict()
    all_isins = set(cur_weights) | set(prior_weights)

    deltas = {isin: cur_weights.get(isin, 0.0) - prior_weights.get(isin, 0.0) for isin in all_isins}
    max_abs_delta = max((abs(d) for d in deltas.values()), default=0.0)
    moved_funds = {isin: d for isin, d in deltas.items() if abs(d) > threshold}

    if prior_bucket is not None and cur_bucket != prior_bucket:
        status = "RED"
        reason = f"bucket changed: '{prior_bucket}' -> '{cur_bucket}'"
    elif moved_funds:
        status = "YELLOW"
        reason = f"{len(moved_funds)} fund(s) moved more than {threshold*100:.0f}pp (max {max_abs_delta*100:.1f}pp)"
    else:
        status = "GREEN"
        reason = f"no fund moved more than {threshold*100:.0f}pp (max observed {max_abs_delta*100:.1f}pp)"

    return {
        "goal": goal, "status": status, "reason": reason,
        "bucket_current": cur_bucket, "bucket_prior": prior_bucket,
        "max_fund_delta_pct": max_abs_delta * 100, "n_funds_moved": len(moved_funds),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare this run's targets against the last saved snapshot.")
    parser.add_argument("--drift-threshold", type=float, default=DEFAULT_DRIFT_THRESHOLD,
                         help=f"Fund weight change (as a fraction) that triggers YELLOW (default {DEFAULT_DRIFT_THRESHOLD})")
    parser.add_argument("--as-of", type=str, default=None, help="Override 'today', format YYYY-MM-DD")
    args = parser.parse_args()
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d") if args.as_of else datetime.now()

    if not GOAL_MAPPING_CSV.exists():
        raise FileNotFoundError(f"{GOAL_MAPPING_CSV} not found — run map_goals_to_portfolios.py first.")

    current = pd.read_csv(GOAL_MAPPING_CSV)
    prior_path = find_prior_snapshot(as_of)

    if prior_path is None:
        print("No prior snapshot found — this is the first run.")
        print("Establishing this run as the baseline. No drift comparison is possible yet;")
        print("that starts from the NEXT annual review, comparing against what gets saved today.\n")
        snapshot_path = SNAPSHOTS_DIR / f"{as_of.strftime('%Y-%m-%d')}.csv"
        current.to_csv(snapshot_path, index=False)
        print(f"Wrote baseline snapshot: {snapshot_path}")
        return

    print(f"Comparing against prior snapshot: {prior_path.name}\n")
    prior = pd.read_csv(prior_path)

    results = []
    for goal in current["goal"].unique():
        cur_g = current[current["goal"] == goal]
        prior_g = prior[prior["goal"] == goal] if goal in prior["goal"].values else pd.DataFrame(columns=current.columns)
        results.append(classify_goal(goal, cur_g, prior_g, args.drift_threshold))

    results_df = pd.DataFrame(results)
    results_df.to_csv(DRIFT_REPORT_CSV, index=False, float_format="%.2f")
    print(f"Wrote {DRIFT_REPORT_CSV}\n")

    icons = {"GREEN": "\U0001F7E2", "YELLOW": "\U0001F7E1", "RED": "\U0001F534"}
    print("--- Annual drift report ---")
    for _, r in results_df.iterrows():
        print(f"  {icons[r['status']]} {r['goal']:20s} {r['status']:6s} — {r['reason']}")

    n_red = (results_df["status"] == "RED").sum()
    n_yellow = (results_df["status"] == "YELLOW").sum()
    n_green = (results_df["status"] == "GREEN").sum()
    print(f"\n{n_green} unchanged, {n_yellow} worth investigating, {n_red} genuinely changed.")
    if n_red > 0:
        print("-> RED goal(s) present: rebuild that goal's allocation (rerun the transition layer for it).")
    elif n_yellow > 0:
        print("-> Only YELLOW: look at what moved before deciding whether to act — don't auto-rebalance on this alone.")
    else:
        print("-> Nothing changed enough to act on. Do nothing, per your own annual-review principle.")

    snapshot_path = SNAPSHOTS_DIR / f"{as_of.strftime('%Y-%m-%d')}.csv"
    current.to_csv(snapshot_path, index=False)
    print(f"\nWrote this run's snapshot for next year: {snapshot_path}")


if __name__ == "__main__":
    main()
