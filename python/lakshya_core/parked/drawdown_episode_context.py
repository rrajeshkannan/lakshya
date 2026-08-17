from pathlib import Path

import pandas as pd

from drawdown_episodes import identify_drawdown_episodes
from drawdown_severity import (
    calculate_drawdown_severity,
    load_fund_nav,
)


def severity_percentile(
    severity: float,
    distribution: pd.Series,
) -> float:
    """
    Return the percentage of observed severity values
    less than or equal to the supplied severity.

    Severity is expressed as a positive number.
    """

    return float(
        (distribution <= severity).mean() * 100
    )


def build_episode_context(
    nav: pd.Series,
    threshold: float = 0.10,
) -> list[dict]:

    running_peak = nav.cummax()

    drawdown = (
        nav / running_peak - 1.0
    )

    severity = -drawdown

    episodes = identify_drawdown_episodes(
        nav,
        threshold,
    )

    contexts = []

    for episode in episodes:

        episode_severity = (
            abs(episode.drawdown_pct)
        )

        percentile = severity_percentile(
            episode_severity,
            severity,
        )

        contexts.append(
            {
                "peak_date": episode.peak_date,
                "trough_date": episode.trough_date,
                "drawdown_pct": episode.drawdown_pct,
                "severity_pct": episode_severity * 100,
                "severity_percentile": percentile,
                "decline_days": episode.decline_days,
                "recovery_days": episode.recovery_days,
                "underwater_days": episode.underwater_days,
                "status": episode.status,
            }
        )

    return contexts


if __name__ == "__main__":

    # isin = "INF174K01KT2"
    # isin = "INF109K01BL4"
    isin = "INF179K01608"

    project_root = Path(__file__).resolve().parents[2]

    nav = load_fund_nav(
        isin,
        project_root,
    )

    contexts = build_episode_context(
        nav,
        threshold=0.10,
    )

    for context in contexts:
        print(context)
