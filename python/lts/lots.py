"""FIFO lot evidence derived from LPS transaction mechanics.

LPS remains authoritative for transaction -> holding semantics. This module
does not classify event types. It uses the signed unit movement already
present in each LPS Transaction:

    positive units -> creates acquisition quantity
    negative units -> consumes earlier acquisition quantity FIFO

The resulting lots are LTS analytical evidence. They never mutate LPS state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lps.transactions import Transaction
from lps.positions import PositionId
from .physical_transaction_history import transactions_for_holding

ZERO = Decimal("0")


@dataclass(frozen=True)
class HoldingLot:
    """One FIFO acquisition lot for a holding.

    transaction_amount is retained as source transaction evidence. It is not
    asserted to be tax cost basis; that requires a separate evidence-backed
    tax-basis contract.
    """

    transaction_date: date
    units_acquired: Decimal
    units_remaining: Decimal
    transaction_amount: Decimal | None
    transaction_price: Decimal | None
    source_description: str


def fifo_holding_lots(
    transactions: list[Transaction] | tuple[Transaction, ...],
    position_id: PositionId,
    as_of: date | None = None,
) -> tuple[HoldingLot, ...]:
    """Derive FIFO acquisition lots through an observation date.

    Only signed unit movement is interpreted. Event type is deliberately not
    used to decide whether a transaction is an acquisition or disposal.

    A disposal that exceeds the acquisition quantity available through the
    as_of date is a data-quality/unsupported-state error; no synthetic lot is
    created to hide it.
    """
    history = transactions_for_holding(transactions, position_id)
    if as_of is not None:
        history = tuple(t for t in history if t.transaction_date <= as_of)

    lots: list[dict[str, object]] = []

    for transaction in history:
        units = transaction.units
        if units is None or units == ZERO:
            continue

        if units > ZERO:
            lots.append(
                {
                    "transaction_date": transaction.transaction_date,
                    "units_acquired": units,
                    "units_remaining": units,
                    "transaction_amount": transaction.amount,
                    "transaction_price": transaction.price,
                    "source_description": transaction.source_description,
                }
            )
            continue

        disposal = -units
        for lot in lots:
            remaining = lot["units_remaining"]
            assert isinstance(remaining, Decimal)
            consumed = min(remaining, disposal)
            lot["units_remaining"] = remaining - consumed
            disposal -= consumed
            if disposal == ZERO:
                break

        if disposal != ZERO:
            raise ValueError(
                "Transaction history contains unit disposal exceeding "
                f"available FIFO acquisition units for {position_id} "
                f"as of {as_of or 'latest transaction'}."
            )

    return tuple(
        HoldingLot(
            transaction_date=lot["transaction_date"],
            units_acquired=lot["units_acquired"],
            units_remaining=lot["units_remaining"],
            transaction_amount=lot["transaction_amount"],
            transaction_price=lot["transaction_price"],
            source_description=lot["source_description"],
        )
        for lot in lots
        if lot["units_remaining"] > ZERO
    )


__all__ = ["HoldingLot", "fifo_holding_lots"]
