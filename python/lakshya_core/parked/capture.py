from dataclasses import dataclass

import pandas as pd


MIN_CAPTURE_MONTHS = 12


@dataclass(frozen=True)
class CaptureEvidence:
    upside_capture_pct: float | None
    downside_capture_pct: float | None
    capture_months_used: int


def monthly_last(series: pd.Series) -> pd.Series:
    """
    Last observation per calendar month.

    Reproduces the legacy mf-portfolio-toolkit convention.
    """

    s = series.dropna()

    if s.empty:
        return s

    periods = s.index.to_period("M")
    monthly = s.groupby(periods).last()
    monthly.index = monthly.index.to_timestamp(how="end")

    return monthly


def calculate_capture(
    fund_nav: pd.Series,
    bench_nav: pd.Series,
) -> CaptureEvidence:

    fund_m = monthly_last(fund_nav)
    bench_m = monthly_last(bench_nav)

    fund_ret = fund_m.pct_change().dropna()
    bench_ret = bench_m.pct_change().dropna()

    common = fund_ret.index.intersection(
        bench_ret.index
    )

    if len(common) < MIN_CAPTURE_MONTHS:
        return CaptureEvidence(
            upside_capture_pct=None,
            downside_capture_pct=None,
            capture_months_used=len(common),
        )

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

    return CaptureEvidence(
        upside_capture_pct=upside,
        downside_capture_pct=downside,
        capture_months_used=len(common),
    )
