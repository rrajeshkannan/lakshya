from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RollingReturnEvidence:
    years: int
    observations: int

    minimum: float
    percentile_25: float
    median: float
    percentile_75: float
    maximum: float

    mean: float
    standard_deviation: float

    positive_periods: int
    negative_periods: int
    positive_period_pct: float

    latest: float


def calculate_rolling_cagr(
    df: pd.DataFrame,
    years: int,
) -> RollingReturnEvidence:
    """
    Calculate rolling CAGR using the inherited toolkit convention:

    CAGR = (ending NAV / starting NAV) ** (1 / years) - 1

    The starting NAV is the latest available NAV on or before
    the requested lookback date.

    [lakshya] The ordered NAV history is searched as arrays rather than
    through per-observation pandas scalar indexing. This preserves the
    exact lookback rule while avoiding millions of Python/pandas calls at
    TEAM scale.
    """

    df = df.sort_values("date").copy()
    df = df.drop_duplicates(subset=["date"])

    dates = df["date"].reset_index(drop=True)
    navs = df["nav"].reset_index(drop=True)

    if len(df) == 0:
        raise ValueError(
            f"Insufficient history for {years}-year rolling returns"
        )

    # [lakshya] DateOffset subtraction retains the existing calendar-year
    # semantics (including leap-day handling). searchsorted then finds the
    # rightmost observation on or before each target date, exactly matching
    # the previous monotonic start-index walk.
    target_starts = dates - pd.DateOffset(years=years)
    date_values = dates.to_numpy(dtype="datetime64[ns]")
    target_values = target_starts.to_numpy(dtype="datetime64[ns]")
    start_indices = np.searchsorted(
        date_values,
        target_values,
        side="right",
    ) - 1

    valid = start_indices >= 0
    if not valid.any():
        raise ValueError(
            f"Insufficient history for {years}-year rolling returns"
        )

    end_indices = np.flatnonzero(valid)
    start_indices = start_indices[valid]
    start_navs = navs.to_numpy(dtype=float)[start_indices]
    end_navs = navs.to_numpy(dtype=float)[end_indices]

    valid_navs = start_navs > 0
    if not valid_navs.any():
        raise ValueError(
            f"Insufficient history for {years}-year rolling returns"
        )

    results = (end_navs[valid_navs] / start_navs[valid_navs]) ** (1 / years) - 1

    if len(results) == 0:
        raise ValueError(
            f"Insufficient history for {years}-year rolling returns"
        )

    series = pd.Series(results)

    positive_periods = int((series > 0).sum())
    negative_periods = int((series < 0).sum())

    return RollingReturnEvidence(
        years=years,
        observations=len(series),

        minimum=float(series.min()),
        percentile_25=float(series.quantile(0.25)),
        median=float(series.median()),
        percentile_75=float(series.quantile(0.75)),
        maximum=float(series.max()),

        mean=float(series.mean()),
        standard_deviation=float(series.std()),

        positive_periods=positive_periods,
        negative_periods=negative_periods,
        positive_period_pct=float(
            (positive_periods / len(series)) * 100
        ),

        latest=float(series.iloc[-1]),
    )
