from datetime import date
from decimal import Decimal

import pytest

from lps.transactions import Transaction
from lts.lots import HoldingLot, fifo_holding_lots
from lts.position_bridge import LtsPositionId


POSITION = LtsPositionId("Amma", "F1", "A", "Slice-1")


def tx(d, units, amount=None, price=None, event="Anything"):
    return Transaction(
        transaction_date=date.fromisoformat(d),
        event_type=event,
        investor="Amma",
        folio="F1",
        isin="A",
        units=Decimal(str(units)) if units is not None else None,
        amount=Decimal(str(amount)) if amount is not None else None,
        price=Decimal(str(price)) if price is not None else None,
        source_description=f"{d}-{units}",
    )


def test_fifo_uses_signed_units_not_event_type():
    lots = fifo_holding_lots(
        [
            tx("2022-01-01", 10, 1000, 100, event="Purchase"),
            tx("2023-01-01", -4, event="Mystery disposal"),
            tx("2024-01-01", 3, 360, 120, event="Mystery acquisition"),
        ],
        POSITION,
    )

    assert lots == (
        HoldingLot(
            transaction_date=date(2022, 1, 1),
            units_acquired=Decimal("10"),
            units_remaining=Decimal("6"),
            transaction_amount=Decimal("1000"),
            transaction_price=Decimal("100"),
            source_description="2022-01-01-10",
        ),
        HoldingLot(
            transaction_date=date(2024, 1, 1),
            units_acquired=Decimal("3"),
            units_remaining=Decimal("3"),
            transaction_amount=Decimal("360"),
            transaction_price=Decimal("120"),
            source_description="2024-01-01-3",
        ),
    )


def test_fifo_as_of_excludes_later_transactions():
    lots = fifo_holding_lots(
        [
            tx("2022-01-01", 10),
            tx("2024-01-01", 5),
        ],
        POSITION,
        as_of=date(2023, 12, 31),
    )

    assert sum(lot.units_remaining for lot in lots) == Decimal("10")


def test_fifo_consumes_multiple_lots_in_order():
    lots = fifo_holding_lots(
        [
            tx("2022-01-01", 5),
            tx("2023-01-01", 7),
            tx("2024-01-01", -8),
        ],
        POSITION,
    )

    assert lots == (
        HoldingLot(
            transaction_date=date(2023, 1, 1),
            units_acquired=Decimal("7"),
            units_remaining=Decimal("4"),
            transaction_amount=None,
            transaction_price=None,
            source_description="2023-01-01-7",
        ),
    )


def test_fifo_rejects_disposal_without_available_acquisition_units():
    with pytest.raises(ValueError, match="exceeding"):
        fifo_holding_lots(
            [tx("2024-01-01", -1)],
            POSITION,
        )


def test_fifo_ignores_transactions_without_unit_quantity():
    lots = fifo_holding_lots(
        [
            tx("2022-01-01", None),
            tx("2023-01-01", 2),
        ],
        POSITION,
    )

    assert sum(lot.units_remaining for lot in lots) == Decimal("2")
