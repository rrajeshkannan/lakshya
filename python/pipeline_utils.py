"""
Shared helpers used by more than one pipeline script (compute_metrics.py,
compute_correlation.py, and later steps). Kept small and dependency-light —
this is glue, not a framework.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_panel(path: Path) -> pd.DataFrame:
    """
    Loads a wide dates x series CSV into a DataFrame indexed by date.
    Date column name varies by source (nav_panel.csv uses 'date',
    benchmarks_consolidated.csv uses 'Date'), so match case-insensitively
    rather than assume one or the other.
    """
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if c.strip().lower() == "date"), None)
    if date_col is None:
        raise ValueError(f"{path.name}: no 'date' column found (got columns: {list(df.columns)})")
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    df.index.name = "date"
    return df


def normalize_index_name(name: str) -> str:
    """Case/whitespace-insensitive key so 'Nifty 500 ' and 'NIFTY  500' match."""
    return " ".join(name.strip().upper().split())


def monthly_last(series: pd.Series) -> pd.Series:
    """
    Last observation per calendar month — implemented via groupby rather than
    .resample('M'/'ME') to sidestep pandas version differences in the resample
    alias (deprecated 'M' vs newer 'ME' across pandas releases).
    """
    s = series.dropna()
    if s.empty:
        return s
    periods = s.index.to_period("M")
    monthly = s.groupby(periods).last()
    monthly.index = monthly.index.to_timestamp(how="end")
    return monthly
