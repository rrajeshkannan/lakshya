"""
Elevation evidence for the Lakshya Fund Behavioural Fingerprint.

Elevation describes the fund's observed prosperity terrain across
multiple investment horizons.

The rolling-return calculation itself remains owned by
rolling_returns.py. This module composes those calculations into the
Fund-stage ElevationEvidence object.

Important:
    ElevationEvidence describes historical behaviour.
    It is not a return forecast and does not imply that future returns
    will repeat the historical observations.
"""

from __future__ import annotations

import pandas as pd

from .models import ElevationEvidence
from .rolling_returns import calculate_rolling_cagr


def _calculate_horizon(
    nav: pd.DataFrame,
    years: int,
):
    """
    Calculate rolling-return evidence for one horizon.

    If the fund does not have enough historical NAV data to support the
    requested horizon, the evidence remains unavailable.

    We deliberately preserve that distinction:

        insufficient evidence != zero return
    """

    try:
        return calculate_rolling_cagr(nav, years)
    except ValueError:
        return None


def calculate_elevation(nav: pd.DataFrame) -> ElevationEvidence:
    """
    Calculate the Fund-stage Elevation evidence from a fund's NAV history.

    Each horizon is calculated independently. A fund may therefore have
    valid evidence for shorter horizons while having insufficient
    evidence for longer horizons.

    No forecast is produced here. This function only assembles observed
    historical rolling-return evidence.
    """

    return ElevationEvidence(
        rolling_3y=_calculate_horizon(nav, 3),
        rolling_5y=_calculate_horizon(nav, 5),
        rolling_7y=_calculate_horizon(nav, 7),
        rolling_10y=_calculate_horizon(nav, 10),
    )
