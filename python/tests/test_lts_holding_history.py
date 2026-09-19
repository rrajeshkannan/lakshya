from datetime import date
from decimal import Decimal

from lps.transactions import Transaction
from lts.holding_history import HoldingHistory, holding_history
from lts.position_bridge import LtsPositionId


def transaction(d, event="Purchase"):
    return Transaction(
        transaction_date=date.fromisoformat(d),
        event_type=event,
        investor="Amma",
        folio="F1",
        isin="A",
        units=Decimal("1"),
        amount=Decimal("100"),
        price=Decimal("100"),
        source_description="source",
    )


def test_holding_history_summarizes_transaction_dates():
    result = holding_history(
        [transaction("2026-03-01"), transaction("2026-01-01")],
        LtsPositionId("Amma", "F1", "A", "Slice-1"),
    )

    assert result == HoldingHistory(
        transaction_count=2,
        first_transaction_date=date(2026, 1, 1),
        last_transaction_date=date(2026, 3, 1),
    )


def test_holding_history_is_independent_of_slice():
    transactions = [transaction("2026-01-01")]

    slice_one = holding_history(
        transactions,
        LtsPositionId("Amma", "F1", "A", "Slice-1"),
    )
    slice_two = holding_history(
        transactions,
        LtsPositionId("Amma", "F1", "A", "Slice-2"),
    )

    assert slice_one == slice_two


def test_holding_history_is_empty_when_no_transactions_exist():
    result = holding_history(
        [],
        LtsPositionId("Amma", "F1", "A", "Slice-1"),
    )

    assert result == HoldingHistory(
        transaction_count=0,
        first_transaction_date=None,
        last_transaction_date=None,
    )
