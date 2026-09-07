from decimal import Decimal

from lps.position_persistence import read_positions, write_positions
from lps.positions import Position, PositionId


def test_write_and_read_positions_preserves_full_collection(tmp_path):
    path = tmp_path / "amma_positions.csv"
    positions = [
        Position(
            id=PositionId("Amma", "F1", "INF001"),
            units=Decimal("10.5"),
            nav=Decimal("100.25"),
            market_value=Decimal("1052.625"),
        ),
        Position(
            id=PositionId("Amma", "F2", "INF002"),
            units=Decimal("0"),
        ),
    ]

    write_positions(path, positions)

    assert read_positions(path) == positions


def test_positions_persistence_has_stable_column_layout(tmp_path):
    path = tmp_path / "appanna_positions.csv"
    write_positions(path, [])

    assert path.read_text(encoding="utf-8").splitlines()[0] == (
        "investor,folio,isin,units,nav,market_value"
    )
