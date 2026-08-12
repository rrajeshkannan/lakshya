"""
Step 5 of the portfolio pipeline: correlation and covariance matrix across funds.

Why this matters more than any single fund's own metrics: the frontier in Step 6
doesn't just want "good funds" — it wants funds that don't all fall together. Two
funds can each look great individually and still be a bad *pair* if they're 95%
correlated (you're not diversifying, you're just holding the same bet twice, which is
close to what motivated this whole 17-fund consolidation in the first place).

The honest problem with covariance from ~13 years of monthly data across 17 funds:
the raw sample covariance matrix is notoriously noisy — few observations relative to
the number of assets means small changes in the lookback window can swing "optimal"
weights a lot, and the raw matrix can even come out non-positive-semi-definite (which
breaks a mean-variance optimizer outright). This script computes both:
  1. The raw sample covariance/correlation, for reference.
  2. A Ledoit-Wolf shrunk covariance matrix — pulls the raw estimate toward a more
     stable structured target, which is standard practice for exactly this small-
     sample-many-assets situation, and is what Step 6 should actually use.

A second wrinkle: your 17 funds don't all have the same history (Parag Parikh ELSS
only goes back to 2019, others to 2006). Two funds' correlation could technically be
computed over their own pairwise overlap, but doing that inconsistently across the
matrix risks a non-PSD result and mixes different market regimes per pair. Instead,
this script uses the single COMMON window where ALL funds have data for the
shrinkage/frontier-ready matrix, and separately reports the full pairwise-history
correlation as a diagnostic — worth glancing at, not what feeds the optimizer.

Reads:   output/nav_panel.csv
         data/funds_universe.csv        (isin -> name, for readable output)
Writes:  output/correlation_pairwise_full_history.csv   (diagnostic only)
         output/correlation_common_window.csv           (frontier-ready)
         output/covariance_shrunk_annualized.csv        (frontier-ready — USE THIS ONE)
         Prints: which window was used, how many months, shrinkage intensity,
         and a positive-definiteness check on both the raw and shrunk matrices.

Usage:
    python compute_correlation.py
    python compute_correlation.py --min-pairwise-months 36   # diagnostic matrix only
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from pipeline_utils import load_panel, monthly_last

ROOT = Path(__file__).resolve().parent.parent
NAV_PANEL_CSV = ROOT / "output" / "nav_panel.csv"
FUNDS_UNIVERSE_CSV = ROOT / "data" / "funds_universe.csv"
OUTPUT_DIR = ROOT / "output"

MONTHS_PER_YEAR = 12


def load_fund_labels() -> dict[str, str]:
    df = pd.read_csv(FUNDS_UNIVERSE_CSV, dtype=str)
    return dict(zip(df["isin"].str.strip(), df["name"].str.strip()))


def build_monthly_returns(nav_panel: pd.DataFrame) -> pd.DataFrame:
    """One column per fund, monthly simple returns, NaN before a fund's inception."""
    returns = {}
    for isin in nav_panel.columns:
        m = monthly_last(nav_panel[isin])
        returns[isin] = m.pct_change()
    return pd.DataFrame(returns)


def check_positive_semidefinite(cov: np.ndarray, label: str) -> None:
    eigenvalues = np.linalg.eigvalsh(cov)
    min_eig = eigenvalues.min()
    status = "OK (positive semi-definite)" if min_eig >= -1e-10 else "PROBLEM (has negative eigenvalues)"
    print(f"  {label}: min eigenvalue = {min_eig:.6f} -> {status}")


def write_matrix_csv(matrix: pd.DataFrame, path: Path) -> None:
    matrix.to_csv(path, float_format="%.6f")
    print(f"Wrote {path} ({matrix.shape[0]} x {matrix.shape[1]})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute correlation/covariance matrices for the frontier step.")
    parser.add_argument("--min-pairwise-months", type=int, default=36,
                         help="Minimum overlapping months for the diagnostic pairwise correlation (default 36)")
    args = parser.parse_args()

    if not NAV_PANEL_CSV.exists():
        raise FileNotFoundError(f"{NAV_PANEL_CSV} not found — run fetch_data.py first.")

    nav_panel = load_panel(NAV_PANEL_CSV)
    labels = load_fund_labels()
    monthly_returns = build_monthly_returns(nav_panel)

    print(f"Monthly return series: {monthly_returns.shape[0]} months x {monthly_returns.shape[1]} funds")
    for isin in monthly_returns.columns:
        n = monthly_returns[isin].dropna().shape[0]
        print(f"  {isin}  {labels.get(isin, '?'):55s} {n} months of returns")

    # --- Diagnostic: pairwise-history correlation (each pair uses its own overlap) ---
    print(f"\n--- Pairwise-history correlation (diagnostic only, min {args.min_pairwise_months} months overlap) ---")
    pairwise_corr = monthly_returns.corr(min_periods=args.min_pairwise_months)
    n_missing = pairwise_corr.isna().sum().sum()
    if n_missing > 0:
        print(f"  [note] {n_missing} pairs had insufficient overlap and are blank in the output")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_matrix_csv(pairwise_corr, OUTPUT_DIR / "correlation_pairwise_full_history.csv")

    # --- Frontier-ready: common window where ALL funds have data ---
    common = monthly_returns.dropna(how="any")
    n_common = len(common)
    if n_common < 24:
        print(f"\n[warn] only {n_common} months in the common window across all funds — "
              "shrinkage covariance will be built on thin data. Consider dropping the "
              "shortest-history fund(s) from the universe for this step if this feels too thin.")

    start, end = (common.index[0].date(), common.index[-1].date()) if n_common > 0 else (None, None)
    print(f"\n--- Common window across all {monthly_returns.shape[1]} funds: "
          f"{n_common} months, {start} to {end} ---")

    common_corr = common.corr()
    write_matrix_csv(common_corr, OUTPUT_DIR / "correlation_common_window.csv")

    # Persisted so later steps (the frontier, and anything after it) use the exact
    # same aligned monthly returns rather than each recomputing it independently —
    # avoids the two scripts silently drifting apart if nav_panel.csv is refreshed
    # between runs.
    common.to_csv(OUTPUT_DIR / "monthly_returns_common_window.csv", float_format="%.6f")
    print(f"Wrote {OUTPUT_DIR / 'monthly_returns_common_window.csv'} ({common.shape[0]} x {common.shape[1]})")

    # Raw sample covariance (monthly), for the positive-definiteness comparison
    raw_cov_monthly = common.cov().values
    print("\n--- Positive-definiteness check ---")
    check_positive_semidefinite(raw_cov_monthly, "Raw sample covariance   ")

    # Ledoit-Wolf shrinkage — pulls the noisy sample estimate toward a stable target.
    # This is what Step 6 (the frontier) should actually consume.
    lw = LedoitWolf().fit(common.values)
    shrunk_cov_monthly = lw.covariance_
    check_positive_semidefinite(shrunk_cov_monthly, "Ledoit-Wolf shrunk cov  ")
    print(f"  Shrinkage intensity (0=no shrinkage, 1=fully toward target): {lw.shrinkage_:.4f}")

    shrunk_cov_annual = pd.DataFrame(
        shrunk_cov_monthly * MONTHS_PER_YEAR, index=common.columns, columns=common.columns
    )
    write_matrix_csv(shrunk_cov_annual, OUTPUT_DIR / "covariance_shrunk_annualized.csv")

    print("\nUse output/covariance_shrunk_annualized.csv as the frontier's covariance input.")
    print("output/correlation_pairwise_full_history.csv is for your own eyeballing only —")
    print("not internally consistent enough (mixed windows per pair) to feed an optimizer.")


if __name__ == "__main__":
    main()
