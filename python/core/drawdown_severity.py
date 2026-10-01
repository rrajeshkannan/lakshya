"""
Protection evidence for the Lakshya Fund Behavioural Fingerprint.

Protection describes the severity of adversity experienced by a fund
relative to its own historical high-water mark.

The important distinction is:

    Protection asks:
        "How severe is the adversity when it happens?"

It does not ask:

    "How did the fund compare with its benchmark?"

Benchmark-relative behaviour is a separate analytical lens and is not
part of intrinsic Fund-stage Protection evidence.

This module calculates severity only. Recovery journeys belong to
ResilienceEvidence and are handled by the drawdown episode layer.
"""

from __future__ import annotations

import pandas as pd

from .models import ProtectionEvidence


# These thresholds define the common severity terrain we observe across
# funds. They are deliberately shared across funds so that the resulting
# ProtectionEvidence remains comparable at the Fund stage.
PROTECTION_THRESHOLDS = (5, 10, 15, 20, 25, 30)


def calculate_protection(
    nav: pd.DataFrame,
) -> ProtectionEvidence:
    """
    Calculate intrinsic Protection evidence from a fund's NAV history.

    Severity is measured relative to the fund's own running high-water
    mark:

        severity = 1 - (NAV / running_high_water_mark)

    Therefore:

        NAV at high-water mark -> 0% severity
        NAV 10% below high-water mark -> 10% severity
        NAV 40% below high-water mark -> 40% severity

    No benchmark is required.

    This function describes the adversity terrain only. It does not
    describe how quickly the fund recovered from that adversity.
    """

    nav = nav.dropna().sort_values("date").copy()

    if nav.empty:
        raise ValueError("NAV series is empty.")

    running_peak = nav["nav"].cummax()

    severity = (
        1.0 - (nav["nav"] / running_peak)
    ).clip(lower=0.0)

    return ProtectionEvidence(
        observations=int(len(severity)),

        median_severity_pct=float(
            severity.quantile(0.50) * 100
        ),

        percentile_75_severity_pct=float(
            severity.quantile(0.75) * 100
        ),

        percentile_90_severity_pct=float(
            severity.quantile(0.90) * 100
        ),

        percentile_95_severity_pct=float(
            severity.quantile(0.95) * 100
        ),

        percentile_99_severity_pct=float(
            severity.quantile(0.99) * 100
        ),

        maximum_severity_pct=float(
            severity.max() * 100
        ),

        # Threshold membership is evaluated with a tiny numerical tolerance.
        # This prevents floating-point representation (for example, 0.099999999999...)
        # from incorrectly excluding an observation that is mathematically exactly
        # on a severity boundary.
        days_at_or_above_threshold={
            threshold: int(
                (severity >= (threshold / 100) - 1e-12).sum()
            )
            for threshold in PROTECTION_THRESHOLDS
        },

        pct_days_at_or_above_threshold={
            threshold: float(
                (severity >= (threshold / 100) - 1e-12).mean() * 100
            )
            for threshold in PROTECTION_THRESHOLDS
        },
    )
