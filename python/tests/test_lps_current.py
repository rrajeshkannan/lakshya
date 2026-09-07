from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from cas_import_poc.ledger import write_ledger
from cas_import_poc.models import CanonicalTransaction
from lps.current import build_current_snapshot
from lps.nav_evidence import NavEvidenceStore


def tx(**kwargs):
    values = {
        "transaction_date": date(2026, 9, 1),
        "event_type": "Purchase",
        "investor": "Amma",
        "folio": "F1",
        "isin": "INF001",
        "units": Decimal("10"),
        "amount": Decimal("1000"),
        "price": Decimal("100"),
        "source_description": "Purchase",
    }
    values.update(kwargs)
    return CanonicalTransaction(**values)


def write_nav(tmp_path, isin, observations):
    store = NavEvidenceStore(tmp_path / f"{isin}.json")
    store.create(
        isin=isin,
        scheme_code=1001,
        source="test",
        nav=pd.DataFrame({
            "date": pd.to_datetime([item[0] for item in observations]),
            "nav": [Decimal(item[1]) for item in observations],
        }),
        retrieved_at="2026-09-04T10:00:00+05:30",
    )


def test_build_current_snapshot_preserves_both_temporal_boundaries(tmp_path):
    ledger = tmp_path / "canonical_transactions.csv"
    write_ledger(
        ledger,
        [
            tx(transaction_date=date(2026, 8, 1)),
            tx(transaction_date=date(2026, 9, 4), units=Decimal("5")),
        ],
    )
    write_nav(tmp_path, "INF001", [("2026-09-04", "110")])

    snapshot = build_current_snapshot(
        investor="Amma",
        ledger_path=ledger,
        nav_root=tmp_path,
        valuation_as_of_date=date(2026, 9, 4),
    )

    assert snapshot.transaction_through_date == date(2026, 9, 4)
    assert snapshot.valuation_as_of_date == date(2026, 9, 4)
    assert len(snapshot.current_states) == 1
    assert len(snapshot.valuations) == 1
    assert snapshot.total_market_value == Decimal("1650")


def test_build_current_snapshot_uses_applicable_nav_on_or_before_date(tmp_path):
    ledger = tmp_path / "canonical_transactions.csv"
    write_ledger(ledger, [tx()])
    write_nav(tmp_path, "INF001", [("2026-08-14", "109.78"), ("2026-09-04", "110")])

    snapshot = build_current_snapshot(
        investor="Amma",
        ledger_path=ledger,
        nav_root=tmp_path,
        valuation_as_of_date=date(2026, 8, 16),
    )

    assert snapshot.valuations[0].nav_observation_date == date(2026, 8, 14)
    assert snapshot.total_market_value == Decimal("1097.80")


def test_build_current_snapshot_rejects_mixed_investors(tmp_path):
    ledger = tmp_path / "canonical_transactions.csv"
    write_ledger(ledger, [tx(), tx(investor="Appanna")])

    with pytest.raises(ValueError, match="investor mismatch"):
        build_current_snapshot(
            investor="Amma",
            ledger_path=ledger,
            nav_root=tmp_path,
            valuation_as_of_date=date(2026, 9, 4),
        )
