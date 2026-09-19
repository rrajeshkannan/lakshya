from datetime import date
from decimal import Decimal

from lps.transactions import Transaction
from lts.physical_transaction_history import transactions_for_holding
from lts.position_bridge import LtsPositionId


def transaction(d, event, investor="Amma", folio="F1", isin="A", source="source"):
    return Transaction(
        transaction_date=date.fromisoformat(d),
        event_type=event,
        investor=investor,
        folio=folio,
        isin=isin,
        units=Decimal("1"),
        amount=Decimal("100"),
        price=Decimal("100"),
        source_description=source,
    )


def test_transaction_history_is_at_physical_holding_grain():
    transactions = [
        transaction("2026-02-01", "Purchase", source="newer"),
        transaction("2026-01-01", "Purchase", source="older"),
        transaction("2026-03-01", "Purchase", folio="F2"),
    ]

    history = transactions_for_holding(
        transactions,
        LtsPositionId("Amma", "F1", "A", "Slice-2"),
    )

    assert history == (transactions[1], transactions[0])


def test_slice_does_not_change_transaction_history():
    transactions = [
        transaction("2026-01-01", "Purchase"),
    ]

    slice_one = transactions_for_holding(
        transactions,
        LtsPositionId("Amma", "F1", "A", "Slice-1"),
    )
    slice_two = transactions_for_holding(
        transactions,
        LtsPositionId("Amma", "F1", "A", "Slice-2"),
    )

    assert slice_one == slice_two == (transactions[0],)
