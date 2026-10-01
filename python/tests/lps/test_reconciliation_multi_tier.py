import json
from decimal import Decimal

import pytest

from lps.position_persistence import read_positions
from lps.positions import PositionId
from lps.reconciliation import reconcile


FOLIO_A = ("Amma", "10391853 / 47", "INF109K01BL4")
FOLIO_B = ("Amma", "12799161 / 64", "INF179K01608")

POSITIONS = """investor,folio,isin,slice,units,nav,market_value,purpose
Amma,10391853 / 47,INF109K01BL4,slice-1,4569.681,1,4569.681,Retirement
Amma,12799161 / 64,INF179K01608,slice-1,303.000,1,303.000,Marriage
"""

TRANSACTION_HEADER = (
    "transaction_date,event_type,investor,folio,isin,units,amount,price,source_description\n"
)


def _order(order_id, source, units, target, purpose):
    investor, folio, isin = source
    target_investor, target_folio, target_isin, target_slice = target
    return {
        "order_id": order_id,
        "source_investor": investor,
        "source_folio": folio,
        "source_isin": isin,
        "units_to_redeem": units,
        "target_investor": target_investor,
        "target_folio": target_folio,
        "target_isin": target_isin,
        "target_slice": target_slice,
        "purpose": purpose,
        "status": "PENDING",
        "settled_at": None,
    }


def _orders():
    return [
        _order("ORD-001", FOLIO_A, "1209.408", ("Amma", "11002736", "INF879O01027", "slice-1"), "Edu_B"),
        _order("ORD-002", FOLIO_A, "3360.273", ("Appanna", "11002746", "INF879O01027", "slice-1"), "Edu_B"),
        _order("ORD-003", FOLIO_B, "36.520", ("Amma", "11002736", "INF879O01027", "slice-4"), "Marriage"),
        _order("ORD-004", FOLIO_B, "53.025", ("Amma", "13393503", "INF879O01100", "slice-4"), "Marriage"),
        _order("ORD-005", FOLIO_B, "7.575", ("Amma", "51025894395 / 0", "INF966L01887", "slice-4"), "Marriage"),
        _order("ORD-006", FOLIO_B, "90.900", ("Appanna", "11002746", "INF879O01027", "slice-4"), "Marriage"),
        _order("ORD-007", FOLIO_B, "53.025", ("Appanna", "13394210", "INF879O01100", "slice-4"), "Marriage"),
        _order("ORD-008", FOLIO_B, "7.575", ("Appanna", "51025826366 / 0", "INF966L01887", "slice-4"), "Marriage"),
        _order("ORD-009", FOLIO_B, "54.380", ("Appanna", "NEW_FOLIO_1", "INF174K01LT0", "slice-1"), "Retirement"),
    ]


def _redemptions(*rows):
    lines = []
    for traded_on, source, units, description in rows:
        investor, folio, isin = source
        lines.append(
            f"{traded_on},Redemption,{investor},{folio},{isin},{units},,,{description}"
        )
    return TRANSACTION_HEADER + "\n".join(lines) + "\n"


def _orders_by_id(manifest_path):
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {order["order_id"]: order for order in document["orders"]}


def _position_units(positions_path):
    return {
        position.id: position.units
        for position in read_positions(positions_path)
    }


def _target_id(order):
    return PositionId(
        order["target_investor"],
        order["target_folio"],
        order["target_isin"],
        order["target_slice"],
    )


@pytest.fixture
def transition_book(tmp_path):
    def build(transactions):
        manifest_path = tmp_path / "transition_manifest.json"
        positions_path = tmp_path / "positions.csv"
        transactions_path = tmp_path / "transactions.csv"
        manifest_path.write_text(
            json.dumps(
                {
                    "as_of": "2026-09-06",
                    "manifest_id": "MAN-2026-09-06-01",
                    "contract_version": 7,
                    "orders": _orders(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        positions_path.write_text(POSITIONS, encoding="utf-8")
        transactions_path.write_text(transactions, encoding="utf-8")
        return {
            "manifest_path": manifest_path,
            "positions_path": positions_path,
            "transactions_path": transactions_path,
        }

    return build


def _reconcile(book):
    return reconcile(
        manifest_path=book["manifest_path"],
        transactions_path=book["transactions_path"],
        positions_path=book["positions_path"],
    )


def test_exact_one_to_one_match(transition_book):
    book = transition_book(
        _redemptions(("2026-09-07", FOLIO_A, "-1209.408", "Single order redemption"))
    )

    result = _reconcile(book)

    assert result.fulfilled_this_run == 1
    orders = _orders_by_id(book["manifest_path"])
    assert orders["ORD-001"]["status"] == "FULFILLED"
    assert orders["ORD-001"]["settled_at"] == "2026-09-07"
    assert orders["ORD-002"]["status"] == "PENDING"
    units = _position_units(book["positions_path"])
    assert units[PositionId(*FOLIO_A, "slice-1")] == Decimal("3360.273")
    assert units[_target_id(orders["ORD-001"])] == Decimal("1209.408")
    assert PositionId(*FOLIO_B, "slice-1") in units
    assert units[PositionId(*FOLIO_B, "slice-1")] == Decimal("303.000")


def test_full_folio_aggregated_match(transition_book):
    book = transition_book(
        _redemptions(("2026-09-08", FOLIO_B, "-303.000", "Full folio redemption"))
    )

    result = _reconcile(book)

    orders = _orders_by_id(book["manifest_path"])
    folio_orders = [orders[f"ORD-{index:03d}"] for index in range(3, 10)]
    assert result.fulfilled_this_run == 7
    assert [order["status"] for order in folio_orders] == ["FULFILLED"] * 7
    assert {order["settled_at"] for order in folio_orders} == {"2026-09-08"}
    assert orders["ORD-001"]["status"] == "PENDING"
    assert orders["ORD-002"]["status"] == "PENDING"
    units = _position_units(book["positions_path"])
    assert units[PositionId(*FOLIO_B, "slice-1")] == Decimal("0.000")
    assert units[PositionId(*FOLIO_A, "slice-1")] == Decimal("4569.681")
    for order in folio_orders:
        assert units[_target_id(order)] == Decimal(order["units_to_redeem"])


def test_partial_subset_sum_match(transition_book):
    book = transition_book(
        _redemptions(("2026-09-09", FOLIO_B, "-97.120", "Partial subset redemption"))
    )

    result = _reconcile(book)

    orders = _orders_by_id(book["manifest_path"])
    assert result.fulfilled_this_run == 3
    for order_id in ("ORD-003", "ORD-004", "ORD-005"):
        assert orders[order_id]["status"] == "FULFILLED"
        assert orders[order_id]["settled_at"] == "2026-09-09"
    for order_id in ("ORD-006", "ORD-007", "ORD-008", "ORD-009"):
        assert orders[order_id]["status"] == "PENDING"
        assert orders[order_id]["settled_at"] is None
    units = _position_units(book["positions_path"])
    assert units[PositionId(*FOLIO_B, "slice-1")] == Decimal("205.880")
    fulfilled_units = sum(
        (Decimal(orders[order_id]["units_to_redeem"]) for order_id in ("ORD-003", "ORD-004", "ORD-005")),
        Decimal("0"),
    )
    assert fulfilled_units == Decimal("97.120")
    for order_id in ("ORD-003", "ORD-004", "ORD-005"):
        assert units[_target_id(orders[order_id])] == Decimal(orders[order_id]["units_to_redeem"])
    for order_id in ("ORD-006", "ORD-007", "ORD-008", "ORD-009"):
        assert _target_id(orders[order_id]) not in units


def test_staggered_multi_day_execution(transition_book):
    book = transition_book(
        _redemptions(("2026-09-09", FOLIO_B, "-97.120", "First execution day"))
    )

    first = _reconcile(book)
    after_first = _orders_by_id(book["manifest_path"])
    units_after_first = _position_units(book["positions_path"])

    assert first.fulfilled_this_run == 3
    assert after_first["ORD-003"]["status"] == "FULFILLED"
    assert after_first["ORD-006"]["status"] == "PENDING"
    assert units_after_first[PositionId(*FOLIO_B, "slice-1")] == Decimal("205.880")

    book["transactions_path"].write_text(
        _redemptions(
            ("2026-09-09", FOLIO_B, "-97.120", "First execution day"),
            ("2026-09-11", FOLIO_B, "-205.880", "Second execution day"),
        ),
        encoding="utf-8",
    )
    second = _reconcile(book)

    orders = _orders_by_id(book["manifest_path"])
    units = _position_units(book["positions_path"])
    assert second.fulfilled_this_run == 4
    assert second.pending == 2
    assert second.fulfilled == 7
    for order_id in ("ORD-003", "ORD-004", "ORD-005"):
        assert orders[order_id]["settled_at"] == "2026-09-09"
    for order_id in ("ORD-006", "ORD-007", "ORD-008", "ORD-009"):
        assert orders[order_id]["status"] == "FULFILLED"
        assert orders[order_id]["settled_at"] == "2026-09-11"
    assert units[PositionId(*FOLIO_A, "slice-1")] == Decimal("4569.681")
    assert units[PositionId(*FOLIO_B, "slice-1")] == Decimal("0.000")
    moved = Decimal("0")
    for index in range(3, 10):
        order = orders[f"ORD-{index:03d}"]
        credited = units[_target_id(order)]
        assert credited == Decimal(order["units_to_redeem"])
        moved += credited
    assert moved == Decimal("303.000")
    assert units_after_first[_target_id(orders["ORD-003"])] == Decimal("36.520")
