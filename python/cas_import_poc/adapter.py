"""Translate casparser CAMS output into Lakshya's small canonical vocabulary."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from .models import CanonicalTransaction


# Keep the normal path explicit. Unknown parser types are surfaced rather than guessed.
_EVENT_TYPE_MAP = {
    "PURCHASE": "Purchase",
    "PURCHASE_SIP": "Systematic Investment",
    "REDEMPTION": "Redemption",
    "SWITCH_IN": "Switch In",
    "SWITCH_IN_MERGER": "Switch In",
    "SWITCH_OUT": "Switch Out",
    "SWITCH_OUT_MERGER": "Switch Out",
    "STAMP_DUTY_TAX": "Stamp Duty",
    "STT_TAX": "STT Paid",
    "TDS_TAX": "TDS",
    "REVERSAL": "Reversal",
    "DIVIDEND_PAYOUT": "Dividend Payout",
    "DIVIDEND_REINVEST": "Dividend Reinvest",
    "SEGREGATION": "Segregation",
    "GIFT_IN": "Gift In",
    "GIFT_OUT": "Gift Out",
    "MISC": "Misc",
    "UNKNOWN": "Unknown",
}


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    # casparser's transaction dates are documented as ISO dates.
    return date.fromisoformat(str(value))


def _event_type(parser_type: Any) -> str:
    key = getattr(parser_type, "value", parser_type)
    try:
        return _EVENT_TYPE_MAP[str(key)]
    except KeyError as exc:
        raise ValueError(f"Unsupported casparser transaction type: {key}") from exc


def adapt_transaction(*, investor: str, folio: str, isin: str, transaction: Any) -> CanonicalTransaction:
    """Adapt one casparser transaction object without exposing its schema downstream."""
    if not isin:
        raise ValueError("Cannot adapt transaction without ISIN.")
    description = str(getattr(transaction, "description", ""))
    return CanonicalTransaction(
        transaction_date=_as_date(transaction.date),
        event_type=_event_type(transaction.type),
        investor=investor,
        folio=folio,
        isin=isin,
        units=_decimal(getattr(transaction, "units", None)),
        amount=_decimal(getattr(transaction, "amount", None)),
        price=_decimal(getattr(transaction, "nav", None)),
        source_description=description,
    )


def adapt_cas(data: Any, *, investor_override: str | None = None) -> list[CanonicalTransaction]:
    """Adapt an entire CAMS/KFintech CASData object to canonical transactions."""
    investor = investor_override or str(data.investor_info.name).strip()
    rows: list[CanonicalTransaction] = []
    for folio in data.folios:
        for scheme in folio.schemes:
            isin = scheme.isin
            if not isin:
                # No guess: the POC cannot form Lakshya Position identity without ISIN.
                raise ValueError(
                    f"Scheme has no ISIN and cannot become a Lakshya Position: {scheme.scheme}"
                )
            for transaction in scheme.transactions:
                rows.append(
                    adapt_transaction(
                        investor=investor,
                        folio=str(folio.folio),
                        isin=str(isin),
                        transaction=transaction,
                    )
                )
    return rows
