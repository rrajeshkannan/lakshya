"""Goal requirement calculations for MISSION.

This module calculates the annualised return required to reach a desired
capital target from current capital and an optional constant monthly
contribution. It does not forecast future returns.

Future contributions are treated as month-end cash flows, so each
contribution has only its remaining accumulation period.
"""

from __future__ import annotations

from math import isfinite

from .models import Purpose


def _future_value(
    current_capital: float,
    monthly_contribution: float,
    monthly_rate: float,
    months: int,
) -> float:
    """Return the future value at the end of ``months`` periods."""
    current = current_capital * (1.0 + monthly_rate) ** months
    if monthly_contribution == 0.0:
        return current

    if monthly_rate == 0.0:
        contributions = monthly_contribution * months
    else:
        contributions = monthly_contribution * (
            ((1.0 + monthly_rate) ** months - 1.0) / monthly_rate
        )
    return current + contributions


def required_annual_return(purpose: Purpose) -> float | None:
    """Calculate the annualised return required by a targeted Purpose.

    Returns ``None`` when the Purpose has no complete target/horizon and
    therefore has no meaningful achievability requirement.

    The calculation is a requirement calculation only. It does not claim
    that the returned rate will occur in the future.
    """
    target = purpose.desired_target
    horizon_years = purpose.horizon_years
    contribution = purpose.monthly_contribution or 0.0

    if target is None or horizon_years is None:
        return None
    if not isfinite(purpose.current_capital) or purpose.current_capital < 0:
        raise ValueError("current_capital must be finite and non-negative")
    if not isfinite(target) or target < 0:
        raise ValueError("desired_target must be finite and non-negative")
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")
    if not isfinite(contribution) or contribution < 0:
        raise ValueError("monthly_contribution must be finite and non-negative")

    months = horizon_years * 12

    # At zero growth, determine whether the target is already covered by
    # current capital plus the planned contributions.
    if _future_value(purpose.current_capital, contribution, 0.0, months) >= target:
        return 0.0

    # Solve for the monthly rate by bisection. The upper bound is deliberately
    # generous; this is a required-rate calculation, not a forecast.
    low = -0.999999
    high = 1.0

    while _future_value(purpose.current_capital, contribution, high, months) < target:
        high *= 2.0
        if high > 100.0:
            raise ValueError("required return is outside supported calculation range")

    for _ in range(200):
        mid = (low + high) / 2.0
        if _future_value(purpose.current_capital, contribution, mid, months) < target:
            low = mid
        else:
            high = mid

    monthly_rate = (low + high) / 2.0
    return (1.0 + monthly_rate) ** 12 - 1.0
