"""
Step 9 of the portfolio pipeline: the tax-aware transition layer.

This formalizes what we did by hand earlier in the project (the FIFO cost-basis +
LTCG/STCG estimate for the original manual REDEEM list) into something repeatable —
because the target allocation now comes from Step 8's goal-mapping, not a one-off
manual decision, and it'll need recomputing every annual review as targets drift.

What it does, per goal:
  1. Aggregate your current holdings (data/current_holdings.csv) by goal, using the
     goal-tag mapping in data/goal_tag_mapping.csv.
  2. Compare against the target weights for that goal's assigned bucket
     (output/goal_portfolio_mapping.csv, from Step 8).
  3. For every fund that needs to shrink, compute FIFO cost basis from the full
     transaction history (data/cashflows_log.csv), classify the gain as long-term or
     short-term (12-month cutoff), and estimate tax:
       - LTCG (equity, >12mo): 12.5% above a Rs 1.25L exemption, per person per FY
       - STCG (equity, <=12mo): 20% flat
     (These are the FY2025-26/26-27 rates per Budget 2024; a rate change in a future
     budget would need updating here — check before trusting a specific number years
     from now.)
  4. Flags ELSS holdings that are still within their 3-year lock-in — these can't be
     sold regardless of what the target says, so they're excluded from sell suggestions
     and reported separately.
  5. Holdings tagged Edu_A are NOT included in any target comparison — see
     data/goal_tag_mapping.csv for why. They're reported separately as
     "pending goal decision."

IMPORTANT — this produces a SUGGESTION for your own judgment, not an instruction to
execute. In particular it does NOT do the FY-boundary-splitting optimization we
discussed manually (spreading large gains across two financial years to use the
exemption twice) — that's a sequencing decision layered on top of this output, not
something this script decides for you.

Reads:   data/current_holdings.csv         (investor, isin, folio, units, value, goal_tag)
         data/goal_tag_mapping.csv          (current_goal_tag -> pipeline_goal)
         data/cashflows_log.csv             (full transaction history, for FIFO cost basis)
         output/goal_portfolio_mapping.csv  (target weights per goal, from Step 8)
         data/funds_universe.csv            (isin -> name, category)
Writes:  output/transition_actions.csv      (one row per investor+fund+goal: current
                                              value, target value, delta, action, tax
                                              estimate where applicable)
         output/transition_edu_a_pending.csv (Edu_A holdings, unmapped, for your own decision)

Usage:
    python compute_transition.py
    python compute_transition.py --as-of 2026-08-13
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
HOLDINGS_CSV = ROOT / "data" / "current_holdings.csv"
GOAL_TAG_MAP_CSV = ROOT / "data" / "goal_tag_mapping.csv"
CASHFLOWS_CSV = ROOT / "data" / "cashflows_log.csv"
GOAL_MAPPING_CSV = ROOT / "output" / "goal_portfolio_mapping.csv"
FUNDS_UNIVERSE_CSV = ROOT / "data" / "funds_universe.csv"
OUTPUT_ACTIONS_CSV = ROOT / "output" / "transition_actions.csv"
OUTPUT_EDU_A_CSV = ROOT / "output" / "transition_edu_a_pending.csv"

LTCG_EXEMPTION_PER_PERSON = 125_000
LTCG_RATE = 0.125
STCG_RATE = 0.20
CESS_RATE = 0.04
LT_CUTOFF_DAYS = 365
ELSS_LOCK_IN_DAYS = 3 * 365
ELSS_ISINS_HINT = ("ELSS", "TAX SAVER")  # matched against fund name, case-insensitive


def fifo_lots(cashflows: pd.DataFrame, investor: str, isin: str, folio: str) -> list[dict]:
    """Replays the transaction history for one (investor, isin, folio) and returns the
    remaining lots (date, units, cost) after netting out any historical redemptions/switches."""
    txns = cashflows[
        (cashflows["investor"] == investor) & (cashflows["isin"] == isin) & (cashflows["folio"] == folio)
    ].sort_values("transaction_date")

    lots: list[dict] = []
    for _, txn in txns.iterrows():
        units = txn["units"]
        if units > 0:
            lots.append({"date": txn["transaction_date"], "units": units, "cost": abs(txn["amount"])})
        elif units < 0:
            remaining = -units
            for lot in lots:
                if remaining <= 1e-6:
                    break
                if lot["units"] <= 1e-9:
                    continue
                take = min(lot["units"], remaining)
                cost_per_unit = lot["cost"] / lot["units"]
                lot["cost"] -= take * cost_per_unit
                lot["units"] -= take
                remaining -= take
            lots = [l for l in lots if l["units"] > 1e-6]
    return lots


def estimate_sale_tax(lots: list[dict], units_to_sell: float, current_value_total: float,
                       current_units_total: float, as_of: datetime) -> dict:
    """Sells `units_to_sell` FIFO from the lots, classifies LT/ST, returns gain breakdown.
    current_value_total/current_units_total are used to price each unit sold at today's NAV."""
    price_per_unit = current_value_total / current_units_total if current_units_total > 0 else 0
    remaining = units_to_sell
    lt_cost = lt_units = st_cost = st_units = 0.0
    for lot in lots:
        if remaining <= 1e-6:
            break
        take = min(lot["units"], remaining)
        cost_per_unit = lot["cost"] / lot["units"] if lot["units"] > 0 else 0
        cost_of_take = take * cost_per_unit
        is_long_term = (as_of - lot["date"]).days > LT_CUTOFF_DAYS
        if is_long_term:
            lt_cost += cost_of_take
            lt_units += take
        else:
            st_cost += cost_of_take
            st_units += take
        remaining -= take

    lt_value = lt_units * price_per_unit
    st_value = st_units * price_per_unit
    return {
        "lt_gain": lt_value - lt_cost, "lt_units": lt_units,
        "st_gain": st_value - st_cost, "st_units": st_units,
        "units_unsold_insufficient_lots": max(remaining, 0.0),
    }


def is_elss(fund_name: str) -> bool:
    name_upper = fund_name.upper()
    return any(hint in name_upper for hint in ELSS_ISINS_HINT)


def earliest_unlocked_units(lots: list[dict], as_of: datetime) -> float:
    """Units whose lot date is old enough to clear the 3-year ELSS lock-in."""
    return sum(lot["units"] for lot in lots if (as_of - lot["date"]).days > ELSS_LOCK_IN_DAYS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a tax-aware buy/sell action list per goal.")
    parser.add_argument("--as-of", type=str, default=None, help="Override 'today', format YYYY-MM-DD")
    args = parser.parse_args()
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d") if args.as_of else datetime.now()

    for path in (HOLDINGS_CSV, GOAL_TAG_MAP_CSV, CASHFLOWS_CSV, GOAL_MAPPING_CSV, FUNDS_UNIVERSE_CSV):
        if not path.exists():
            raise FileNotFoundError(f"{path} not found")

    holdings = pd.read_csv(HOLDINGS_CSV)
    goal_tag_map = pd.read_csv(GOAL_TAG_MAP_CSV).set_index("current_goal_tag")["pipeline_goal"].to_dict()
    cashflows = pd.read_csv(CASHFLOWS_CSV, parse_dates=["transaction_date"])
    goal_targets = pd.read_csv(GOAL_MAPPING_CSV)  # columns: goal, bucket, isin, name, category, weight
    universe = pd.read_csv(FUNDS_UNIVERSE_CSV, dtype=str).set_index("isin")

    holdings["pipeline_goal"] = holdings["goal_tag"].map(goal_tag_map)

    pending = holdings[holdings["pipeline_goal"] == "UNMAPPED"]
    if not pending.empty:
        pending.to_csv(OUTPUT_EDU_A_CSV, index=False)
        print(f"[note] {len(pending)} holdings worth INR {pending['value'].sum():,.0f} are UNMAPPED "
              f"(goal_tag_mapping.csv) — written to {OUTPUT_EDU_A_CSV}, excluded from target comparison.")

    mapped = holdings[holdings["pipeline_goal"] != "UNMAPPED"].copy()

    action_rows = []
    for goal, goal_holdings in mapped.groupby("pipeline_goal"):
        goal_total_value = goal_holdings["value"].sum()
        targets = goal_targets[goal_targets["goal"] == goal].set_index("isin")["weight"].to_dict()

        current_by_fund = goal_holdings.groupby(["investor", "isin"]).agg(
            units=("units", "sum"), value=("value", "sum")
        ).reset_index()

        all_isins = set(current_by_fund["isin"]) | set(targets.keys())
        for isin in all_isins:
            fund_name = universe.loc[isin, "name"] if isin in universe.index else "?"
            target_weight = targets.get(isin, 0.0)
            target_value = goal_total_value * target_weight

            fund_rows = current_by_fund[current_by_fund["isin"] == isin]
            if fund_rows.empty:
                # Fund isn't currently held for this goal but the target wants it: pure BUY.
                action_rows.append({
                    "goal": goal, "investor": "(any / new folio)", "isin": isin, "name": fund_name,
                    "current_value": 0.0, "target_value": target_value, "delta": target_value,
                    "action": "BUY", "lt_gain": None, "st_gain": None, "tax_estimate": None,
                    "elss_locked_units": None, "note": "New position — no existing holding for this goal.",
                })
                continue

            for _, row in fund_rows.iterrows():
                investor, current_value, current_units = row["investor"], row["value"], row["units"]
                # Split the goal-level target proportionally across investors holding this fund
                # for this goal (keeps the per-investor tax picture separate, same as before).
                investor_share = current_value / current_by_fund[current_by_fund["isin"] == isin]["value"].sum()
                investor_target_value = target_value * investor_share
                delta = investor_target_value - current_value

                note = ""
                lt_gain = st_gain = tax_estimate = elss_locked = None

                if delta < -1:  # needs to shrink
                    folios = holdings[
                        (holdings["investor"] == investor) & (holdings["isin"] == isin) &
                        (holdings["pipeline_goal"] == goal)
                    ]["folio"].unique()

                    all_lots = []
                    for folio in folios:
                        all_lots.extend(fifo_lots(cashflows, investor, isin, folio))

                    price_per_unit = current_value / current_units if current_units > 0 else 0
                    units_to_sell = -delta / price_per_unit if price_per_unit > 0 else 0

                    if is_elss(fund_name):
                        unlocked_units = earliest_unlocked_units(all_lots, as_of)
                        elss_locked = max(current_units - unlocked_units, 0.0)
                        if units_to_sell > unlocked_units:
                            note = (f"ELSS lock-in limits sale: only {unlocked_units:.1f} of "
                                    f"{current_units:.1f} units unlocked. ")
                            units_to_sell = min(units_to_sell, unlocked_units)

                    if units_to_sell > 0.01:
                        tax = estimate_sale_tax(all_lots, units_to_sell, current_value, current_units, as_of)
                        lt_gain, st_gain = tax["lt_gain"], tax["st_gain"]
                        if tax["units_unsold_insufficient_lots"] > 0.01:
                            note += (f"[warn] {tax['units_unsold_insufficient_lots']:.1f} units had no "
                                     "matching purchase lot — cost basis may be incomplete. ")

                action_rows.append({
                    "goal": goal, "investor": investor, "isin": isin, "name": fund_name,
                    "current_value": current_value, "target_value": investor_target_value, "delta": delta,
                    "action": "SELL" if delta < -1 else ("BUY" if delta > 1 else "HOLD"),
                    "lt_gain": lt_gain, "st_gain": st_gain, "tax_estimate": None,
                    "elss_locked_units": elss_locked, "note": note,
                })

    actions_df = pd.DataFrame(action_rows)

    # Per-investor LTCG tax estimate: exemption applies per person per FY across ALL their
    # LT gains this run touches, not per fund — so compute it in aggregate, then note each
    # SELL row's own gain alongside the person's overall taxable position.
    print("\n--- Per-investor LTCG exemption usage (this transition run only) ---")
    for investor in actions_df["investor"].dropna().unique():
        if investor == "(any / new folio)":
            continue
        inv_rows = actions_df[(actions_df["investor"] == investor) & (actions_df["action"] == "SELL")]
        total_lt_gain = inv_rows["lt_gain"].fillna(0).sum()
        total_st_gain = inv_rows["st_gain"].fillna(0).sum()
        taxable_lt = max(0, total_lt_gain - LTCG_EXEMPTION_PER_PERSON)
        lt_tax = taxable_lt * LTCG_RATE
        st_tax = total_st_gain * STCG_RATE
        total_tax = (lt_tax + st_tax) * (1 + CESS_RATE)
        print(f"  {investor}: LT gain=INR {total_lt_gain:,.0f}  ST gain=INR {total_st_gain:,.0f}  "
              f"est. tax (incl. cess)=INR {total_tax:,.0f}")

    OUTPUT_ACTIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    actions_df.to_csv(OUTPUT_ACTIONS_CSV, index=False, float_format="%.2f")
    print(f"\nWrote {OUTPUT_ACTIONS_CSV} ({len(actions_df)} rows)")

    print("\n--- Actions by goal ---")
    for goal in actions_df["goal"].unique():
        g = actions_df[actions_df["goal"] == goal]
        print(f"\n  {goal}:")
        for _, r in g.sort_values("delta").iterrows():
            tag = r["action"]
            print(f"    [{tag:4s}] {r['name']:50s} current=INR{r['current_value']:>10,.0f}  "
                  f"target=INR{r['target_value']:>10,.0f}  delta=INR{r['delta']:>10,.0f}  {r['note']}")


if __name__ == "__main__":
    main()
