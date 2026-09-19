from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from lps.nav_evidence import NavEvidenceStore
from lps.positions import Position, PositionId
from lps.transactions import Transaction
from lts.evidence import build_transition_evidence


def make_store(tmp_path, isin="INF001"):
    path = tmp_path / f"{isin}.json"
    store = NavEvidenceStore(path)
    store.create(
        isin=isin,
        scheme_code="1001",
        source="test",
        nav=pd.DataFrame({
            "date": pd.to_datetime(["2026-08-14", "2026-08-18"]),
            "nav": [Decimal("109.78"), Decimal("109.06")],
        }),
        retrieved_at="2026-08-18T10:00:00+05:30",
    )
    return store


def position(
    investor="Amma",
    folio="F1",
    isin="INF001",
    units="10",
    purpose="Retirement",
):
    return Position(
        id=PositionId(investor, folio, isin),
        units=Decimal(units),
        purpose=purpose,
    )


def test_transition_evidence_retains_position_identity_and_purpose(tmp_path):
    evidence = build_transition_evidence(
        [position()],
        [],
        {"INF001": make_store(tmp_path)},
        date(2026, 8, 18),
    )

    row = evidence.positions[0]
    assert row.id == PositionId("Amma", "F1", "INF001")
    assert row.units == Decimal("10")
    assert row.purpose == "Retirement"


def test_transition_evidence_retains_actual_nav_observation_date(tmp_path):
    evidence = build_transition_evidence(
        [position()],
        [],
        {"INF001": make_store(tmp_path)},
        date(2026, 8, 16),
    )

    row = evidence.positions[0]
    assert row.nav == Decimal("109.78")
    assert row.nav_observation_date == date(2026, 8, 14)
    assert row.market_value == Decimal("1097.80")


def test_transition_evidence_does_not_use_requested_date_as_nav_date(tmp_path):
    evidence = build_transition_evidence(
        [position()],
        [],
        {"INF001": make_store(tmp_path)},
        date(2026, 8, 16),
    )

    assert evidence.positions[0].nav_observation_date != date(2026, 8, 16)


def test_transition_evidence_preserves_zero_unit_position_without_fake_valuation(
    tmp_path,
):
    evidence = build_transition_evidence(
        [position(units="0")],
        [],
        {"INF001": make_store(tmp_path)},
        date(2026, 8, 18),
    )

    row = evidence.positions[0]
    assert row.units == Decimal("0")
    assert row.nav is None
    assert row.nav_observation_date is None
    assert row.market_value is None
    assert row.purpose == "Retirement"


def test_transition_evidence_requires_nav_for_active_position(tmp_path):
    with pytest.raises(KeyError, match="INF001"):
        build_transition_evidence(
            [position()],
            [],
            {},
            date(2026, 8, 18),
        )


def test_transition_evidence_preserves_transactions_as_history():
    older = Transaction(
        transaction_date=date(2026, 1, 1),
        event_type="Purchase",
        investor="Amma",
        folio="F1",
        isin="INF001",
        units=Decimal("10"),
        amount=Decimal("1000"),
        price=Decimal("100"),
        source_description="older",
    )
    newer = Transaction(
        transaction_date=date(2026, 2, 1),
        event_type="Switch Out",
        investor="Amma",
        folio="F1",
        isin="INF001",
        units=Decimal("-2"),
        amount=Decimal("220"),
        price=Decimal("110"),
        source_description="newer",
    )

    evidence = build_transition_evidence(
        [],
        [newer, older],
        {},
        date(2026, 8, 18),
    )

    assert evidence.transactions == (older, newer)
    assert evidence.transactions[0].event_type == "Purchase"
