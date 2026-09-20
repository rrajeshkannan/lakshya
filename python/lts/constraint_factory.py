"""Build holding constraints from the already-projected fund classification."""

from __future__ import annotations

from .fund_metadata import FundClassification
from .holding_constraints import HoldingTaxConstraint


def holding_constraint_for_fund(
    classification: FundClassification,
    *,
    long_term_holding_months: int | None = None,
    elss_lock_in_years: int = 3,
) -> HoldingTaxConstraint:
    """Create the minimal holding constraint for one classified fund.

    The fund classification supplies the explicit ELSS fact. The applicable
    long-term holding threshold remains an explicit caller-supplied rule;
    this function does not infer tax rules from fund names or categories.
    """
    if long_term_holding_months is not None and long_term_holding_months <= 0:
        raise ValueError("long_term_holding_months must be positive when supplied")
    if elss_lock_in_years <= 0:
        raise ValueError("elss_lock_in_years must be positive")

    return HoldingTaxConstraint(
        isin=classification.isin,
        is_elss=classification.is_elss,
        elss_lock_in_years=elss_lock_in_years,
        long_term_holding_months=long_term_holding_months,
    )


__all__ = ["holding_constraint_for_fund"]
