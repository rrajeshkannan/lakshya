"""
Step 4 of the portfolio pipeline: the metrics engine.

Turns "acceptable downside, quick recovery" from a judgment call into numbers, per fund:
  - Rolling CAGR at 3/5/7/10Y windows (not just one trailing figure — the full
    distribution across entry points, so you can see how consistent it's been rather
    than just how it did from today looking back).
  - Max drawdown, and how long it took to fall and to recover.
  - Downside deviation (volatility of only the bad days) and Sortino ratio.
  - Upside/downside capture ratio against the fund's category benchmark — this is what
    actually answers "did the extra return come with proportionate extra pain".

Reads:   output/nav_panel.csv                (from fetch_data.py)
         data/benchmarks_consolidated.csv     (your hand-maintained TRI file)
         data/funds_universe.csv              (isin -> category)
         data/benchmark_universe.csv          (category -> benchmark index name)
Writes:  output/fund_metrics.csv              (one row per fund, ~30 metric columns)

Usage:
    python compute_metrics.py
    python compute_metrics.py --risk-free-rate 0.065   # override the Sortino assumption

Assumptions worth knowing about:
  - RISK_FREE_RATE_ANNUAL below is a placeholder (India ~6.5%, roughly 10Y G-Sec /
    bank FD territory). It only affects the Sortino ratio. Override with --risk-free-rate
    if you have a better number, or track the actual G-Sec yield over time later.
  - A rolling N-year window is only computed where N years of history actually exist —
    a fund with 6 years of data gets 3Y and 5Y rolling stats but not 7Y or 10Y (blank,
    not a fabricated/extrapolated number).
  - Capture ratios need at least MIN_CAPTURE_MONTHS of overlapping fund+benchmark
    monthly data; below that, they're left blank rather than computed on too little
    evidence to mean anything.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NAV_PANEL_CSV = ROOT / "output" / "nav_panel.csv"
BENCHMARKS_CSV = ROOT / "data" / "benchmarks_consolidated.csv"
FUNDS_UNIVERSE_CSV = ROOT / "data" / "funds_universe.csv"
BENCHMARK_UNIVERSE_CSV = ROOT / "data" / "benchmark_universe.csv"
OUTPUT_CSV = ROOT / "output" / "fund_metrics.csv"

ROLLING_WINDOWS_YEARS = [3, 5, 7, 10]
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE_ANNUAL_DEFAULT = 0.065
MIN_CAPTURE_MONTHS = 12


# --- loading ------------------------------------------------------------------

def load_panel(path: Path) -> pd.DataFrame:
    """Loads a wide dates x series CSV. Date column name varies by source
    (nav_panel.csv uses 'date', benchmarks_consolidated.csv uses 'Date'), so
    match case-insensitively rather than assume one or the other."""
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if c.strip().lower() == "date"), None)
    if date_col is None:
        raise ValueError(f"{path.name}: no 'date' column found (got columns: {list(df.columns)})")
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    df.index.name = "date"
    return df


def load_universe() -> pd.DataFrame:
    return pd.read_csv(FUNDS_UNIVERSE_CSV, dtype=str)


def load_benchmark_map() -> dict[str, str]:
    df = pd.read_csv(BENCHMARK_UNIVERSE_CSV, dtype=str)
    return dict(zip(df["category"].str.strip(), df["benchmark_index_name"].str.strip()))


def normalize_index_name(name: str) -> str:
    return " ".join(name.strip().upper().split())


# --- per-series metric computations --------------------------------------------

def rolling_cagr(nav: pd.Series, years: int) -> pd.Series:
    """CAGR ending at each date, looking back `years` years, wherever that lookback exists."""
    nav = nav.dropna()
    if nav.empty:
        return pd.Series(dtype=float)
    offset = pd.DateOffset(years=years)
    earliest = nav.index[0]
    out = {}
    for date, value in nav.items():
        start_date = date - offset
        if start_date < earliest or value <= 0:
            continue
        start_value = nav.asof(start_date)
        if pd.isna(start_value) or start_value <= 0:
            continue
        out[date] = (value / start_value) ** (1 / years) - 1
    return pd.Series(out, dtype=float)


def rolling_summary(series: pd.Series) -> dict[str, float | None]:
    if series.empty:
        return {"mean": None, "median": None, "std": None, "min": None, "max": None,
                "pct_positive": None, "latest": None}
    return {
        "mean": series.mean(),
        "median": series.median(),
        "std": series.std(),
        "min": series.min(),
        "max": series.max(),
        "pct_positive": float((series > 0).mean()),
        "latest": series.iloc[-1],
    }


def max_drawdown_and_recovery(nav: pd.Series) -> dict:
    nav = nav.dropna()
    if len(nav) < 2:
        return {"mdd_pct": None, "peak_date": None, "trough_date": None, "recovery_date": None,
                "decline_days": None, "recovery_days": None, "recovered": None}

    running_max = nav.cummax()
    drawdown = nav / running_max - 1
    trough_date = drawdown.idxmin()
    mdd = drawdown.loc[trough_date]
    peak_date = nav.loc[:trough_date].idxmax()
    peak_value = nav.loc[peak_date]

    after_trough = nav.loc[trough_date:]
    recovered_mask = after_trough >= peak_value
    recovery_date = after_trough.index[recovered_mask][0] if recovered_mask.any() else None

    return {
        "mdd_pct": mdd * 100,
        "peak_date": peak_date.date().isoformat(),
        "trough_date": trough_date.date().isoformat(),
        "recovery_date": recovery_date.date().isoformat() if recovery_date is not None else None,
        "decline_days": (trough_date - peak_date).days,
        "recovery_days": (recovery_date - trough_date).days if recovery_date is not None else None,
        "recovered": recovery_date is not None,
    }


def downside_deviation_annual(daily_returns: pd.Series) -> float | None:
    downside = daily_returns[daily_returns < 0]
    if downside.empty:
        return 0.0
    return float(np.sqrt((downside ** 2).mean()) * np.sqrt(TRADING_DAYS_PER_YEAR))


def full_period_cagr(nav: pd.Series) -> float | None:
    nav = nav.dropna()
    if len(nav) < 2:
        return None
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    if years <= 0 or nav.iloc[0] <= 0:
        return None
    return (nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1


def monthly_last(series: pd.Series) -> pd.Series:
    """Last observation per calendar month — implemented via groupby rather than
    .resample('M'/'ME') to sidestep pandas version differences in the resample alias."""
    s = series.dropna()
    if s.empty:
        return s
    periods = s.index.to_period("M")
    monthly = s.groupby(periods).last()
    monthly.index = monthly.index.to_timestamp(how="end")
    return monthly


def capture_ratios(fund_nav: pd.Series, bench_nav: pd.Series) -> dict:
    fund_m = monthly_last(fund_nav)
    bench_m = monthly_last(bench_nav)
    fund_ret = fund_m.pct_change().dropna()
    bench_ret = bench_m.pct_change().dropna()

    common = fund_ret.index.intersection(bench_ret.index)
    if len(common) < MIN_CAPTURE_MONTHS:
        return {"upside_capture_pct": None, "downside_capture_pct": None, "capture_months_used": len(common)}

    f = fund_ret.loc[common]
    b = bench_ret.loc[common]
    up_mask = b > 0
    down_mask = b < 0

    upside = None
    if up_mask.sum() > 0:
        f_up = (1 + f[up_mask]).prod() - 1
        b_up = (1 + b[up_mask]).prod() - 1
        if b_up != 0:
            upside = f_up / b_up * 100

    downside = None
    if down_mask.sum() > 0:
        f_down = (1 + f[down_mask]).prod() - 1
        b_down = (1 + b[down_mask]).prod() - 1
        if b_down != 0:
            downside = f_down / b_down * 100

    return {"upside_capture_pct": upside, "downside_capture_pct": downside, "capture_months_used": len(common)}


# --- orchestration --------------------------------------------------------------

def compute_fund_metrics(isin: str, name: str, category: str, nav: pd.Series,
                          bench_nav: pd.Series | None, bench_name: str | None,
                          risk_free_rate: float) -> dict:
    row: dict = {"isin": isin, "name": name, "category": category, "benchmark_index": bench_name or ""}

    nav_clean = nav.dropna()
    if nav_clean.empty:
        row["track_record_years"] = 0
        return row

    track_years = (nav_clean.index[-1] - nav_clean.index[0]).days / 365.25
    row["track_record_years"] = round(track_years, 2)

    for years in ROLLING_WINDOWS_YEARS:
        prefix = f"roll_{years}y_"
        if track_years < years:
            for stat in ("mean", "median", "std", "min", "max", "pct_positive", "latest"):
                row[prefix + stat] = None
            continue
        series = rolling_cagr(nav_clean, years)
        summary = rolling_summary(series)
        for stat, value in summary.items():
            row[prefix + stat] = value * 100 if (value is not None and stat != "pct_positive") else \
                (value * 100 if value is not None else None)

    dd = max_drawdown_and_recovery(nav_clean)
    row.update({f"mdd_{k}": v for k, v in dd.items()})

    daily_returns = nav_clean.pct_change().dropna()
    ddev = downside_deviation_annual(daily_returns)
    row["downside_deviation_annual_pct"] = ddev * 100 if ddev is not None else None

    cagr_full = full_period_cagr(nav_clean)
    row["full_period_cagr_pct"] = cagr_full * 100 if cagr_full is not None else None
    if cagr_full is not None and ddev is not None and ddev > 0:
        row["sortino_ratio"] = (cagr_full - risk_free_rate) / ddev
    else:
        row["sortino_ratio"] = None

    if bench_nav is not None:
        row.update(capture_ratios(nav_clean, bench_nav.dropna()))
    else:
        row.update({"upside_capture_pct": None, "downside_capture_pct": None, "capture_months_used": None})

    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute fund metrics: rolling returns, drawdown, capture ratios.")
    parser.add_argument("--risk-free-rate", type=float, default=RISK_FREE_RATE_ANNUAL_DEFAULT,
                         help=f"Annual risk-free rate used only for Sortino ratio (default {RISK_FREE_RATE_ANNUAL_DEFAULT})")
    args = parser.parse_args()

    if not NAV_PANEL_CSV.exists():
        raise FileNotFoundError(f"{NAV_PANEL_CSV} not found — run fetch_data.py first.")
    if not BENCHMARKS_CSV.exists():
        raise FileNotFoundError(f"{BENCHMARKS_CSV} not found — see README for the manual download workflow.")

    nav_panel = load_panel(NAV_PANEL_CSV)
    benchmarks = load_panel(BENCHMARKS_CSV)
    benchmarks.columns = [normalize_index_name(c) for c in benchmarks.columns]

    universe = load_universe()
    benchmark_map = load_benchmark_map()

    rows = []
    for _, fund in universe.iterrows():
        isin = fund["isin"].strip()
        name = fund["name"].strip()
        category = fund["category"].strip()

        if isin not in nav_panel.columns:
            print(f"  [warn] {isin} ({name}): not present in nav_panel.csv, skipping")
            continue

        bench_index_name = benchmark_map.get(category)
        bench_nav = None
        bench_key = None
        if bench_index_name:
            bench_key = normalize_index_name(bench_index_name)
            if bench_key in benchmarks.columns:
                bench_nav = benchmarks[bench_key]
            else:
                print(f"  [warn] {isin} ({name}): benchmark '{bench_index_name}' not found in "
                      f"{BENCHMARKS_CSV.name}, capture ratios will be blank")

        row = compute_fund_metrics(
            isin, name, category, nav_panel[isin], bench_nav, bench_index_name, args.risk_free_rate
        )
        rows.append(row)
        print(f"[done] {isin} ({name}): {row['track_record_years']}y track record, "
              f"MDD {row.get('mdd_mdd_pct')}")

    if not rows:
        print("No funds processed — nothing to write.")
        return

    fieldnames = list(rows[0].keys())
    for r in rows[1:]:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ("" if v is None else v) for k, v in r.items()})

    print(f"\nWrote {OUTPUT_CSV} ({len(rows)} funds)")


if __name__ == "__main__":
    main()
