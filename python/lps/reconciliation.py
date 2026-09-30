"""Settle LTS transition orders against later CAMS redemptions.

The transition manifest is the open order book. A redemption settles pending
orders on its source holding only when it is strictly after the manifest
``as_of`` date. Matching is exact, in this order:

1. one pending order with the same unit quantity;
2. every still-pending order on that holding, when their units sum to the
   redemption;
3. the earliest smaller combination of those orders, in manifest order, whose
   units sum to the redemption.

Fulfilled orders stay fulfilled so a later run does not apply them again.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import combinations
from pathlib import Path

from .position_persistence import read_positions, write_positions
from .positions import PRIMARY_SLICE, Position, PositionId
from .transaction_persistence import read_transactions
from .transactions import Transaction


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "data" / "lps" / "transition_manifest.json"
DEFAULT_TRANSACTIONS_PATH = PROJECT_ROOT / "data" / "lps" / "transactions.csv"
DEFAULT_POSITIONS_PATH = PROJECT_ROOT / "data" / "lps" / "positions.csv"

ORDER_FIELDS = (
    "order_id",
    "source_investor",
    "source_folio",
    "source_isin",
    "units_to_redeem",
    "target_investor",
    "target_folio",
    "target_isin",
    "target_slice",
    "purpose",
    "status",
    "settled_at",
)
PENDING = "PENDING"
FULFILLED = "FULFILLED"
REDEMPTION = "Redemption"


@dataclass(frozen=True)
class ReconciliationResult:
    """Outcome of one reconciliation pass."""

    manifest_present: bool
    as_of: str | None = None
    manifest_id: str | None = None
    order_count: int = 0
    fulfilled_this_run: int = 0
    pending: int = 0
    fulfilled: int = 0
    positions_changed: bool = False


def reconcile(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    transactions_path: Path = DEFAULT_TRANSACTIONS_PATH,
    positions_path: Path = DEFAULT_POSITIONS_PATH,
) -> ReconciliationResult:
    """Match post-``as_of`` CAMS redemptions to pending transition orders.

    Missing manifest: no positions are read or written. Pending orders with
    no matching redemption stay pending and the positions file is left as it
    is. A second pass skips orders already marked ``FULFILLED``.
    """
    if not manifest_path.is_file():
        return ReconciliationResult(manifest_present=False)

    manifest = _load_manifest(manifest_path)
    as_of = date.fromisoformat(manifest["as_of"])
    orders: list[dict[str, object]] = manifest["orders"]
    transactions = read_transactions(transactions_path)
    settlements = _match_pending_orders(orders, transactions, as_of)

    positions_changed = False
    if settlements:
        positions = read_positions(positions_path)
        for order in settlements:
            positions = _apply_settlement(positions, order)
        _replace_positions(positions_path, positions)
        _replace_json(manifest_path, manifest)
        positions_changed = True

    statuses = [str(order["status"]) for order in orders]
    return ReconciliationResult(
        manifest_present=True,
        as_of=str(manifest["as_of"]),
        manifest_id=str(manifest["manifest_id"]),
        order_count=len(orders),
        fulfilled_this_run=len(settlements),
        pending=statuses.count(PENDING),
        fulfilled=statuses.count(FULFILLED),
        positions_changed=positions_changed,
    )


def _match_pending_orders(
    orders: list[dict[str, object]],
    transactions: list[Transaction],
    as_of: date,
) -> list[dict[str, object]]:
    """Mark matched pending orders fulfilled and return them in settlement order."""
    settled: list[dict[str, object]] = []
    ordered = sorted(
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
    for transaction in ordered:
        if transaction.transaction_date <= as_of or not _is_cams_redemption(transaction):
            continue
        matched = _match_redemption(orders, transaction)
        if not matched:
            continue
        settled_at = transaction.transaction_date.isoformat()
        for order in matched:
            order["status"] = FULFILLED
            order["settled_at"] = settled_at
            settled.append(order)
    return settled


def _match_redemption(
    orders: list[dict[str, object]],
    transaction: Transaction,
) -> list[dict[str, object]]:
    """Return the pending orders one redemption settles, if any."""
    pending = [
        order
        for order in orders
        if order["status"] == PENDING and _same_source(order, transaction)
    ]
    if not pending:
        return []
    raw_units = transaction.units
    assert raw_units is not None
    units = -raw_units
    exact = _tier_one_exact(pending, units)
    if exact is not None:
        return [exact]
    aggregated = _tier_two_full_folio(pending, units)
    if aggregated is not None:
        return aggregated
    return _tier_three_subset(pending, units)


def _same_source(order: dict[str, object], transaction: Transaction) -> bool:
    return (
        transaction.investor == order["source_investor"]
        and transaction.folio == order["source_folio"]
        and transaction.isin == order["source_isin"]
    )


def _order_units(order: dict[str, object]) -> Decimal:
    return Decimal(str(order["units_to_redeem"]))


def _tier_one_exact(
    pending: list[dict[str, object]],
    units: Decimal,
) -> dict[str, object] | None:
    """Return the earliest pending order with this exact unit quantity."""
    for order in pending:
        if _order_units(order) == units:
            return order
    return None


def _tier_two_full_folio(
    pending: list[dict[str, object]],
    units: Decimal,
) -> list[dict[str, object]] | None:
    """Return every pending order when the redemption redeems the whole set."""
    if len(pending) < 2:
        return None
    total = sum((_order_units(order) for order in pending), Decimal("0"))
    if total == units:
        return list(pending)
    return None


def _tier_three_subset(
    pending: list[dict[str, object]],
    units: Decimal,
) -> list[dict[str, object]]:
    """Return the earliest proper subset whose units sum to the redemption.

    Combinations follow manifest order. Smaller combinations are tried before
    larger ones, and each size is tried in lexicographic index order. The
    full pending set is tier 2, and a single order is tier 1.
    """
    quantities = [_order_units(order) for order in pending]
    for size in range(2, len(pending)):
        for combo in combinations(range(len(pending)), size):
            if sum((quantities[index] for index in combo), Decimal("0")) == units:
                return [pending[index] for index in combo]
    return []


def _is_cams_redemption(transaction: Transaction) -> bool:
    units = transaction.units
    return (
        transaction.event_type.strip() == REDEMPTION
        and units is not None
        and units < 0
    )


def _apply_settlement(
    positions: list[Position],
    order: dict[str, object],
) -> list[Position]:
    units = Decimal(str(order["units_to_redeem"]))
    updated = list(positions)
    source_index = _source_index(
        updated,
        investor=str(order["source_investor"]),
        folio=str(order["source_folio"]),
        isin=str(order["source_isin"]),
    )
    source = updated[source_index]
    if source.units < units:
        raise ValueError(
            f"Source slice {source.id.key} has {source.units} units, "
            f"cannot settle {units} for {order['order_id']}."
        )
    updated[source_index] = _with_units(source, source.units - units)
    updated = _credit_target(updated, order, units)
    return updated


def _source_index(
    positions: list[Position],
    *,
    investor: str,
    folio: str,
    isin: str,
) -> int:
    matches = [
        index
        for index, position in enumerate(positions)
        if (
            position.id.investor == investor
            and position.id.folio == folio
            and position.id.isin == isin
        )
    ]
    if not matches:
        raise ValueError(
            "No source slice for redemption "
            f"{investor}|{folio}|{isin}."
        )
    if len(matches) == 1:
        return matches[0]
    primary = [
        index for index in matches if positions[index].id.slice == PRIMARY_SLICE
    ]
    if len(primary) == 1:
        return primary[0]
    raise ValueError(
        "Source holding has no single primary slice to redeem: "
        f"{investor}|{folio}|{isin}."
    )


def _credit_target(
    positions: list[Position],
    order: dict[str, object],
    units: Decimal,
) -> list[Position]:
    target_id = PositionId(
        investor=str(order["target_investor"]),
        folio=str(order["target_folio"]),
        isin=str(order["target_isin"]),
        slice=str(order["target_slice"]),
    )
    purpose = str(order["purpose"]).strip() or None
    for index, position in enumerate(positions):
        if position.id != target_id:
            continue
        credited = _with_units(position, position.units + units)
        if credited.purpose is None and purpose is not None:
            credited = Position(
                id=credited.id,
                units=credited.units,
                nav=credited.nav,
                market_value=credited.market_value,
                purpose=purpose,
            )
        positions[index] = credited
        return positions

    positions.append(Position(id=target_id, units=units, purpose=purpose))
    return positions


def _with_units(position: Position, units: Decimal) -> Position:
    market_value = None if position.nav is None else units * position.nav
    return Position(
        id=position.id,
        units=units,
        nav=position.nav,
        market_value=market_value,
        purpose=position.purpose,
    )


def _load_manifest(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Transition manifest must be an object: {path}")
    as_of = payload.get("as_of")
    manifest_id = payload.get("manifest_id")
    if not isinstance(as_of, str) or not as_of.strip():
        raise ValueError(f"Transition manifest as_of must be a date string: {path}")
    date.fromisoformat(as_of)
    if not isinstance(manifest_id, str) or not manifest_id.strip():
        raise ValueError(f"Transition manifest manifest_id is required: {path}")
    contract_version = payload.get("contract_version")
    if isinstance(contract_version, bool) or not isinstance(contract_version, int):
        raise ValueError(f"Transition manifest contract_version must be an integer: {path}")
    orders = payload.get("orders")
    if not isinstance(orders, list):
        raise ValueError(f"Transition manifest orders must be a list: {path}")
    for index, order in enumerate(orders, start=1):
        _validate_order(order, index, path)
    return payload


def _validate_order(order: object, index: int, path: Path) -> None:
    if not isinstance(order, dict):
        raise ValueError(f"Transition order {index} in {path} must be an object.")
    missing = [field for field in ORDER_FIELDS if field not in order]
    if missing:
        raise ValueError(
            f"Transition order {index} in {path} is missing fields: {', '.join(missing)}"
        )
    units = order["units_to_redeem"]
    if not isinstance(units, str) or not units.strip():
        raise ValueError(
            f"Transition order {index} units_to_redeem must be a decimal string."
        )
    quantity = Decimal(units)
    if not quantity.is_finite() or quantity <= 0:
        raise ValueError(f"Transition order {index} units_to_redeem must be positive.")
    status = order["status"]
    settled_at = order["settled_at"]
    if status == PENDING:
        if settled_at is not None:
            raise ValueError(f"Pending transition order {index} cannot have settled_at.")
        return
    if status == FULFILLED:
        if not isinstance(settled_at, str) or not settled_at.strip():
            raise ValueError(f"Fulfilled transition order {index} requires settled_at.")
        date.fromisoformat(settled_at)
        return
    raise ValueError(f"Transition order {index} has unsupported status {status!r}.")


def _replace_json(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _replace_positions(path: Path, positions: list[Position]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    write_positions(temporary, positions)
    temporary.replace(path)


__all__ = [
    "DEFAULT_MANIFEST_PATH",
    "DEFAULT_POSITIONS_PATH",
    "DEFAULT_TRANSACTIONS_PATH",
    "ORDER_FIELDS",
    "ReconciliationResult",
    "reconcile",
]
