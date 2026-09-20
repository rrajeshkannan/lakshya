"""FIFO redemption allocation evidence for LTS.

This module reports which acquisition lots would be consumed by signed unit
movements. It does not calculate tax, mutate LPS state, or assume that a folio
is a permanent tax boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lps.positions import PositionId
from lps.transactions import Transaction
from .physical_transaction_history import transactions_for_holding

ZERO = Decimal("0")


@dataclass(frozen=True)
class FifoRedemptionAllocation:
    """One portion of a disposal allocated to an acquisition transaction."""

    disposal_date: date
    acquisition_date: date
    units: Decimal
    acquisition_amount: Decimal | None
    acquisition_price: Decimal | None
    acquisition_source_description: str


def fifo_redemption_allocations(
    transactions: list[Transaction] | tuple[Transaction, ...],
    position_id: PositionId,
    as_of: date | None = None,
) -> tuple[FifoRedemptionAllocation, ...]:
    """Return deterministic FIFO disposal-to-acquisition allocations."""
    history = transactions_for_holding(transactions, position_id)
    if as_of is not None:
        history = tuple(t for t in history if t.transaction_date <= as_of)

    lots: list[dict[str, object]] = []
    allocations: list[FifoRedemptionAllocation] = []

    for transaction in history:
        units = transaction.units
        if units is None or units == ZERO:
            continue

        if units > ZERO:
            lots.append(
                {
                    "date": transaction.transaction_date,
                    "remaining": units,
                    "amount": transaction.amount,
                    "price": transaction.price,
                    "source": transaction.source_description,
                }
            )
            continue

        disposal = -units
        for lot in lots:
            remaining = lot["remaining"]
            assert isinstance(remaining, Decimal)
            consumed = min(remaining, disposal)
            if consumed:
                allocations.append(
                    FifoRedemptionAllocation(
                        disposal_date=transaction.transaction_date,
                        acquisition_date=lot["date"],
                        units=consumed,
                        acquisition_amount=lot["amount"],
                        acquisition_price=lot["price"],
                        acquisition_source_description=lot["source"],
                    )
                )
                lot["remaining"] = remaining - consumed
                disposal -= consumed
            if disposal == ZERO:
                break

        if disposal != ZERO:
            raise ValueError(
                "Transaction history contains unit disposal exceeding "
                f"available FIFO acquisition units for {position_id} "
                f"as of {as_of or 'latest transaction'}."
            )

    return tuple(allocations)


__all__ = ["FifoRedemptionAllocation", "fifo_redemption_allocations"]
