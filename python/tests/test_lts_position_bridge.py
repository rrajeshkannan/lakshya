from decimal import Decimal

from lps.positions import Position, PositionId
from lts.position_bridge import LtsPositionId, LtsPosition, bridge_positions


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
        LtsPosition(
            id=LtsPositionId("Amma", "F1", "INF001", "Slice-1"),
            units=Decimal("10"),
            nav=Decimal("100"),
            market_value=Decimal("1000"),
            purpose="Retirement",
            percentage=Decimal("100"),
        )
    ]


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
    assert projected[0].id == LtsPositionId("Amma", "F1", "INF001", "Slice-1")
    assert projected[0].id.slice == "Slice-1"
    assert projected[0].id.investor == source.id.investor
    assert projected[0].id.folio == source.id.folio
    assert projected[0].id.isin == source.id.isin
