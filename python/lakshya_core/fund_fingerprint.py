from .elevation import calculate_elevation
from .models import Fund, FundBehaviouralFingerprint
from .drawdown_severity import calculate_protection
from .drawdown_episodes import (
    identify_drawdown_episodes,
    calculate_resilience,
)

import pandas as pd


DRAWDOWN_EPISODE_THRESHOLD_PCT = 5.0


def build_fund_behavioural_fingerprint(
    fund: Fund,
    nav: pd.DataFrame,
) -> FundBehaviouralFingerprint:
    """
    Build the complete Fund-stage Behavioural Fingerprint.

    This is an orchestration function, not a new analytical engine.

    It asks the three independent behavioural dimensions to interpret
    the same observed NAV history:

        Elevation   -> prosperity terrain
        Protection  -> adversity severity
        Resilience  -> behaviour after adversity begins

    The resulting evidence is composed into a single Fund Compass.

    No scoring, ranking, weighting, suitability judgement, or benchmark
    comparison occurs here.
    """

    elevation = calculate_elevation(nav)

    protection = calculate_protection(nav)

    episodes = identify_drawdown_episodes(
        nav["nav"],
        threshold_pct=DRAWDOWN_EPISODE_THRESHOLD_PCT,
    )

    resilience = calculate_resilience(episodes)

    return FundBehaviouralFingerprint(
        fund=fund,
        elevation=elevation,
        protection=protection,
        resilience=resilience,
    )
