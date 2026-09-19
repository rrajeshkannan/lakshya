from datetime import date
from decimal import Decimal

from lps.transactions import Transaction
from lts.acquisition_transactions import (
    ACQUISITION_EVENT_TYPES,
    acquisition_transactions_for_holding,
)
from lts.position_bridge import LtsPositionId


def tx(d, event):
    return Transaction(
        transaction_date=date.fromisoformat(d),
        event_type=event,
        investor="Amma",
        folio="F1",
        isin="A",
        units=Decimal("1"),
        amount=Decimal("100"),
        price=Decimal("100"),
        source_description=event,
    )


def test_acquisition_transactions_are_selected_from_holding_history():
    transactions = [
        tx("2026-01-01", "Purchase"),
        tx("2026-02-01", "SIP"),
        tx("2026-03-01", "Switch In"),
        tx("2026-04-01", "Switch Out"),
        tx("2026-05-01", "Redemption"),
    ]

    result = acquisition_transactions_for_holding(
        transactions,
        LtsPositionId("Amma", "F1", "A", "Slice-1"),
    )

    assert [item.event_type for item in result] == [
        "Purchase",
        "SIP",
        "Switch In",
    ]


def test_acquisition_transactions_are_independent_of_slice():
    transactions = [tx("2026-01-01", "Purchase")]

    one = acquisition_transactions_for_holding(
        transactions, LtsPositionId("Amma", "F1", "A", "Slice-1")
    )
    two = acquisition_transactions_for_holding(
        transactions, LtsPositionId("Amma", "F1", "A", "Slice-2")
    )

    assert one == two == (transactions[0],)


def test_acquisition_event_types_are_explicit():
    assert ACQUISITION_EVENT_TYPES == frozenset({"Purchase", "SIP", "Switch In"})
