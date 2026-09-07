from datetime import date
from decimal import Decimal

from cas_import_poc.ledger import read_ledger, write_ledger
from cas_import_poc.models import Transaction


def _transaction(**kwargs):
    values = {
        "transaction_date": date(2026, 9, 1),
        "event_type": "Purchase",
        "investor": "Amma",
        "folio": "12345678",
        "isin": "INF000000000",
        "units": Decimal("10.500"),
        "amount": Decimal("1000.25"),
        "price": Decimal("95.2619047619"),
        "source_description": "Purchase",
    }
    values.update(kwargs)
    return Transaction(**values)


def test_ledger_round_trip_preserves_transactions_for_multiple_investors(tmp_path):
    transactions = [
        _transaction(),
        _transaction(
            investor="Appanna",
            transaction_date=date(2026, 9, 2),
            event_type="Redemption",
            units=Decimal("-2.500"),
            amount=Decimal("-250.00"),
            source_description="Redemption less STT",
        ),
        _transaction(
            transaction_date=date(2026, 9, 3),
            event_type="Stamp Duty",
            units=None,
            amount=Decimal("-1.00"),
            price=None,
            source_description="Stamp Duty",
        ),
    ]
    path = tmp_path / "transactions.csv"

    write_ledger(path, transactions)

    assert read_ledger(path) == sorted(
        transactions,
        key=lambda transaction: (
            transaction.transaction_date,
            transaction.investor,
            transaction.folio,
            transaction.isin,
            transaction.event_type,
            transaction.source_description,
        ),
    )


def test_ledger_writes_expected_transaction_columns(tmp_path):
    path = tmp_path / "transactions.csv"
    write_ledger(path, [_transaction()])

    assert path.read_text(encoding="utf-8").splitlines()[0] == (
        "transaction_date,event_type,investor,folio,isin,units,amount,price,source_description"
    )


def test_ledger_rejects_unexpected_columns(tmp_path):
    path = tmp_path / "transactions.csv"
    path.write_text("investor,isin\nAmma,INF000000000\n", encoding="utf-8")

    try:
        read_ledger(path)
    except ValueError as exc:
        assert "unexpected column layout" in str(exc)
    else:
        raise AssertionError("Expected invalid transactions layout to fail")
