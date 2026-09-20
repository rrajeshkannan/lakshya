"""Pre-tax Purpose-to-TARGET allocation contract.

This module validates the economic allocation boundary before any taxation,
transaction mechanics, or execution constraints are introduced.

The allocation is Purpose-owned: each Purpose's observed current capital is
allocated across its selected TARGET ISINs using the already-selected FINAL
weights. Tax consequences are deliberately outside this contract and must not
rewrite the pre-tax allocation.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .models import FormationIntentRow, TargetFormation

ZERO = Decimal("0")
ONE = Decimal("1")
TOLERANCE = Decimal("0.00000001")


def _rows(formation: TargetFormation | list[FormationIntentRow]) -> tuple[FormationIntentRow, ...]:
    return formation.rows if isinstance(formation, TargetFormation) else tuple(formation)


def validate_purpose_target_allocation(
    formation: TargetFormation | list[FormationIntentRow],
) -> None:
    """Validate the pre-tax Purpose-to-TARGET allocation.

    Each Purpose must have one consistent capital base, non-negative finite
    weights, and weights summing to one. The function does not apply tax,
    mutate capital, or construct transaction instructions.
    """
    rows = _rows(formation)
    if not rows:
        raise ValueError("Purpose TARGET allocation cannot be empty.")

    capital_by_purpose: dict[str, Decimal] = {}
    weight_sum: defaultdict[str, Decimal] = defaultdict(lambda: ZERO)
    seen: set[tuple[str, str]] = set()

    for row in rows:
        if not row.purpose.strip() or not row.isin.strip():
            raise ValueError("Purpose and ISIN must be non-blank.")
        if not row.target_capital.is_finite() or row.target_capital < ZERO:
            raise ValueError(f"Invalid target capital for Purpose {row.purpose!r}.")
        if not row.target_weight.is_finite() or not ZERO <= row.target_weight <= ONE:
            raise ValueError(f"Invalid target weight for Purpose {row.purpose!r}, ISIN {row.isin!r}.")
        key = (row.purpose, row.isin)
        if key in seen:
            raise ValueError(f"Duplicate Purpose-to-ISIN allocation: {key!r}")
        seen.add(key)

        prior_capital = capital_by_purpose.setdefault(row.purpose, row.target_capital)
        if prior_capital != row.target_capital:
            raise ValueError(
                f"Purpose {row.purpose!r} has inconsistent target capital bases: "
                f"{prior_capital} and {row.target_capital}."
            )
        weight_sum[row.purpose] += row.target_weight

    for purpose, total in weight_sum.items():
        if abs(total - ONE) > TOLERANCE:
            raise ValueError(
                f"TARGET weights for Purpose {purpose!r} must sum to 1; got {total}."
            )


__all__ = ["validate_purpose_target_allocation"]
