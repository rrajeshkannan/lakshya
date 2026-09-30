import json
from datetime import date
from decimal import Decimal

from lps.position_persistence import read_positions
from lps.positions import PositionId
from lps.reconciliation import reconcile


POSITIONS = """investor,folio,isin,slice,units,nav,market_value,purpose
Amma,F1,SRC,slice-1,100,2,200,Retirement
Amma,F2,TGT,slice-1,10,5,50,Edu_B
"""

TRANSACTIONS = """transaction_date,event_type,investor,folio,isin,units,amount,price,source_description
2026-09-06,Redemption,Amma,F1,SRC,-25,-50,2,On the boundary
2026-09-07,Purchase,Amma,F1,SRC,25,50,2,Not a redemption
2026-09-07,Redemption,Amma,F1,SRC,-25,-50,2,Matched redemption
2026-09-08,Redemption,Amma,F1,OTHER,-25,-50,2,Different holding
"""


def _manifest(orders):
    return {
        "as_of": "2026-09-06",
        "manifest_id": "MAN-2026-09-06-01",
        "contract_version": 7,
        "orders": orders,
    }


def _order(**overrides):
    order = {
        "order_id": "ORD-001",
        "source_investor": "Amma",
        "source_folio": "F1",
        "source_isin": "SRC",
        "units_to_redeem": "25",
        "target_investor": "Amma",
        "target_folio": "F2",
        "target_isin": "TGT",
        "target_slice": "slice-4",
        "purpose": "Marriage",
        "status": "PENDING",
        "settled_at": None,
    }
    order.update(overrides)
    return order


def _write_book(tmp_path, orders, transactions=TRANSACTIONS, positions=POSITIONS):
    manifest = tmp_path / "transition_manifest.json"
    manifest.write_text(json.dumps(_manifest(orders), indent=2) + "\n", encoding="utf-8")
    (tmp_path / "transactions.csv").write_text(transactions, encoding="utf-8")
    positions_path = tmp_path / "positions.csv"
    positions_path.write_text(positions, encoding="utf-8")
    return manifest, positions_path


def test_missing_manifest_leaves_positions_untouched(tmp_path):
    positions = tmp_path / "positions.csv"
    positions.write_text(POSITIONS, encoding="utf-8")
    before = positions.read_bytes()

    result = reconcile(
        manifest_path=tmp_path / "missing.json",
        transactions_path=tmp_path / "transactions.csv",
        positions_path=positions,
    )

    assert result.manifest_present is False
    assert positions.read_bytes() == before


def test_pending_order_without_a_later_redemption_does_not_change_positions(tmp_path):
    manifest, positions = _write_book(tmp_path, [_order(units_to_redeem="999")])
    before_positions = positions.read_bytes()
    before_manifest = manifest.read_bytes()

    result = reconcile(
        manifest_path=manifest,
        transactions_path=tmp_path / "transactions.csv",
        positions_path=positions,
    )

    assert result.fulfilled_this_run == 0
    assert result.pending == 1
    assert result.positions_changed is False
    assert positions.read_bytes() == before_positions
    assert manifest.read_bytes() == before_manifest
    assert json.loads(manifest.read_text(encoding="utf-8"))["orders"][0]["status"] == "PENDING"


def test_exact_redemption_fulfills_order_and_moves_units(tmp_path):
    manifest, positions = _write_book(
        tmp_path,
        [_order(), _order(order_id="ORD-002", units_to_redeem="7")],
    )

    result = reconcile(
        manifest_path=manifest,
        transactions_path=tmp_path / "transactions.csv",
        positions_path=positions,
    )

    assert result.fulfilled_this_run == 1
    assert result.pending == 1
    assert result.fulfilled == 1
    assert result.positions_changed is True
    document = json.loads(manifest.read_text(encoding="utf-8"))
    fulfilled, pending = document["orders"]
    assert fulfilled["status"] == "FULFILLED"
    assert fulfilled["settled_at"] == "2026-09-07"
    assert pending["status"] == "PENDING"
    assert pending["settled_at"] is None

    book = {position.id: position for position in read_positions(positions)}
    source = book[PositionId("Amma", "F1", "SRC", "slice-1")]
    existing_target = book[PositionId("Amma", "F2", "TGT", "slice-1")]
    credited = book[PositionId("Amma", "F2", "TGT", "slice-4")]
    assert source.units == Decimal("75")
    assert source.market_value == Decimal("150")
    assert source.purpose == "Retirement"
    assert existing_target.units == Decimal("10")
    assert credited.units == Decimal("25")
    assert credited.purpose == "Marriage"
    assert credited.nav is None
    assert date.fromisoformat(fulfilled["settled_at"]) == date(2026, 9, 7)


def test_rerunning_reconciliation_is_idempotent(tmp_path):
    manifest, positions = _write_book(tmp_path, [_order()])
    paths = dict(
        manifest_path=manifest,
        transactions_path=tmp_path / "transactions.csv",
        positions_path=positions,
    )

    first = reconcile(**paths)
    after_first_positions = positions.read_bytes()
    after_first_manifest = manifest.read_bytes()
    second = reconcile(**paths)

    assert first.fulfilled_this_run == 1
    assert second.fulfilled_this_run == 0
    assert second.fulfilled == 1
    assert second.pending == 0
    assert second.positions_changed is False
    assert positions.read_bytes() == after_first_positions
    assert manifest.read_bytes() == after_first_manifest
    assert read_positions(positions)[0].units == Decimal("75")


def test_already_fulfilled_order_is_not_applied_again(tmp_path):
    manifest, positions = _write_book(
        tmp_path,
        [_order(status="FULFILLED", settled_at="2026-09-07")],
        positions=POSITIONS.replace("100,2,200", "75,2,150"),
    )
    before_positions = positions.read_bytes()

    result = reconcile(
        manifest_path=manifest,
        transactions_path=tmp_path / "transactions.csv",
        positions_path=positions,
    )

    assert result.fulfilled_this_run == 0
    assert result.fulfilled == 1
    assert result.positions_changed is False
    assert positions.read_bytes() == before_positions
