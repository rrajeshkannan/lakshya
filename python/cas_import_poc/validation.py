"""Hard validation checks for the CAS import boundary."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

from .models import ReconciliationResult


_UNIT_EVENT_TYPES = {
    "PURCHASE",
    "PURCHASE_SIP",
    "REDEMPTION",
    "SWITCH_IN",
    "SWITCH_IN_MERGER",
    "SWITCH_OUT",
    "SWITCH_OUT_MERGER",
    "SEGREGATION",
    "GIFT_IN",
    "GIFT_OUT",
    "DIVIDEND_REINVEST",
}


_SIGN_BY_TYPE = {
    "PURCHASE": Decimal("1"),
    "PURCHASE_SIP": Decimal("1"),
    "REDEMPTION": Decimal("-1"),
    "SWITCH_IN": Decimal("1"),
    "SWITCH_IN_MERGER": Decimal("1"),
    "SWITCH_OUT": Decimal("-1"),
    "SWITCH_OUT_MERGER": Decimal("-1"),
    "SEGREGATION": Decimal("1"),
    "GIFT_IN": Decimal("1"),
    "GIFT_OUT": Decimal("-1"),
    "DIVIDEND_REINVEST": Decimal("1"),
}


def reconcile_unit_balance(
    opening_units: Decimal,
    printed_closing_units: Decimal,
    transactions: Iterable[Any],
) -> ReconciliationResult:
    """Reconstruct closing units from parsed unit-bearing transaction events."""
    computed = Decimal(opening_units)
    for transaction in transactions:
        parser_type = getattr(transaction, "type", None)
        parser_type = getattr(parser_type, "value", parser_type)
        parser_type = str(parser_type)
        if parser_type not in _UNIT_EVENT_TYPES:
            continue
        units = getattr(transaction, "units", None)
        if units is None:
            raise ValueError(
                f"Unit-bearing transaction has no units: {parser_type}"
            )
        computed += _SIGN_BY_TYPE[parser_type] * Decimal(str(units))

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
