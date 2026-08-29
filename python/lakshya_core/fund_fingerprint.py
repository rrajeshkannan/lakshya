from .elevation import calculate_elevation
from .models import Fund, FundFingerprint
from .drawdown_severity import calculate_protection
from .drawdown_episodes import (
    identify_drawdown_episodes,
    calculate_resilience,
)

import pandas as pd


# Drawdown episodes are detected once adversity reaches 5%.
#
# This value is represented as a decimal fraction because the underlying
# episode detector compares it directly with decimal drawdown values:
#
#     0.05 == 5%
#
# This is deliberately separate from Protection's 5/10/15/... severity
# terrain thresholds. Those thresholds measure frequency; this threshold
# defines the resolution at which we record a journey.
DRAWDOWN_EPISODE_THRESHOLD = 0.05


def build_fund_behavioural_fingerprint(
    fund: Fund,
    nav: pd.DataFrame,
) -> FundFingerprint:
    """
    Build the complete Fund-stage Fingerprint.

    This is an orchestration function, not a new analytical engine.

    It asks the three independent behavioural dimensions to interpret
    the same observed NAV history:

        Elevation   -> prosperity terrain
        Protection  -> adversity severity
        Resilience  -> behaviour after adversity begins

    The resulting evidence is composed into a single Fund Fingerprint.

    No scoring, ranking, weighting, suitability judgement, or benchmark
    comparison occurs here.
    """

    elevation = calculate_elevation(nav)

    protection = calculate_protection(nav)

    episodes = identify_drawdown_episodes(
        nav.set_index("date")["nav"],
        threshold_pct=DRAWDOWN_EPISODE_THRESHOLD,
    )

    resilience = calculate_resilience(episodes)

    return FundFingerprint(
        fund=fund,
        elevation=elevation,
        protection=protection,
        resilience=resilience,
    )
