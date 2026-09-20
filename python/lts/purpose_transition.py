"""Purpose-owned, conservation-balanced CURRENT -> TARGET transition mapping.

This module is analytical only. It does not calculate tax, execute transactions,
or mutate LPS state. It preserves Purpose ownership and source provenance while
mapping every current rupee to exactly one TARGET allocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .models import TargetFormation
from .position_bridge import LtsPosition, LtsPositionId, validate_slice_percentages
from .purpose_allocation import validate_purpose_target_allocation

ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
TOLERANCE = Decimal("0.00000001")


class TransitionDisposition(str, Enum):
    RETAIN = "RETAIN"
    REDEEM = "REDEEM"
    REDEEM_LOCKED = "REDEEM_LOCKED"
    INVEST = "INVEST"


class TransitionSourceKind(str, Enum):
    RETAINED_POSITION = "RETAINED_POSITION"
    REDEMPTION_PROCEEDS = "REDEMPTION_PROCEEDS"
    LOCKED_REDEMPTION_PROCEEDS = "LOCKED_REDEMPTION_PROCEEDS"


@dataclass(frozen=True)
class PurposeTransitionRow:
    """Backward-compatible treatment row for a source or target requirement."""

    purpose: str
    source_position_id: LtsPositionId | None
    source_isin: str | None
    destination_isin: str
    disposition: TransitionDisposition
    amount: Decimal
    locked: bool = False


@dataclass(frozen=True)
class TransitionMapping:
    """One conservation-balanced source-to-TARGET mapping edge."""

    purpose: str
    source_position_id: LtsPositionId
    source_isin: str
    source_kind: TransitionSourceKind
    destination_isin: str
    amount: Decimal
    locked: bool = False


@dataclass(frozen=True)
class PurposeTransitionBalance:
    """Conservation evidence for one Purpose."""

    purpose: str
    current_amount: Decimal
    target_amount: Decimal
    mapped_source_amount: Decimal
    mapped_destination_amount: Decimal
    unallocated_source_amount: Decimal
    unfunded_target_amount: Decimal

    @property
    def is_balanced(self) -> bool:
        return (
            abs(self.current_amount - self.target_amount) <= TOLERANCE
            and abs(self.mapped_source_amount - self.current_amount) <= TOLERANCE
            and abs(self.mapped_destination_amount - self.target_amount) <= TOLERANCE
            and self.unallocated_source_amount <= TOLERANCE
            and self.unfunded_target_amount <= TOLERANCE
        )


@dataclass(frozen=True)
class PurposeTransitionPlan:
    """Complete Purpose-owned, conservation-balanced transition result."""

    rows: tuple[PurposeTransitionRow, ...]
    mappings: tuple[TransitionMapping, ...]
    balances: tuple[PurposeTransitionBalance, ...]

    @property
    def total_amount(self) -> Decimal:
        return sum((row.amount for row in self.rows), ZERO)

    @property
    def is_balanced(self) -> bool:
        return all(balance.is_balanced for balance in self.balances)

    @property
    def portfolio_current_amount(self) -> Decimal:
        return sum((balance.current_amount for balance in self.balances), ZERO)

    @property
    def portfolio_target_amount(self) -> Decimal:
        return sum((balance.target_amount for balance in self.balances), ZERO)


def _value(position: LtsPosition) -> Decimal:
    if position.market_value is None:
        raise ValueError(f"Cannot plan transition for unvalued Position {position.id}.")
    if position.market_value < ZERO:
        raise ValueError(f"Position market value cannot be negative: {position.id}.")
    return position.market_value * position.percentage / ONE_HUNDRED


def build_purpose_transition_plan(
    positions: list[LtsPosition],
    formation: TargetFormation,
    *,
    locked_position_ids: set[LtsPositionId] | None = None,
) -> PurposeTransitionPlan:
    """Build a deterministic and fully conservation-balanced transition map.

    Same-Purpose and same-ISIN capital is retained first. Every excess source
    becomes redemption capacity, preserving whether it is currently locked.
    Released capacity is then allocated to remaining target gaps within the
    same Purpose. The function rejects Purpose-level capital imbalance instead
    of silently creating or losing money.
    """
    validate_slice_percentages(positions)
    validate_purpose_target_allocation(formation)
    locked = locked_position_ids or set()

    target: dict[tuple[str, str], Decimal] = {}
    for item in formation.rows:
        key = (item.purpose, item.isin)
        target[key] = target.get(key, ZERO) + item.target_value

    current: dict[tuple[str, str], Decimal] = {}
    purpose_current: dict[str, Decimal] = {}
    purpose_target: dict[str, Decimal] = {}
    for position in positions:
        if position.purpose is None:
            raise ValueError(f"Position has no Purpose attribution: {position.id}")
        amount = _value(position)
        key = (position.purpose, position.id.isin)
        current[key] = current.get(key, ZERO) + amount
        purpose_current[position.purpose] = purpose_current.get(position.purpose, ZERO) + amount
    for (purpose, _isin), amount in target.items():
        purpose_target[purpose] = purpose_target.get(purpose, ZERO) + amount

    purposes = sorted(set(purpose_current) | set(purpose_target))
    for purpose in purposes:
        if abs(purpose_current.get(purpose, ZERO) - purpose_target.get(purpose, ZERO)) > TOLERANCE:
            raise ValueError(
                "Purpose capital must be conserved before transition mapping: "
                f"{purpose}: current={purpose_current.get(purpose, ZERO)}, "
                f"target={purpose_target.get(purpose, ZERO)}"
            )

    target_remaining = dict(target)
    rows: list[PurposeTransitionRow] = []
    mappings: list[TransitionMapping] = []
    released: list[tuple[LtsPosition, Decimal, bool]] = []

    ordered_positions = sorted(
        positions,
        key=lambda item: (
            item.purpose or "",
            item.id.investor,
            item.id.folio,
            item.id.isin,
            item.id.slice,
        ),
    )

    for position in ordered_positions:
        if position.purpose is None:
            continue
        amount = _value(position)
        key = (position.purpose, position.id.isin)
        retained = min(amount, target_remaining.get(key, ZERO))
        target_remaining[key] = target_remaining.get(key, ZERO) - retained
        excess = amount - retained

        if retained > ZERO:
            rows.append(PurposeTransitionRow(
                purpose=position.purpose,
                source_position_id=position.id,
                source_isin=position.id.isin,
                destination_isin=position.id.isin,
                disposition=TransitionDisposition.RETAIN,
                amount=retained,
            ))
            mappings.append(TransitionMapping(
                purpose=position.purpose,
                source_position_id=position.id,
                source_isin=position.id.isin,
                source_kind=TransitionSourceKind.RETAINED_POSITION,
                destination_isin=position.id.isin,
                amount=retained,
            ))

        if excess > ZERO:
            is_locked = position.id in locked
            disposition = TransitionDisposition.REDEEM_LOCKED if is_locked else TransitionDisposition.REDEEM
            source_kind = (
                TransitionSourceKind.LOCKED_REDEMPTION_PROCEEDS
                if is_locked else TransitionSourceKind.REDEMPTION_PROCEEDS
            )
            rows.append(PurposeTransitionRow(
                purpose=position.purpose,
                source_position_id=position.id,
                source_isin=position.id.isin,
                destination_isin=position.id.isin,
                disposition=disposition,
                amount=excess,
                locked=is_locked,
            ))
            released.append((position, excess, is_locked))

    # Retained mappings have already consumed the direct target demand.
    gaps: list[tuple[str, str, Decimal]] = [
        (purpose, isin, amount)
        for (purpose, isin), amount in sorted(target_remaining.items())
        if amount > ZERO
    ]

    gap_index = 0
    for position, released_amount, is_locked in released:
        remaining_source = released_amount
        source_kind = (
            TransitionSourceKind.LOCKED_REDEMPTION_PROCEEDS
            if is_locked else TransitionSourceKind.REDEMPTION_PROCEEDS
        )
        while remaining_source > ZERO and gap_index < len(gaps):
            purpose, destination_isin, gap_amount = gaps[gap_index]
            if purpose != position.purpose:
                gap_index += 1
                continue
            mapped = min(remaining_source, gap_amount)
            mappings.append(TransitionMapping(
                purpose=purpose,
                source_position_id=position.id,
                source_isin=position.id.isin,
                source_kind=source_kind,
                destination_isin=destination_isin,
                amount=mapped,
                locked=is_locked,
            ))
            rows.append(PurposeTransitionRow(
                purpose=purpose,
                source_position_id=position.id,
                source_isin=position.id.isin,
                destination_isin=destination_isin,
                disposition=TransitionDisposition.INVEST,
                amount=mapped,
                locked=is_locked,
            ))
            remaining_source -= mapped
            gap_amount -= mapped
            gaps[gap_index] = (purpose, destination_isin, gap_amount)
            if gap_amount <= ZERO:
                gap_index += 1

        if remaining_source > TOLERANCE:
            raise ValueError(
                "Released capital could not be mapped to a TARGET gap: "
                f"{position.id}, amount={remaining_source}"
            )

    unfunded = [gap for gap in gaps if gap[2] > TOLERANCE]
    if unfunded:
        raise ValueError(f"TARGET gaps remain unfunded: {unfunded}")

    balances: list[PurposeTransitionBalance] = []
    for purpose in purposes:
        purpose_mappings = [item for item in mappings if item.purpose == purpose]
        current_amount = purpose_current.get(purpose, ZERO)
        target_amount = purpose_target.get(purpose, ZERO)
        mapped_source = sum((item.amount for item in purpose_mappings), ZERO)
        mapped_destination = mapped_source
        balance = PurposeTransitionBalance(
            purpose=purpose,
            current_amount=current_amount,
            target_amount=target_amount,
            mapped_source_amount=mapped_source,
            mapped_destination_amount=mapped_destination,
            unallocated_source_amount=current_amount - mapped_source,
            unfunded_target_amount=target_amount - mapped_destination,
        )
        if not balance.is_balanced:
            raise ValueError(f"Purpose transition is not balanced: {balance}")
        balances.append(balance)

    return PurposeTransitionPlan(
        rows=tuple(rows),
        mappings=tuple(mappings),
        balances=tuple(balances),
    )


__all__ = [
    "PurposeTransitionBalance",
    "PurposeTransitionPlan",
    "PurposeTransitionRow",
    "TransitionDisposition",
    "TransitionMapping",
    "TransitionSourceKind",
    "build_purpose_transition_plan",
]
