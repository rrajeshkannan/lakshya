from decimal import Decimal

from lps.current_state import CurrentState, derive_current_state
from lps.positions import Position, PositionKey


def test_derive_current_state_wraps_position_without_copying_units():
    position = Position(
        key=PositionKey("Amma", "F1", "INF001"),
        units=Decimal("123.45"),
    )

    states = derive_current_state([position])

    assert states == [CurrentState(position=position)]
    assert states[0].position.units == Decimal("123.45")


def test_derive_current_state_retains_zero_balance_historical_position():
    position = Position(
        key=PositionKey("Amma", "F2", "INF002"),
        units=Decimal("0"),
    )

    states = derive_current_state([position])

    assert len(states) == 1
    assert states[0].position.units == Decimal("0")
