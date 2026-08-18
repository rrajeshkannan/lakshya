from dataclasses import dataclass

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
    """

    df = df.sort_values("date").copy()
    df = df.drop_duplicates(subset=["date"])

    dates = df["date"].reset_index(drop=True)
    navs = df["nav"].reset_index(drop=True)

    results = []

    start_idx = 0

    for i in range(len(df)):
        end_date = dates.iloc[i]
        target_start = end_date - pd.DateOffset(years=years)

        while (
            start_idx + 1 < len(df)
            and dates.iloc[start_idx + 1] <= target_start
        ):
            start_idx += 1

        if dates.iloc[start_idx] > target_start:
            continue

        start_nav = float(navs.iloc[start_idx])
        end_nav = float(navs.iloc[i])

        if start_nav <= 0:
            continue

        cagr = (end_nav / start_nav) ** (1 / years) - 1

        results.append(cagr)

    if not results:
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
