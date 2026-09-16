from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from lps.nav_evidence import NavEvidenceStore
from lps.positions import Position, PositionId
from lps.transactions import Transaction
from mission.historical_positions import build_positions_as_of


def _tx(day: str, units: str, *, isin: str = "ISIN1") -> Transaction:
    return Transaction(
        transaction_date=date.fromisoformat(day),
        event_type="Purchase" if Decimal(units) > 0 else "Redemption",
        investor="Amma",
        folio="F1",
        isin=isin,
        units=Decimal(units),
        amount=None,
        price=None,
        source_description="test",
    )


def _nav(path: Path, isin: str = "ISIN1") -> None:
    store = NavEvidenceStore(path / f"{isin}.json")
    store.create(
        isin=isin,
        scheme_code=1,
        source="test",
        nav=pd.DataFrame(
            {
                "date": ["2026-09-01", "2026-09-10", "2026-09-15"],
                "nav": [100.0, 110.0, 120.0],
            }
        ),
        retrieved_at="2026-09-16T00:00:00+05:30",
    )


def test_build_positions_as_of_uses_transactions_through_boundary_and_nav_at_boundary(tmp_path: Path):
    nav_dir = tmp_path / "nav"
    nav_dir.mkdir()
    _nav(nav_dir)

    current = [
        Position(
            id=PositionId("Amma", "F1", "ISIN1"),
            units=Decimal("999"),
            purpose="Edu_B",
        )
    ]
    transactions = [
        _tx("2026-09-05", "10"),
        _tx("2026-09-10", "5"),
        _tx("2026-09-11", "100"),
        _tx("2026-09-15", "-2"),
    ]

    positions = build_positions_as_of(
        transactions,
        current,
        formation_as_of=date(2026, 9, 10),
        nav_dir=nav_dir,
    )

    assert len(positions) == 1
    position = positions[0]
    assert position.units == Decimal("15")
    assert position.nav == Decimal("110.0")
    assert position.market_value == Decimal("1650.0")
    assert position.purpose == "Edu_B"


def test_build_positions_as_of_preserves_zero_unit_position_without_nav(tmp_path: Path):
    nav_dir = tmp_path / "nav"
    nav_dir.mkdir()
    _nav(nav_dir)

    current = [
        Position(
            id=PositionId("Amma", "F1", "ISIN1"),
            units=Decimal("999"),
            purpose="Edu_B",
        )
    ]
    transactions = [_tx("2026-09-05", "10"), _tx("2026-09-10", "-10")]

    positions = build_positions_as_of(
        transactions,
        current,
        formation_as_of=date(2026, 9, 10),
        nav_dir=nav_dir,
    )

    assert positions[0].units == 0
    assert positions[0].nav is None
    assert positions[0].market_value is None
    assert positions[0].purpose == "Edu_B"
