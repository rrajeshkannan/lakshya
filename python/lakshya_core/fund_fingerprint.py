from .elevation import calculate_elevation
from .models import Fund, FundFingerprint
from .drawdown_severity import calculate_protection

import pandas as pd


def build_fund_behavioural_fingerprint(
    fund: Fund,
    nav: pd.DataFrame,
) -> FundFingerprint:
    """
    Build the Fund-stage Fingerprint.

    This is an orchestration function, not a new analytical engine.

    It asks the active Fund-stage behavioural dimensions to interpret
    the same observed NAV history:

        Elevation   -> prosperity terrain
        Protection  -> adversity severity

    The resulting evidence is composed into a single Fund Fingerprint.

    No scoring, ranking, weighting, suitability judgement, or benchmark
    comparison occurs here.
    """

    elevation = calculate_elevation(nav)
    protection = calculate_protection(nav)

    return FundFingerprint(
        fund=fund,
        elevation=elevation,
        protection=protection,
    )
