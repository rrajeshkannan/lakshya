from datetime import date
from decimal import Decimal

import pandas as pd

from cas_import_poc.ledger import write_ledger
from cas_import_poc.models import CanonicalTransaction
from lps.nav_evidence import NavEvidenceStore
from lps.run_current import build_family_current


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


def test_build_family_current_uses_lps_data_layout(tmp_path):
    investor_root = tmp_path / "lps" / "Amma"
    investor_root.mkdir(parents=True)
    ledger = investor_root / "canonical_transactions.csv"
    write_ledger(ledger, [tx()])

    nav_root = tmp_path / "nav"
    nav_root.mkdir()
    store = NavEvidenceStore(nav_root / "INF001.json")
    store.create(
        isin="INF001",
        scheme_code=1001,
        source="test",
        nav=pd.DataFrame({
            "date": pd.to_datetime(["2026-09-04"]),
            "nav": [Decimal("110")],
        }),
        retrieved_at="2026-09-08T10:00:00+05:30",
    )

    snapshot = build_family_current(
        investor="Amma",
        valuation_as_of_date=date(2026, 9, 8),
        data_root=tmp_path,
    )

    assert snapshot.transaction_through_date == date(2026, 9, 1)
    assert snapshot.valuation_as_of_date == date(2026, 9, 8)
    assert snapshot.total_market_value == Decimal("1100")


def test_build_family_current_fails_clearly_when_ledger_missing(tmp_path):
    try:
        build_family_current(
            investor="Amma",
            valuation_as_of_date=date(2026, 9, 8),
            data_root=tmp_path,
        )
    except FileNotFoundError as exc:
        assert "canonical_transactions.csv" in str(exc)
    else:
        raise AssertionError("Expected missing-ledger failure")
