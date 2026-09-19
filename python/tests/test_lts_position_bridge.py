from decimal import Decimal

from lps.positions import Position, PositionId
from lts.position_bridge import LtsPositionId, bridge_positions


def test_bridge_projects_legacy_position_to_slice_one_at_100_percent():
    source = Position(
        id=PositionId("Amma", "F1", "INF001"),
        units=Decimal("10"),
        nav=Decimal("100"),
        market_value=Decimal("1000"),
        purpose="Retirement",
    )

    projected = bridge_positions([source])

    assert projected == [
        projected[0]
    ]
    assert projected[0].id == LtsPositionId(
        "Amma", "F1", "INF001", "Slice-1"
    )
    assert projected[0].units == Decimal("10")
    assert projected[0].nav == Decimal("100")
    assert projected[0].market_value == Decimal("1000")
    assert projected[0].purpose == "Retirement"
    assert projected[0].percentage == Decimal("100")


def test_bridge_preserves_unattributed_position():
    source = Position(
        id=PositionId("Amma", "F1", "INF001"),
        units=Decimal("10"),
        market_value=Decimal("1000"),
        purpose=None,
    )

    projected = bridge_positions([source])

    assert projected[0].purpose is None
    assert projected[0].percentage == Decimal("100")


def test_bridge_does_not_mutate_source_identity():
    source = Position(
        id=PositionId("Amma", "F1", "INF001"),
        units=Decimal("10"),
        purpose="Retirement",
    )

    projected = bridge_positions([source])

    assert source.id == PositionId("Amma", "F1", "INF001")
    assert projected[0].id != source.id
