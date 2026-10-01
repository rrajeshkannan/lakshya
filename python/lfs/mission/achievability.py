"""Goal requirement calculations for MISSION."""

from __future__ import annotations

from math import isfinite

from .models import Purpose


def _future_value(
    capital: float,
    monthly_contribution: float,
    monthly_rate: float,
    months: int,
) -> float:
    """Return the future value at the end of ``months`` periods."""
    existing = capital * (1.0 + monthly_rate) ** months
    if monthly_contribution == 0.0:
        return existing

    if monthly_rate == 0.0:
        contributions = monthly_contribution * months
    else:
        contributions = monthly_contribution * (
            ((1.0 + monthly_rate) ** months - 1.0) / monthly_rate
        )
    return existing + contributions


def required_annual_return(purpose: Purpose) -> float | None:
    """Calculate the annualised return required by a targeted Purpose.

    This is a requirement calculation only; it does not forecast future
    investment returns.
    """
    target = purpose.desired_target
    horizon_years = purpose.horizon_years
    contribution = purpose.monthly_contribution or 0.0

    if target is None or horizon_years is None:
        return None
    if not isfinite(purpose.capital) or purpose.capital < 0:
        raise ValueError("capital must be finite and non-negative")
    if not isfinite(target) or target < 0:
        raise ValueError("desired_target must be finite and non-negative")
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")
    if not isfinite(contribution) or contribution < 0:
        raise ValueError("monthly_contribution must be finite and non-negative")

    months = horizon_years * 12
    if _future_value(purpose.capital, contribution, 0.0, months) >= target:
        return 0.0

    low = -0.999999
    high = 1.0
    while _future_value(purpose.capital, contribution, high, months) < target:
        high *= 2.0
        if high > 100.0:
            raise ValueError("required return is outside supported calculation range")

    for _ in range(200):
        mid = (low + high) / 2.0
        if _future_value(purpose.capital, contribution, mid, months) < target:
            low = mid
        else:
            high = mid

    monthly_rate = (low + high) / 2.0
    return (1.0 + monthly_rate) ** 12 - 1.0
