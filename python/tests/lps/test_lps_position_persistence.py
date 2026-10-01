from decimal import Decimal

from lps.position_persistence import read_positions, write_positions
from lps.positions import Position, PositionId


def test_write_and_read_positions_preserves_family_collection(tmp_path):
    path = tmp_path / "positions.csv"
    positions = [
        Position(
            id=PositionId("Amma", "F1", "INF001"),
            units=Decimal("10.5"),
            nav=Decimal("100.25"),
            market_value=Decimal("1052.625"),
            purpose="Retirement",
        ),
        Position(
            id=PositionId("Appanna", "F2", "INF002"),
            units=Decimal("20"),
            nav=Decimal("50"),
            market_value=Decimal("1000"),
            purpose="Education",
        ),
        Position(
            id=PositionId("Amma", "F3", "INF003"),
            units=Decimal("0"),
        ),
    ]

    write_positions(path, positions)

    assert read_positions(path) == positions


def test_positions_persistence_has_stable_column_layout(tmp_path):
    path = tmp_path / "positions.csv"
    write_positions(path, [])

    assert path.read_text(encoding="utf-8").splitlines()[0] == (
        "investor,folio,isin,slice,units,nav,market_value,purpose"
    )


def test_position_identity_is_investor_folio_isin_and_slice():
    primary = PositionId("Amma", "F1", "INF001")
    other_slice = PositionId("Amma", "F1", "INF001", "slice-2")

    assert primary.slice == "slice-1"
    assert primary.key == "Amma|F1|INF001|slice-1"
    assert other_slice.key == "Amma|F1|INF001|slice-2"
    assert primary != other_slice


def test_read_positions_defaults_missing_slice_to_primary(tmp_path):
    path = tmp_path / "positions.csv"
    path.write_text(
        "investor,folio,isin,units,nav,market_value,purpose\n"
        "Amma,F1,INF001,10,1,10,Retirement\n",
        encoding="utf-8",
    )

    positions = read_positions(path)

    assert positions[0].id == PositionId("Amma", "F1", "INF001", "slice-1")
    assert positions[0].id.key == "Amma|F1|INF001|slice-1"
