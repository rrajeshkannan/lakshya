from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from cas_import_poc.adapter import adapt_cas, adapt_transaction
from cas_import_poc.models import PositionKey
from cas_import_poc.validation import reconcile_unit_balance


def _transaction(**kwargs):
    defaults = {
        "date": date(2026, 9, 1),
        "description": "Purchase",
        "amount": Decimal("1000"),
        "units": Decimal("10"),
        "nav": Decimal("100"),
        "type": "PURCHASE",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_adapt_purchase_preserves_source_semantics():
    tx = adapt_transaction(
        investor="Amma",
        folio="12345678",
        isin="INF000000000",
        transaction=_transaction(),
    )

    assert tx.transaction_date == date(2026, 9, 1)
    assert tx.event_type == "Purchase"
    assert tx.investor == "Amma"
    assert tx.folio == "12345678"
    assert tx.isin == "INF000000000"
    assert tx.units == Decimal("10")
    assert tx.amount == Decimal("1000")
    assert tx.price == Decimal("100")


def test_adapt_sip_purchase_uses_shared_event_vocabulary():
    tx = adapt_transaction(
        investor="Appanna",
        folio="12345678",
        isin="INF000000000",
        transaction=_transaction(type="PURCHASE_SIP", description="Systematic Investment"),
    )

    assert tx.event_type == "Systematic Investment"


def test_adapt_unknown_parser_type_is_explicit_failure():
    with pytest.raises(ValueError, match="Unsupported casparser transaction type"):
        adapt_transaction(
            investor="Amma",
            folio="12345678",
            isin="INF000000000",
            transaction=_transaction(type="SOMETHING_NEW"),
        )


def test_reconcile_unit_balance_uses_parser_signed_unit_movements():
    result = reconcile_unit_balance(
        Decimal("100"),
        Decimal("115"),
        [
            _transaction(type="PURCHASE", units=Decimal("20")),
            _transaction(type="STAMP_DUTY_TAX", units=None),
            _transaction(type="REDEMPTION", units=Decimal("-5")),
        ],
    )

    assert result.computed_closing_units == Decimal("115")
    assert result.passed


def test_reconcile_unit_balance_detects_mismatch():
    result = reconcile_unit_balance(
        Decimal("100"),
        Decimal("116"),
        [_transaction(type="PURCHASE", units=Decimal("15"))],
    )

    assert result.computed_closing_units == Decimal("115")
    assert not result.passed


def test_position_identity_is_investor_folio_isin():
    key = PositionKey("Amma", "12345678", "INF000000000")

    assert key == PositionKey("Amma", "12345678", "INF000000000")
    assert key != PositionKey("Appanna", "12345678", "INF000000000")
    assert key != PositionKey("Amma", "87654321", "INF000000000")
    assert key != PositionKey("Amma", "12345678", "INF111111111")


def test_adapt_cas_uses_investor_override_for_lakshya_label():
    transaction = _transaction()
    scheme = SimpleNamespace(isin="INF000000000", scheme="Test Fund", transactions=[transaction])
    folio = SimpleNamespace(folio="12345678", schemes=[scheme])
    data = SimpleNamespace(
        investor_info=SimpleNamespace(name="Printed Name"),
        folios=[folio],
    )

    rows = adapt_cas(data, investor_override="Amma")

    assert len(rows) == 1
    assert rows[0].investor == "Amma"


def test_adapt_cas_rejects_scheme_without_isin():
    scheme = SimpleNamespace(isin=None, scheme="Test Fund", transactions=[])
    folio = SimpleNamespace(folio="12345678", schemes=[scheme])
    data = SimpleNamespace(
        investor_info=SimpleNamespace(name="Printed Name"),
        folios=[folio],
    )

    with pytest.raises(ValueError, match="no ISIN"):
        adapt_cas(data)
