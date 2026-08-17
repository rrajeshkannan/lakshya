from dataclasses import dataclass

import pandas as pd

from lakshya_core.evidence_inventory import load_nav_cache


@dataclass(frozen=True)
class DownsideEvidence:
    negative_observations: int
    downside_rms_daily: float
    downside_rms_annualized: float


def calculate_downside_deviation(
    df: pd.DataFrame,
) -> DownsideEvidence:
    """
    Reproduce the inherited toolkit's downside-deviation concept.

    Daily returns below zero are isolated and their dispersion is
    annualized using sqrt(252).
    """

    df = df.sort_values("date").copy()

    returns = df["nav"].pct_change().dropna()

    negative_returns = returns[returns < 0]

    if negative_returns.empty:
        return DownsideEvidence(
            negative_observations=0,
            downside_rms_daily=0.0,
            downside_rms_annualized=0.0,
        )

    downside_daily = float(
        (negative_returns.pow(2).mean()) ** 0.5
    )

    downside_annualized = downside_daily * (252 ** 0.5)

    return DownsideEvidence(
        negative_observations=len(negative_returns),
        downside_rms_daily=downside_daily,
        downside_rms_annualized=downside_annualized,
    )


if __name__ == "__main__":
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]

    path = (
        project_root
        / "data"
        / "cache"
        # / "INF174K01KT2_nav.json"
        # / "INF109K01BL4_nav.json"
        / "INF179K01608_nav.json"
    )

    df = load_nav_cache(path)

    evidence = calculate_downside_deviation(df)

    print(evidence)
