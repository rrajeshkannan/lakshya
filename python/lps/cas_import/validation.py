"""Hard validation checks for the CAS import boundary."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

from .models import ReconciliationResult


def reconcile_unit_balance(
    opening_units: Decimal,
    printed_closing_units: Decimal,
    transactions: Iterable[Any],
) -> ReconciliationResult:
    """Reconstruct closing units using casparser's signed unit movements.

    casparser normalizes transaction ``units`` to economic movement signs
    before returning the CASData object. In particular, redemption and
    switch-out units are negative. Lakshya must preserve those source
    semantics rather than applying a second sign based on transaction type.
    """
    computed = Decimal(opening_units)
    for transaction in transactions:
        units = getattr(transaction, "units", None)
        if units is None:
            continue
        computed += Decimal(str(units))

    return ReconciliationResult(
        opening_units=Decimal(opening_units),
        computed_closing_units=computed,
        printed_closing_units=Decimal(printed_closing_units),
    )


def validate_parse_warnings(data: Any) -> None:
    """Treat parser data-quality warnings as a hard import boundary failure."""
    warnings = list(getattr(data, "parse_warnings", None) or [])
    if warnings:
        raise ValueError(
            "casparser reported data-quality warnings; review before import:\n"
            + "\n".join(str(warning) for warning in warnings)
        )


def validate_scheme_unit_balances(data: Any) -> list[ReconciliationResult]:
    """Validate every scheme whose parsed output contains a unit balance."""
    results: list[ReconciliationResult] = []
    for folio in data.folios:
        for scheme in folio.schemes:
            result = reconcile_unit_balance(
                Decimal(str(scheme.open)),
                Decimal(str(scheme.close)),
                scheme.transactions,
            )
            results.append(result)
            if not result.passed:
                raise ValueError(
                    "Unit-balance reconciliation failed for "
                    f"folio={folio.folio} scheme={scheme.scheme} isin={scheme.isin}: "
                    f"computed={result.computed_closing_units} "
                    f"printed={result.printed_closing_units}"
                )
    return results
