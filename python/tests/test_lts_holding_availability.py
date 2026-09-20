from datetime import date
from decimal import Decimal

from lts.holding_availability import summarize_holding_availability
from lts.holding_constraints import HoldingTaxConstraint, analyze_holding
from lps.positions import Position, PositionId
from lps.transactions import Transaction


POSITION = Position(
    id=PositionId("Amma", "F1", "A"),
    units=Decimal("30"),
    nav=Decimal("150"),
    market_value=Decimal("4500"),
    purpose="Edu",
)


def tx(d, units, amount):
    return Transaction(
        transaction_date=date.fromisoformat(d),
        event_type="Any",
        investor="Amma",
        folio="F1",
        isin="A",
        units=Decimal(str(units)),
        amount=Decimal(str(amount)) if amount is not None else None,
        price=None,
        source_description=f"{d}-{units}",
    )


def test_all_unlocked_lots_are_bundled():
    analysis = analyze_holding(
        POSITION,
        [tx("2020-01-01", 10, 1000), tx("2021-01-01", 20, 2000)],
        date(2026, 9, 20),
        HoldingTaxConstraint(isin="A", is_elss=True),
    )

    result = summarize_holding_availability(analysis)

    assert result.unlocked_units == Decimal("30")
    assert result.unlocked_value == Decimal("4500")
    assert result.unlocked_lot_count == 2
    assert result.locked_lots == ()


def test_locked_lots_remain_individual_and_unlocked_units_are_bundled():
    analysis = analyze_holding(
        POSITION,
        [
            tx("2020-01-01", 10, 1000),
            tx("2025-01-01", 20, 2000),
        ],
        date(2026, 9, 20),
        HoldingTaxConstraint(isin="A", is_elss=True),
    )

    result = summarize_holding_availability(analysis)

    assert result.unlocked_units == Decimal("10")
    assert result.unlocked_value == Decimal("1500")
    assert result.unlocked_lot_count == 1
    assert result.locked_units == Decimal("20")
    assert result.locked_value == Decimal("3000")
    assert len(result.locked_lots) == 1
    assert result.locked_lots[0].acquired_on == date(2025, 1, 1)
    assert result.locked_lots[0].units == Decimal("20")
    assert result.locked_lots[0].current_value == Decimal("3000")
    assert result.locked_lots[0].locked_until == date(2028, 1, 1)


def test_missing_nav_keeps_values_unknown_without_losing_unit_visibility():
    position = Position(
        id=POSITION.id,
        units=Decimal("10"),
        nav=None,
        market_value=None,
        purpose="Edu",
    )
    analysis = analyze_holding(
        position,
        [tx("2020-01-01", 10, 1000)],
        date(2026, 9, 20),
        HoldingTaxConstraint(isin="A", is_elss=True),
    )

    result = summarize_holding_availability(analysis)

    assert result.unlocked_units == Decimal("10")
    assert result.unlocked_value is None
    assert result.locked_lots == ()
