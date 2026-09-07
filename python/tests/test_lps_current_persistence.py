from datetime import date
from decimal import Decimal

from lps.current import CurrentSnapshot
from lps.current_persistence import persist_current_snapshot
from lps.current_state import CurrentState
from lps.positions import Position, PositionKey


def test_persist_current_snapshot_preserves_all_current_states(tmp_path):
    zero_position = Position(
        key=PositionKey("Amma", "F1", "INF001"),
        units=Decimal("0"),
    )
    snapshot = CurrentSnapshot(
        investor="Amma",
        transaction_through_date=date(2026, 1, 2),
        valuation_as_of_date=date(2026, 9, 8),
        current_states=(CurrentState(position=zero_position),),
        valuations=(),
        total_market_value=Decimal("0"),
    )

    path = persist_current_snapshot(snapshot, tmp_path / "current")

    assert path == tmp_path / "current" / "2026-09-08" / "Amma.json"
    text = path.read_text(encoding="utf-8")
    assert '"transaction_through_date": "2026-01-02"' in text
    assert '"valuation_as_of_date": "2026-09-08"' in text
    assert '"investor": "Amma"' in text
    assert '"units": "0"' in text
    assert text.count('"units": "0"') == 1


def test_persist_current_snapshot_creates_one_file_per_investor(tmp_path):
    for investor in ("Amma", "Appanna"):
        snapshot = CurrentSnapshot(
            investor=investor,
            transaction_through_date=date(2026, 1, 2),
            valuation_as_of_date=date(2026, 9, 8),
            current_states=(),
            valuations=(),
            total_market_value=Decimal("0"),
        )
        persist_current_snapshot(snapshot, tmp_path / "current")

    assert (tmp_path / "current" / "2026-09-08" / "Amma.json").exists()
    assert (tmp_path / "current" / "2026-09-08" / "Appanna.json").exists()
