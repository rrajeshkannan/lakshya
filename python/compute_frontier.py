"""
Step 6 of the portfolio pipeline: the efficient frontier.

Standard mean-variance optimization (Markowitz), long-only, with two constraint knobs
you actually care about (no fund becomes 80% of the portfolio just because it has the
best historical Sharpe — that's overfitting to one sample, not diversification):
  --max-weight           cap on any single fund
  --max-category-weight  cap on any single category (Small Cap, Flexi Cap, etc.)

Two anchor portfolios, plus the curve between them:
  - Global Minimum Variance (GMV): lowest possible volatility, whatever return that implies.
  - Max Sharpe (tangency portfolio): best return per unit of risk, given --risk-free-rate.
  - The frontier itself: minimum-variance portfolio for a range of target returns
    between those two.

The honest caveat, made concrete rather than just mentioned: with only 85 months of
common-window data across 17 funds, "the optimal portfolio" from a single historical
sample is itself uncertain — a slightly different sample could point somewhere else.
So this script also bootstraps the Max Sharpe portfolio: resample the monthly returns
(with replacement) N times, re-shrink the covariance and re-solve each time, and report
how STABLE each fund's weight is across those resamples. A fund that gets a real weight
in 95% of resamples is a robust pick. A fund that flips between 0% and 20% depending on
which months got resampled is telling you the "optimal" weight is mostly noise — that's
your answer to "how many can be weeded out immediately."

Reads:   output/covariance_shrunk_annualized.csv    (from compute_correlation.py)
         output/monthly_returns_common_window.csv    (from compute_correlation.py)
         data/funds_universe.csv                      (isin -> name, category)
Writes:  output/frontier_points.csv           (target_return, volatility, sharpe, weights)
         output/frontier_key_portfolios.csv   (GMV and Max Sharpe rows, full detail)
         output/frontier_bootstrap_stability.csv   (per-fund weight stability across resamples)

Usage:
    python compute_frontier.py
    python compute_frontier.py --max-weight 0.25 --max-category-weight 0.40
    python compute_frontier.py --n-frontier-points 30 --n-bootstrap 200
    python compute_frontier.py --risk-free-rate 0.065
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

ROOT = Path(__file__).resolve().parent.parent
COV_CSV = ROOT / "output" / "covariance_shrunk_annualized.csv"
RETURNS_CSV = ROOT / "output" / "monthly_returns_common_window.csv"
FUNDS_UNIVERSE_CSV = ROOT / "data" / "funds_universe.csv"
OUTPUT_DIR = ROOT / "output"

MONTHS_PER_YEAR = 12


# --- loading --------------------------------------------------------------------

def load_universe() -> pd.DataFrame:
    return pd.read_csv(FUNDS_UNIVERSE_CSV, dtype=str)


def annualized_geometric_return(monthly_returns: pd.DataFrame) -> pd.Series:
    """Compounded annualized return per fund, over the same window the covariance uses —
    deliberately NOT each fund's own full-history CAGR, to stay period-consistent with
    the covariance matrix rather than mixing a long window for returns with a short
    window for risk."""
    n_months = len(monthly_returns)
    compounded = (1 + monthly_returns).prod()
    return compounded ** (MONTHS_PER_YEAR / n_months) - 1


# --- portfolio math ---------------------------------------------------------------

def port_return(w: np.ndarray, mu: np.ndarray) -> float:
    return float(w @ mu)


def port_vol(w: np.ndarray, cov: np.ndarray) -> float:
    variance = float(w @ cov @ w)
    return np.sqrt(max(variance, 0.0))


def neg_sharpe(w: np.ndarray, mu: np.ndarray, cov: np.ndarray, rf: float) -> float:
    v = port_vol(w, cov)
    if v <= 1e-12:
        return 1e6
    return -(port_return(w, mu) - rf) / v


def build_constraints(n: int, mu: np.ndarray, category_groups: dict[str, list[int]],
                       max_category_weight: float | None, target_return: float | None):
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    if target_return is not None:
        cons.append({"type": "eq", "fun": lambda w, tr=target_return: w @ mu - tr})
    if max_category_weight is not None:
        for cat, idx in category_groups.items():
            cons.append({
                "type": "ineq",
                "fun": lambda w, idx=idx, cap=max_category_weight: cap - np.sum(w[idx]),
            })
    return cons


def solve_min_variance(mu: np.ndarray, cov: np.ndarray, category_groups: dict[str, list[int]],
                        max_weight: float, max_category_weight: float | None,
                        target_return: float | None) -> dict | None:
    n = len(mu)
    bounds = [(0.0, max_weight)] * n
    cons = build_constraints(n, mu, category_groups, max_category_weight, target_return)
    x0 = np.full(n, 1.0 / n)

    result = minimize(port_vol, x0, args=(cov,), method="SLSQP", bounds=bounds,
                       constraints=cons, options={"maxiter": 500, "ftol": 1e-10})
    if not result.success:
        return None
    w = result.x
    return {"weights": w, "return": port_return(w, mu), "vol": port_vol(w, cov)}


def solve_max_sharpe(mu: np.ndarray, cov: np.ndarray, category_groups: dict[str, list[int]],
                      max_weight: float, max_category_weight: float | None, rf: float) -> dict | None:
    n = len(mu)
    bounds = [(0.0, max_weight)] * n
    cons = build_constraints(n, mu, category_groups, max_category_weight, target_return=None)
    x0 = np.full(n, 1.0 / n)

    result = minimize(neg_sharpe, x0, args=(mu, cov, rf), method="SLSQP", bounds=bounds,
                       constraints=cons, options={"maxiter": 500, "ftol": 1e-10})
    if not result.success:
        return None
    w = result.x
    r, v = port_return(w, mu), port_vol(w, cov)
    return {"weights": w, "return": r, "vol": v, "sharpe": (r - rf) / v if v > 0 else None}


# --- frontier ----------------------------------------------------------------------

def build_frontier(mu: np.ndarray, cov: np.ndarray, category_groups: dict[str, list[int]],
                    max_weight: float, max_category_weight: float | None,
                    gmv_return: float, n_points: int) -> list[dict]:
    max_single_return = float(mu.max())
    targets = np.linspace(gmv_return, max_single_return, n_points)
    points = []
    for target in targets:
        res = solve_min_variance(mu, cov, category_groups, max_weight, max_category_weight, target)
        if res is not None:
            points.append(res)
    return points


# --- bootstrap robustness check for the Max Sharpe portfolio -----------------------

def bootstrap_max_sharpe(monthly_returns: pd.DataFrame, category_groups: dict[str, list[int]],
                          max_weight: float, max_category_weight: float | None, rf: float,
                          n_bootstrap: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    isins = monthly_returns.columns.tolist()
    n_months = len(monthly_returns)
    values = monthly_returns.values

    weight_samples = []
    n_failed = 0
    for i in range(n_bootstrap):
        sample_idx = rng.integers(0, n_months, size=n_months)  # resample months with replacement
        sample = values[sample_idx, :]

        mu_boot = (1 + pd.DataFrame(sample)).prod().values ** (MONTHS_PER_YEAR / n_months) - 1
        cov_boot = LedoitWolf().fit(sample).covariance_ * MONTHS_PER_YEAR

        res = solve_max_sharpe(mu_boot, cov_boot, category_groups, max_weight, max_category_weight, rf)
        if res is None:
            n_failed += 1
            continue
        weight_samples.append(res["weights"])

    if n_failed > 0:
        print(f"  [note] {n_failed}/{n_bootstrap} bootstrap resamples failed to converge, excluded")

    W = np.array(weight_samples)  # shape: (n_successful, n_funds)
    stability = pd.DataFrame({
        "isin": isins,
        "mean_weight": W.mean(axis=0),
        "std_weight": W.std(axis=0),
        "min_weight": W.min(axis=0),
        "max_weight": W.max(axis=0),
        "pct_samples_weight_gt_1pct": (W > 0.01).mean(axis=0),
    })
    return stability.set_index("isin")


# --- orchestration -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build the efficient frontier from the shrunk covariance matrix.")
    parser.add_argument("--max-weight", type=float, default=0.30, help="Max weight for any single fund (default 0.30)")
    parser.add_argument("--max-category-weight", type=float, default=0.45,
                         help="Max combined weight for any single category (default 0.45)")
    parser.add_argument("--risk-free-rate", type=float, default=0.065,
                         help="Annual risk-free rate for Sharpe ratio (default 0.065)")
    parser.add_argument("--n-frontier-points", type=int, default=25, help="Number of points along the frontier")
    parser.add_argument("--n-bootstrap", type=int, default=200, help="Number of bootstrap resamples for stability check")
    parser.add_argument("--no-bootstrap", action="store_true", help="Skip the bootstrap stability check (faster)")
    args = parser.parse_args()

    if not COV_CSV.exists() or not RETURNS_CSV.exists():
        raise FileNotFoundError("Missing output/covariance_shrunk_annualized.csv or "
                                 "output/monthly_returns_common_window.csv — run compute_correlation.py first.")

    cov_df = pd.read_csv(COV_CSV, index_col=0)
    monthly_returns = pd.read_csv(RETURNS_CSV, index_col=0, parse_dates=True)
    universe = load_universe().set_index("isin")

    isins = cov_df.columns.tolist()
    assert list(monthly_returns.columns) == isins, "covariance and returns files are out of sync — rerun compute_correlation.py"

    mu_series = annualized_geometric_return(monthly_returns)
    mu = mu_series.reindex(isins).values
    cov = cov_df.values

    category_groups: dict[str, list[int]] = {}
    for i, isin in enumerate(isins):
        cat = universe.loc[isin, "category"] if isin in universe.index else "Unknown"
        category_groups.setdefault(cat, []).append(i)

    print(f"{len(isins)} funds, {len(category_groups)} categories, "
          f"max_weight={args.max_weight}, max_category_weight={args.max_category_weight}\n")
    print("Annualized expected return per fund (common-window, geometric):")
    for isin, r in mu_series.reindex(isins).items():
        print(f"  {isin}  {universe.loc[isin, 'name'] if isin in universe.index else '?':55s} {r*100:6.2f}%")

    # --- GMV ---
    gmv = solve_min_variance(mu, cov, category_groups, args.max_weight, args.max_category_weight, target_return=None)
    if gmv is None:
        raise RuntimeError("GMV optimization failed to converge — try relaxing --max-weight/--max-category-weight")
    print(f"\nGlobal Minimum Variance: return={gmv['return']*100:.2f}%  vol={gmv['vol']*100:.2f}%")

    # --- Max Sharpe ---
    max_sharpe = solve_max_sharpe(mu, cov, category_groups, args.max_weight, args.max_category_weight, args.risk_free_rate)
    if max_sharpe is None:
        raise RuntimeError("Max Sharpe optimization failed to converge")
    print(f"Max Sharpe:              return={max_sharpe['return']*100:.2f}%  vol={max_sharpe['vol']*100:.2f}%  "
          f"sharpe={max_sharpe['sharpe']:.3f}")

    # --- frontier curve ---
    frontier = build_frontier(mu, cov, category_groups, args.max_weight, args.max_category_weight,
                               gmv["return"], args.n_frontier_points)
    print(f"\nFrontier: {len(frontier)}/{args.n_frontier_points} target points converged")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    frontier_rows = []
    for pt in frontier:
        row = {"target_return_pct": pt["return"] * 100, "volatility_pct": pt["vol"] * 100,
               "sharpe": (pt["return"] - args.risk_free_rate) / pt["vol"] if pt["vol"] > 0 else None}
        for isin, w in zip(isins, pt["weights"]):
            row[isin] = w
        frontier_rows.append(row)
    pd.DataFrame(frontier_rows).to_csv(OUTPUT_DIR / "frontier_points.csv", index=False, float_format="%.6f")
    print(f"Wrote {OUTPUT_DIR / 'frontier_points.csv'}")

    key_rows = []
    for label, pt in [("Global Minimum Variance", gmv), ("Max Sharpe", max_sharpe)]:
        row = {"portfolio": label, "return_pct": pt["return"] * 100, "volatility_pct": pt["vol"] * 100,
               "sharpe": pt.get("sharpe", (pt["return"] - args.risk_free_rate) / pt["vol"] if pt["vol"] > 0 else None)}
        for isin, w in zip(isins, pt["weights"]):
            row[isin] = w
        key_rows.append(row)
    pd.DataFrame(key_rows).to_csv(OUTPUT_DIR / "frontier_key_portfolios.csv", index=False, float_format="%.6f")
    print(f"Wrote {OUTPUT_DIR / 'frontier_key_portfolios.csv'}")

    # --- bootstrap stability ---
    if not args.no_bootstrap:
        print(f"\nRunning {args.n_bootstrap} bootstrap resamples of the Max Sharpe portfolio "
              "(re-shrinking covariance each time — this takes a bit)...")
        stability = bootstrap_max_sharpe(monthly_returns, category_groups, args.max_weight,
                                          args.max_category_weight, args.risk_free_rate, args.n_bootstrap)
        stability["name"] = [universe.loc[i, "name"] if i in universe.index else "?" for i in stability.index]
        stability["category"] = [universe.loc[i, "category"] if i in universe.index else "?" for i in stability.index]
        stability = stability[["name", "category", "mean_weight", "std_weight", "min_weight",
                                "max_weight", "pct_samples_weight_gt_1pct"]]
        stability = stability.sort_values("mean_weight", ascending=False)
        stability.to_csv(OUTPUT_DIR / "frontier_bootstrap_stability.csv", float_format="%.4f")
        print(f"Wrote {OUTPUT_DIR / 'frontier_bootstrap_stability.csv'}")

        print("\n--- Bootstrap stability (Max Sharpe portfolio, sorted by mean weight) ---")
        print("A fund with high mean_weight AND high pct_samples_weight_gt_1pct is a robust pick.")
        print("A fund with high std_weight relative to its mean is sensitive to sampling noise.\n")
        for isin, row in stability.iterrows():
            print(f"  {isin}  {row['name']:50s} mean={row['mean_weight']*100:5.1f}%  "
                  f"std={row['std_weight']*100:5.1f}%  in {row['pct_samples_weight_gt_1pct']*100:5.1f}% of samples")


if __name__ == "__main__":
    main()
