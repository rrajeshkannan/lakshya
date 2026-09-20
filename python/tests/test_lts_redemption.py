from datetime import date
from decimal import Decimal

import pytest

from lps.transactions import Transaction
from lts.position_bridge import LtsPositionId
from lts.redemption import FifoRedemptionAllocation, fifo_redemption_allocations


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


def test_redemption_allocates_against_one_acquisition_lot():
    allocations = fifo_redemption_allocations(
        [
            tx("2022-01-01", 10, 1000, 100),
            tx("2024-01-01", -4),
        ],
        POSITION,
    )

    assert allocations == (
        FifoRedemptionAllocation(
            disposal_date=date(2024, 1, 1),
            acquisition_date=date(2022, 1, 1),
            units=Decimal("4"),
            acquisition_amount=Decimal("1000"),
            acquisition_price=Decimal("100"),
            acquisition_source_description="2022-01-01-10",
        ),
    )


def test_redemption_consumes_multiple_lots_in_fifo_order():
    allocations = fifo_redemption_allocations(
        [
            tx("2022-01-01", 5),
            tx("2023-01-01", 7),
            tx("2024-01-01", -8),
        ],
        POSITION,
    )

    assert allocations == (
        FifoRedemptionAllocation(
            disposal_date=date(2024, 1, 1),
            acquisition_date=date(2022, 1, 1),
            units=Decimal("5"),
            acquisition_amount=None,
            acquisition_price=None,
            acquisition_source_description="2022-01-01-5",
        ),
        FifoRedemptionAllocation(
            disposal_date=date(2024, 1, 1),
            acquisition_date=date(2023, 1, 1),
            units=Decimal("3"),
            acquisition_amount=None,
            acquisition_price=None,
            acquisition_source_description="2023-01-01-7",
        ),
    )


def test_redemption_records_partial_consumption_of_latest_lot():
    allocations = fifo_redemption_allocations(
        [
            tx("2022-01-01", 5),
            tx("2023-01-01", 7),
            tx("2024-01-01", -6),
        ],
        POSITION,
    )

    assert [allocation.units for allocation in allocations] == [Decimal("5"), Decimal("1")]


def test_redemption_records_complete_consumption_of_older_lot():
    allocations = fifo_redemption_allocations(
        [
            tx("2022-01-01", 5),
            tx("2023-01-01", 7),
            tx("2024-01-01", -5),
        ],
        POSITION,
    )

    assert allocations[0].acquisition_date == date(2022, 1, 1)
    assert allocations[0].units == Decimal("5")
    assert len(allocations) == 1


def test_redemption_rejects_over_redemption():
    with pytest.raises(ValueError, match="exceeding"):
        fifo_redemption_allocations(
            [tx("2024-01-01", -1)],
            POSITION,
        )


def test_redemption_order_is_deterministic_for_multiple_disposals():
    allocations = fifo_redemption_allocations(
        [
            tx("2022-01-01", 10),
            tx("2023-01-01", -3),
            tx("2024-01-01", -4),
        ],
        POSITION,
    )

    assert allocations == (
        FifoRedemptionAllocation(
            disposal_date=date(2023, 1, 1),
            acquisition_date=date(2022, 1, 1),
            units=Decimal("3"),
            acquisition_amount=None,
            acquisition_price=None,
            acquisition_source_description="2022-01-01-10",
        ),
        FifoRedemptionAllocation(
            disposal_date=date(2024, 1, 1),
            acquisition_date=date(2022, 1, 1),
            units=Decimal("4"),
            acquisition_amount=None,
            acquisition_price=None,
            acquisition_source_description="2022-01-01-10",
        ),
    )
