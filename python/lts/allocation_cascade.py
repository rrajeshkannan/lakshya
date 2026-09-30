"""Allocate current holdings onto LFS purposes with retain-and-cascade rules.

The pipeline is a review plan. It does not redeem, submit orders, or change
LPS state.

1. Aggregate each real holding, Investor + Folio + ISIN, from the Slice-1 bridge.
2. Split that holding where lot evidence says part of it cannot be redeemed.
   ELSS lots purchased less than three years ago are ``ELSS_LOCKED``.
   Non-ELSS equity lots purchased 365 days ago or sooner are ``STCG_LOCKED``.
3. Place current value onto purpose compositions from LFS weights. A holding's
   current purpose tag is not an affinity. Chosen funds, and every locked
   portion, stay ``RETAIN``. Surplus in a chosen fund is kept, and another
   fund's weight in that purpose is reduced so the purpose total still matches
   its capital. Surplus that the purpose cannot absorb is cascaded into
   another purpose. The review rows record those weight changes.
4. Assign ``target_investor`` while materializing slices. ``RETAIN`` stays
   with the holding owner. For each purpose and target fund, redeemed capital
   is routed to whichever holding investor is furthest below an equal share
   of that fund's market value. With Amma and Appanna that share is half.
   Locked inventory above half is left in place, and every redeemed rupee
   in that fund goes to the other investor.
5. Resolve ``target_folio``. Retained lots keep their current folio. Redeemed
   capital reuses a folio the target investor already holds for that fund.
   Fresh reinvestment gets a purpose-specific placeholder, ``NEW_FOLIO_1``
   onward, so goals do not share a new account.
6. Number ``target_slice`` on ``(target_investor, target_folio, target_isin)``.
   Each purpose on that virtual holding gets the next slice, so one target
   position maps to one purpose.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_EVEN
from io import StringIO
from typing import Mapping, Sequence

from lps.positions import Position, PositionId
from lps.transactions import Transaction

from .fund_metadata import FundClassification
from .lots import fifo_holding_lots
from .models import TargetFormation, TransitionDisposition
from .position_bridge import LtsPosition
from .purpose_allocation import validate_purpose_target_allocation

ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
TOLERANCE = Decimal("0.00000001")
ELSS_LOCK_YEARS = 3
STCG_LOCK_DAYS = 365
ELSS_LOCKED = "ELSS_LOCKED"
STCG_LOCKED = "STCG_LOCKED"
STAGE_UNCHANGED = "UNCHANGED"
STAGE_IN_COMPOSITION = "IN_COMPOSITION"
STAGE_CROSS_COMPOSITION = "CROSS_COMPOSITION"
def new_folio_name(index: int) -> str:
    """Return the purpose-isolated placeholder for one fresh reinvestment folio."""
    if index < 1:
        raise ValueError(f"New folio index must be positive: {index}")
    return f"NEW_FOLIO_{index}"


@dataclass(frozen=True)
class TransitionSlice:
    """One virtual slice of a current real holding."""

    current_investor: str
    current_folio: str
    current_isin: str
    target_investor: str
    target_folio: str
    target_isin: str
    target_slice: str
    purpose: str
    disposition: TransitionDisposition
    locked: bool
    percentage: Decimal
    units: Decimal
    nav: Decimal
    market_value: Decimal
    disposition_reason: str | None = None


@dataclass(frozen=True)
class CascadeReviewRow:
    """One composition adjustment or one locked supply portion."""

    record_type: str
    purpose: str
    isin: str
    nominal_weight: Decimal | None
    adjusted_weight: Decimal | None
    nominal_value: Decimal | None
    adjusted_value: Decimal | None
    delta_value: Decimal | None
    stage: str
    review_note: str
    investor: str = ""
    folio: str = ""
    units: Decimal | None = None
    locked: bool | None = None
    disposition_reason: str = ""


@dataclass(frozen=True)
class AllocationCascade:
    """Slice matrix plus the weight-adjustment review."""

    slices: tuple[TransitionSlice, ...]
    review: tuple[CascadeReviewRow, ...]


@dataclass(frozen=True)
class _Holding:
    investor: str
    folio: str
    isin: str
    units: Decimal
    nav: Decimal
    value: Decimal


@dataclass(frozen=True)
class _Portion:
    investor: str
    folio: str
    isin: str
    units: Decimal
    nav: Decimal
    value: Decimal
    locked: bool
    disposition_reason: str | None

    @property
    def holding_key(self) -> tuple[str, str, str]:
        return self.investor, self.folio, self.isin


@dataclass(frozen=True)
class _Draft:
    investor: str
    folio: str
    isin: str
    target_isin: str
    purpose: str
    disposition: TransitionDisposition
    locked: bool
    disposition_reason: str | None
    units: Decimal
    nav: Decimal


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, day=28)


def redemption_lock_reason(
    acquired_on: date,
    as_of: date,
    *,
    is_elss: bool,
    asset_class: str,
) -> str | None:
    """Return the redemption lock for one lot, or None when it may be sold.

    ELSS uses the three-year statutory lock: a lot is locked while ``as_of``
    is still before the third anniversary. Non-ELSS equity uses a 365-day
    short-term lock, and a lot acquired exactly 365 days earlier stays locked.
    Debt and other asset classes are not locked by either rule.
    """
    if acquired_on > as_of:
        raise ValueError(
            f"Lot acquisition {acquired_on.isoformat()} is after as_of {as_of.isoformat()}."
        )
    if is_elss:
        if as_of < _add_years(acquired_on, ELSS_LOCK_YEARS):
            return ELSS_LOCKED
        return None
    if asset_class.strip().lower() == "equity" and (as_of - acquired_on).days <= STCG_LOCK_DAYS:
        return STCG_LOCKED
    return None


def _attributed_units(position: LtsPosition) -> Decimal:
    return position.units * position.percentage / ONE_HUNDRED


def _attributed_value(position: LtsPosition) -> Decimal:
    if position.market_value is None:
        raise ValueError(f"Cannot allocate an unvalued Position: {position.id}")
    return position.market_value * position.percentage / ONE_HUNDRED


def _aggregate_holdings(positions: Sequence[LtsPosition]) -> tuple[_Holding, ...]:
    grouped: dict[tuple[str, str, str], list[LtsPosition]] = defaultdict(list)
    for position in positions:
        units = _attributed_units(position)
        value = _attributed_value(position)
        if units < ZERO or value < ZERO:
            raise ValueError(f"Position units and value cannot be negative: {position.id}")
        if units == ZERO:
            continue
        if value == ZERO:
            raise ValueError(f"Cannot allocate a zero-value holding: {position.id}")
        grouped[(position.id.investor, position.id.folio, position.id.isin)].append(position)

    holdings: list[_Holding] = []
    for key in sorted(grouped):
        rows = grouped[key]
        units = sum((_attributed_units(row) for row in rows), ZERO)
        value = sum((_attributed_value(row) for row in rows), ZERO)
        navs = {row.nav for row in rows}
        nav = next(iter(navs))
        if len(navs) != 1 or nav is None or nav * units != value:
            nav = value / units
        holdings.append(_Holding(
            investor=key[0],
            folio=key[1],
            isin=key[2],
            units=units,
            nav=nav,
            value=value,
        ))
    return tuple(holdings)


def _portions_for_holding(
    holding: _Holding,
    transactions: Sequence[Transaction] | None,
    classifications: Mapping[str, FundClassification] | None,
    as_of: date | None,
) -> tuple[_Portion, ...]:
    if transactions is None:
        return (_portion(holding, holding.units, locked=False, reason=None),)

    if classifications is None or as_of is None:
        raise ValueError("Classifications and as_of are required when transactions are supplied.")
    try:
        classification = classifications[holding.isin]
    except KeyError as exc:
        raise KeyError(f"No fund classification for ISIN {holding.isin}") from exc

    lots = fifo_holding_lots(
        list(transactions),
        PositionId(holding.investor, holding.folio, holding.isin),
        as_of=as_of,
    )
    if not lots:
        raise ValueError(
            "No acquisition lots are available for "
            f"{holding.investor}/{holding.folio}/{holding.isin}."
        )

    locked_by_reason: dict[str, Decimal] = defaultdict(lambda: ZERO)
    unlocked = ZERO
    for lot in lots:
        reason = redemption_lock_reason(
            lot.transaction_date,
            as_of,
            is_elss=classification.is_elss,
            asset_class=classification.asset_class,
        )
        if reason is None:
            unlocked += lot.units_remaining
        else:
            locked_by_reason[reason] += lot.units_remaining

    lot_units = unlocked + sum(locked_by_reason.values(), ZERO)
    if lot_units <= ZERO:
        raise ValueError(
            "Acquisition lots have no remaining units for "
            f"{holding.investor}/{holding.folio}/{holding.isin}."
        )

    if lot_units == holding.units:
        scaled = dict(locked_by_reason)
        unlocked_units = unlocked
    else:
        scaled = {
            reason: units * holding.units / lot_units
            for reason, units in locked_by_reason.items()
        }
        unlocked_units = holding.units - sum(scaled.values(), ZERO)

    portions: list[_Portion] = []
    for reason in sorted(scaled):
        if scaled[reason] > ZERO:
            portions.append(_portion(holding, scaled[reason], locked=True, reason=reason))
    if unlocked_units > ZERO:
        portions.append(_portion(holding, unlocked_units, locked=False, reason=None))
    return tuple(portions)


def _portion(
    holding: _Holding,
    units: Decimal,
    *,
    locked: bool,
    reason: str | None,
) -> _Portion:
    return _Portion(
        investor=holding.investor,
        folio=holding.folio,
        isin=holding.isin,
        units=units,
        nav=holding.nav,
        value=units * holding.nav,
        locked=locked,
        disposition_reason=reason,
    )


def build_folio_directory(
    inventory: Sequence[Position] | Sequence[LtsPosition],
) -> dict[tuple[str, str], str]:
    """Pick one existing folio per (investor, ISIN) for REDEEM destinations.

    Every row in the LPS position book is inventory, including a folio that
    currently holds zero units of that ISIN: it is still a folio the investor
    already has open for that fund. When an investor has more than one folio
    for the same ISIN, the folio with the highest market value is preferred,
    matching "the primary active folio." Ties, and every all-zero case, are
    broken by the lowest folio string so the choice is deterministic.
    """
    best: dict[tuple[str, str], tuple[Decimal, str]] = {}
    for row in inventory:
        key = (row.id.investor, row.id.isin)
        value = row.market_value if row.market_value is not None else ZERO
        candidate = (value, row.id.folio)
        current = best.get(key)
        if current is None or candidate[0] > current[0] or (
            candidate[0] == current[0] and candidate[1] < current[1]
        ):
            best[key] = candidate
    return {key: folio for key, (_value, folio) in best.items()}


def _redeem_folio_plan(
    destinations: Sequence[tuple[str, str, str]],
    folio_directory: Mapping[tuple[str, str], str],
) -> dict[tuple[str, str, str], str]:
    """Map ``(purpose, target investor, target ISIN)`` to a redeem folio.

    A legacy folio the investor already holds for that fund is reused for
    every purpose. Each fresh ``(purpose, investor, fund)`` gets the next
    ``NEW_FOLIO_n`` placeholder, in purpose then investor then ISIN order.
    """
    legacy: dict[tuple[str, str, str], str] = {}
    fresh: set[tuple[str, str, str]] = set()
    for purpose, investor, isin in destinations:
        existing = folio_directory.get((investor, isin))
        key = (purpose, investor, isin)
        if existing is None:
            fresh.add(key)
        else:
            legacy[key] = existing
    plan = dict(legacy)
    for index, key in enumerate(sorted(fresh), start=1):
        plan[key] = new_folio_name(index)
    return plan


def _target_slice_plan(
    positions: Sequence[tuple[str, str, str, str]],
) -> dict[tuple[str, str, str, str], str]:
    """Number one slice per purpose on each ``(investor, folio, ISIN)``.

    ``positions`` are ``(target_investor, target_folio, target_isin, purpose)``.
    Purposes sort by name, so the first purpose on a target holding is
    ``slice-1``.
    """
    purposes: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for investor, folio, isin, purpose in positions:
        purposes[(investor, folio, isin)].add(purpose)
    assigned: dict[tuple[str, str, str, str], str] = {}
    for target in sorted(purposes):
        for index, purpose in enumerate(sorted(purposes[target]), start=1):
            assigned[(*target, purpose)] = f"slice-{index}"
    return assigned


@dataclass(frozen=True)
class _Piece:
    """One draft, or a split of a redeemed draft, aimed at one target investor."""

    draft: _Draft
    target_investor: str
    units: Decimal


def _equal_shares(total: Decimal, investors: Sequence[str]) -> dict[str, Decimal]:
    """Split ``total`` into one share per investor. The last share keeps the remainder."""
    shares: dict[str, Decimal] = {}
    remaining = total
    count = len(investors)
    for index, investor in enumerate(investors):
        if index == count - 1:
            shares[investor] = remaining
        else:
            share = total / Decimal(count)
            shares[investor] = share
            remaining -= share
    return shares


def _split_redeem_piece(
    draft: _Draft,
    remaining_gap: dict[str, Decimal],
    receivers: Sequence[str],
    *,
    single_receiver: bool,
) -> list[_Piece]:
    """Route one redeemed draft to the investors still short of an equal share."""
    if single_receiver:
        investor = receivers[0]
        remaining_gap[investor] = remaining_gap.get(investor, ZERO) - draft.units * draft.nav
        return [_Piece(draft, investor, draft.units)]

    left_units = draft.units
    parts: list[_Piece] = []
    while left_units > ZERO:
        left_value = left_units * draft.nav
        needy = [
            investor
            for investor in receivers
            if remaining_gap.get(investor, ZERO) > TOLERANCE
        ]
        if not needy:
            investor = min(receivers, key=lambda name: (remaining_gap.get(name, ZERO), name))
            parts.append(_Piece(draft, investor, left_units))
            remaining_gap[investor] = remaining_gap.get(investor, ZERO) - left_value
            break
        investor = min(needy, key=lambda name: (-remaining_gap[name], name))
        gap = remaining_gap[investor]
        others_still_need = any(name != investor for name in needy)
        take_units = left_units if not others_still_need or gap >= left_value else left_units * gap / left_value
        if take_units >= left_units:
            parts.append(_Piece(draft, investor, left_units))
            remaining_gap[investor] = gap - left_value
            break
        left_units -= take_units
        remaining_gap[investor] = ZERO
        parts.append(_Piece(draft, investor, take_units))
    return parts


def _equalize_group(group: Sequence[_Draft], investors: Sequence[str]) -> list[_Piece]:
    """Keep retained lots with their owner and split redeemed value toward parity."""
    total = sum((draft.units * draft.nav for draft in group), ZERO)
    shares = _equal_shares(total, investors)
    retained: dict[str, Decimal] = {investor: ZERO for investor in investors}
    retain_pieces: list[_Piece] = []
    redeem: list[_Draft] = []
    for draft in group:
        if draft.disposition is TransitionDisposition.RETAIN:
            retained[draft.investor] = retained.get(draft.investor, ZERO) + draft.units * draft.nav
            retain_pieces.append(_Piece(draft, draft.investor, draft.units))
        else:
            redeem.append(draft)
    if not redeem:
        return retain_pieces

    below = [
        investor
        for investor in investors
        if shares[investor] - retained.get(investor, ZERO) > TOLERANCE
    ]
    if not below:
        below = [min(investors, key=lambda name: (retained.get(name, ZERO), name))]
    remaining_gap = {
        investor: shares[investor] - retained.get(investor, ZERO)
        for investor in below
    }
    pieces = list(retain_pieces)
    for draft in sorted(
        redeem,
        key=lambda item: (item.investor, item.folio, item.isin, item.purpose, item.target_isin),
    ):
        pieces.extend(_split_redeem_piece(
            draft,
            remaining_gap,
            below,
            single_receiver=len(below) == 1,
        ))
    return pieces


def _equalize_target_investors(
    drafts: Sequence[_Draft],
    investors: Sequence[str],
) -> list[_Piece]:
    """Assign a target investor to every draft without moving retained lots.

    One investor, or a book with no redeemed capital, keeps the holding owner.
    Two or more investors share each purpose and target fund equally. Redeemed
    value fills the investor furthest below that share first. When retained
    lots already exceed the share, that investor receives none of the liquid
    capital.
    """
    if len(investors) < 2:
        return [_Piece(draft, draft.investor, draft.units) for draft in drafts]

    grouped: dict[tuple[str, str], list[_Draft]] = defaultdict(list)
    order: list[tuple[str, str]] = []
    for draft in drafts:
        key = (draft.purpose, draft.target_isin)
        if key not in grouped:
            order.append(key)
        grouped[key].append(draft)
    pieces: list[_Piece] = []
    for key in order:
        pieces.extend(_equalize_group(grouped[key], investors))
    return pieces


def _positive(amount: Decimal) -> bool:
    return amount > TOLERANCE


def _allocate_exact(total: Decimal, parts: list[Decimal]) -> list[Decimal]:
    if not parts:
        raise ValueError("Cannot allocate across an empty target list.")
    weight = sum(parts, ZERO)
    if weight <= ZERO:
        raise ValueError("Cannot allocate across zero weights.")
    allocated: list[Decimal] = []
    remaining = total
    for index, part in enumerate(parts):
        if index == len(parts) - 1:
            allocated.append(remaining)
        else:
            share = total * part / weight
            allocated.append(share)
            remaining -= share
    return allocated


def _allocate_values(
    portions: Sequence[_Portion],
    formation: TargetFormation,
    chosen: set[str],
) -> tuple[
    dict[tuple[str, str], Decimal],
    dict[tuple[str, str], Decimal],
    dict[str, Decimal],
    dict[tuple[str, str], Decimal],
    dict[tuple[str, str], Decimal],
]:
    purpose_capital: dict[str, Decimal] = {}
    nominal_value: dict[tuple[str, str], Decimal] = {}
    nominal_weight: dict[tuple[str, str], Decimal] = {}
    for row in formation.rows:
        purpose_capital[row.purpose] = row.target_capital
        nominal_value[(row.purpose, row.isin)] = row.target_value
        nominal_weight[(row.purpose, row.isin)] = row.target_weight

    purposes = sorted(purpose_capital)
    budget_left = dict(purpose_capital)
    assigned: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    unplaced: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for portion in portions:
        if portion.locked or portion.isin in chosen:
            unplaced[portion.isin] += portion.value

    def room(purpose: str, isin: str) -> Decimal:
        other_unplaced = sum(
            (amount for key, amount in unplaced.items() if key != isin),
            ZERO,
        )
        other_budget = sum(
            (amount for key, amount in budget_left.items() if key != purpose),
            ZERO,
        )
        must_keep = other_unplaced - other_budget
        if must_keep < ZERO:
            must_keep = ZERO
        available = budget_left[purpose] - must_keep
        return available if available > ZERO else ZERO

    def place(purpose: str, isin: str, amount: Decimal) -> None:
        budget_left[purpose] -= amount
        assigned[(purpose, isin)] += amount
        unplaced[isin] -= amount

    def place_up_to(isin: str, purpose: str, limit: Decimal) -> bool:
        available = min(limit, room(purpose, isin), unplaced[isin], budget_left[purpose])
        if not _positive(available):
            return False
        place(purpose, isin, available)
        return True

    def isin_order() -> list[str]:
        return sorted(
            (isin for isin, amount in unplaced.items() if _positive(amount)),
            key=lambda isin: (-unplaced[isin], isin),
        )

    def drain(candidate) -> None:
        progressed = True
        while progressed:
            progressed = False
            for isin in isin_order():
                for purpose in candidate(isin):
                    if place_up_to(isin, purpose, unplaced[isin]):
                        progressed = True

    for isin in isin_order():
        homes = sorted(
            (purpose for purpose in purposes if _positive(nominal_value.get((purpose, isin), ZERO))),
            key=lambda purpose: (-nominal_value[(purpose, isin)], purpose),
        )
        for purpose in homes:
            cap = nominal_value[(purpose, isin)] - assigned[(purpose, isin)]
            if _positive(cap):
                place_up_to(isin, purpose, cap)

    def local_purposes(isin: str) -> list[str]:
        return sorted(
            (purpose for purpose in purposes if _positive(nominal_value.get((purpose, isin), ZERO))),
            key=lambda purpose: (-nominal_value[(purpose, isin)], purpose),
        )

    def other_purposes(isin: str) -> list[str]:
        return [
            purpose
            for purpose in purposes
            if not _positive(nominal_value.get((purpose, isin), ZERO))
        ]

    drain(local_purposes)
    drain(other_purposes)

    stranded = {isin: amount for isin, amount in unplaced.items() if _positive(amount)}
    if stranded:
        raise ValueError(f"Retained capital could not be placed: {stranded}")

    funded: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    for purpose in purposes:
        floors = {
            isin: amount
            for (row_purpose, isin), amount in assigned.items()
            if row_purpose == purpose and _positive(amount)
        }
        spent = sum(floors.values(), ZERO)
        remaining = purpose_capital[purpose] - spent
        if not _positive(remaining):
            continue
        gaps = [
            (isin, nominal_value[(purpose, isin)] - floors.get(isin, ZERO))
            for isin in sorted(isin for row_purpose, isin in nominal_value if row_purpose == purpose)
            if nominal_value[(purpose, isin)] - floors.get(isin, ZERO) > TOLERANCE
        ]
        if not gaps:
            raise ValueError(f"Purpose {purpose} has unfilled capital and no composition gap.")
        for isin, share in zip(
            (isin for isin, _gap in gaps),
            _allocate_exact(remaining, [gap for _isin, gap in gaps]),
            strict=True,
        ):
            if _positive(share):
                funded[(purpose, isin)] += share

    retained = {
        key: amount for key, amount in assigned.items() if _positive(amount)
    }
    return retained, dict(funded), purpose_capital, nominal_value, nominal_weight


def _consume(
    portion: _Portion,
    buckets: list[tuple[str, str, Decimal]],
) -> list[tuple[str, str, Decimal, Decimal]]:
    """Split one portion across (purpose, target ISIN, value) buckets.

    Each share is ``(purpose, target ISIN, units, value)``. The last share of
    a portion keeps the remaining units so the holding's units stay exact.
    """
    remaining_units = portion.units
    remaining_value = portion.value
    shares: list[tuple[str, str, Decimal, Decimal]] = []
    for purpose, target_isin, amount in buckets:
        if remaining_value <= ZERO and remaining_units <= ZERO:
            break
        if amount <= ZERO:
            continue
        take_value = min(remaining_value, amount)
        if take_value == remaining_value:
            take_units = remaining_units
            remaining_units = ZERO
            remaining_value = ZERO
        else:
            take_units = portion.units * take_value / portion.value
            remaining_units -= take_units
            remaining_value -= take_value
        shares.append((purpose, target_isin, take_units, take_value))
    if remaining_value > ZERO or remaining_units > ZERO:
        raise ValueError(
            "Portion was not fully assigned: "
            f"{portion.investor}/{portion.folio}/{portion.isin} "
            f"value_left={remaining_value} units_left={remaining_units}"
        )
    return shares


def _drafts_for_portions(
    portions: Sequence[_Portion],
    retained: Mapping[tuple[str, str], Decimal],
    funded: Mapping[tuple[str, str], Decimal],
    chosen: set[str],
) -> list[_Draft]:
    retained_left: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    for key, amount in retained.items():
        retained_left[key] = amount
    funded_left: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    for key, amount in funded.items():
        funded_left[key] = amount

    drafts: list[_Draft] = []
    ordered = sorted(
        portions,
        key=lambda portion: (
            portion.isin,
            not portion.locked,
            portion.investor,
            portion.folio,
            portion.disposition_reason or "",
        ),
    )
    for portion in ordered:
        mandatory = portion.locked or portion.isin in chosen
        if mandatory:
            buckets = [
                (purpose, portion.isin, retained_left[(purpose, portion.isin)])
                for purpose in sorted({key[0] for key in retained_left if key[1] == portion.isin})
            ]
            for purpose, target_isin, units, take_value in _consume(portion, buckets):
                retained_left[(purpose, target_isin)] -= take_value
                drafts.append(_Draft(
                    investor=portion.investor,
                    folio=portion.folio,
                    isin=portion.isin,
                    target_isin=target_isin,
                    purpose=purpose,
                    disposition=TransitionDisposition.RETAIN,
                    locked=portion.locked,
                    disposition_reason=portion.disposition_reason,
                    units=units,
                    nav=portion.nav,
                ))
            continue

        buckets = [
            (purpose, isin, funded_left[(purpose, isin)])
            for purpose, isin in sorted(funded_left)
        ]
        for purpose, target_isin, units, take_value in _consume(portion, buckets):
            funded_left[(purpose, target_isin)] -= take_value
            drafts.append(_Draft(
                investor=portion.investor,
                folio=portion.folio,
                isin=portion.isin,
                target_isin=target_isin,
                purpose=purpose,
                disposition=TransitionDisposition.REDEEM,
                locked=False,
                disposition_reason=None,
                units=units,
                nav=portion.nav,
            ))
    return drafts


def _unit_quantum(_total_units: Decimal) -> Decimal:
    """Display units at 3 decimal places, the precision of the position book.

    Exact rationals stay on the slice objects. The CSV rounds to this quantum
    and leaves the remainder on the last slice of the holding.
    """
    return Decimal("0.001")


def _slices_from_drafts(
    drafts: Sequence[_Draft],
    holdings: Sequence[_Holding],
    folio_directory: Mapping[tuple[str, str], str],
) -> tuple[TransitionSlice, ...]:
    investors = tuple(sorted({holding.investor for holding in holdings}))
    pieces = _equalize_target_investors(drafts, investors)
    redeem_folios = _redeem_folio_plan(
        [
            (piece.draft.purpose, piece.target_investor, piece.draft.target_isin)
            for piece in pieces
            if piece.draft.disposition is TransitionDisposition.REDEEM
        ],
        folio_directory,
    )

    def _folio_for(piece: _Piece) -> str:
        draft = piece.draft
        if draft.disposition is TransitionDisposition.RETAIN:
            return draft.folio
        return redeem_folios[(draft.purpose, piece.target_investor, draft.target_isin)]

    slice_names = _target_slice_plan([
        (piece.target_investor, _folio_for(piece), piece.draft.target_isin, piece.draft.purpose)
        for piece in pieces
    ])
    by_holding: dict[tuple[str, str, str], list[_Piece]] = defaultdict(list)
    for piece in pieces:
        draft = piece.draft
        by_holding[(draft.investor, draft.folio, draft.isin)].append(piece)

    slices: list[TransitionSlice] = []
    for holding in holdings:
        rows = by_holding.get((holding.investor, holding.folio, holding.isin), [])
        rows.sort(key=lambda piece: (
            not piece.draft.locked,
            piece.draft.disposition is not TransitionDisposition.RETAIN,
            piece.draft.purpose,
            piece.draft.target_isin,
            piece.target_investor,
        ))
        if not rows:
            raise ValueError(
                "Holding produced no slices: "
                f"{holding.investor}/{holding.folio}/{holding.isin}"
            )
        remaining_percentage = ONE_HUNDRED
        emitted_units: list[Decimal] = []
        for index, piece in enumerate(rows):
            draft = piece.draft
            last = index == len(rows) - 1
            if last:
                units = holding.units - sum(emitted_units, ZERO)
                percentage = remaining_percentage
            else:
                units = piece.units
                emitted_units.append(units)
                percentage = units / holding.units * ONE_HUNDRED
                remaining_percentage -= percentage
            if units < ZERO:
                raise ValueError(
                    "Slice units went negative while conserving the holding: "
                    f"{holding.investor}/{holding.folio}/{holding.isin}"
                )
            target_folio = _folio_for(piece)
            slices.append(TransitionSlice(
                current_investor=draft.investor,
                current_folio=draft.folio,
                current_isin=draft.isin,
                target_investor=piece.target_investor,
                target_folio=target_folio,
                target_isin=draft.target_isin,
                target_slice=slice_names[(
                    piece.target_investor,
                    target_folio,
                    draft.target_isin,
                    draft.purpose,
                )],
                purpose=draft.purpose,
                disposition=draft.disposition,
                locked=draft.locked,
                percentage=percentage,
                units=units,
                nav=draft.nav,
                market_value=units * draft.nav,
                disposition_reason=draft.disposition_reason,
            ))
    return tuple(slices)


def _review_rows(
    portions: Sequence[_Portion],
    slices: Sequence[TransitionSlice],
    purpose_capital: Mapping[str, Decimal],
    nominal_value: Mapping[tuple[str, str], Decimal],
    nominal_weight: Mapping[tuple[str, str], Decimal],
) -> tuple[CascadeReviewRow, ...]:
    adjusted: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    for item in slices:
        adjusted[(item.purpose, item.target_isin)] += item.market_value

    keys = set(nominal_value) | {key for key, amount in adjusted.items() if _positive(amount)}
    rows: list[CascadeReviewRow] = []
    for purpose, isin in sorted(keys):
        nominal = nominal_value.get((purpose, isin), ZERO)
        actual = adjusted.get((purpose, isin), ZERO)
        capital = purpose_capital[purpose]
        weight = nominal_weight.get((purpose, isin), ZERO)
        delta = actual - nominal
        if abs(delta) <= TOLERANCE:
            actual = nominal
            delta = ZERO
        adjusted_weight = actual / capital if capital > ZERO else ZERO
        if not _positive(nominal) and _positive(actual):
            stage = STAGE_CROSS_COMPOSITION
            note = (
                "Retained capital cascaded into this purpose because its "
                "original compositions could not absorb it."
            )
        elif abs(delta) > TOLERANCE:
            stage = STAGE_IN_COMPOSITION
            if delta > ZERO:
                note = (
                    "Chosen or locked capital retained above the formation "
                    "weight. The surplus is not redeemed."
                )
            else:
                note = (
                    "Weight reduced so this purpose stays at its capital "
                    "while retained holdings are kept."
                )
        else:
            stage = STAGE_UNCHANGED
            note = "Formation weight unchanged."
        rows.append(CascadeReviewRow(
            record_type="COMPOSITION",
            purpose=purpose,
            isin=isin,
            nominal_weight=weight,
            adjusted_weight=adjusted_weight,
            nominal_value=nominal,
            adjusted_value=actual,
            delta_value=delta,
            stage=stage,
            review_note=note,
        ))

    for portion in sorted(
        (portion for portion in portions if portion.locked),
        key=lambda portion: (
            portion.investor,
            portion.folio,
            portion.isin,
            portion.disposition_reason or "",
        ),
    ):
        rows.append(CascadeReviewRow(
            record_type="LOCK",
            purpose="",
            isin=portion.isin,
            nominal_weight=None,
            adjusted_weight=None,
            nominal_value=None,
            adjusted_value=None,
            delta_value=None,
            stage=portion.disposition_reason or "",
            review_note="Lot-level units that cannot be redeemed.",
            investor=portion.investor,
            folio=portion.folio,
            units=portion.units,
            locked=True,
            disposition_reason=portion.disposition_reason or "",
        ))
    return tuple(rows)


def _validate(
    slices: Sequence[TransitionSlice],
    holdings: Sequence[_Holding],
    purpose_capital: Mapping[str, Decimal],
    chosen: set[str],
    folio_directory: Mapping[tuple[str, str], str],
) -> None:
    by_holding: dict[tuple[str, str, str], list[TransitionSlice]] = defaultdict(list)
    by_purpose: dict[str, Decimal] = defaultdict(lambda: ZERO)
    redeem_folios = _redeem_folio_plan(
        [
            (row.purpose, row.target_investor, row.target_isin)
            for row in slices
            if row.disposition is TransitionDisposition.REDEEM
        ],
        folio_directory,
    )
    for item in slices:
        if item.disposition not in (TransitionDisposition.RETAIN, TransitionDisposition.REDEEM):
            raise ValueError(f"Unexpected disposition: {item.disposition}")
        if item.locked and item.disposition is not TransitionDisposition.RETAIN:
            raise ValueError(f"Locked slice cannot be redeemed: {item}")
        if item.current_isin in chosen and item.disposition is not TransitionDisposition.RETAIN:
            raise ValueError(f"Chosen fund cannot be redeemed: {item}")
        if item.disposition is TransitionDisposition.RETAIN and item.target_isin != item.current_isin:
            raise ValueError(f"Retained slice changed ISIN: {item}")
        if item.disposition is TransitionDisposition.RETAIN and item.target_folio != item.current_folio:
            raise ValueError(f"Retained slice changed folio: {item}")
        if item.disposition is TransitionDisposition.RETAIN and item.target_investor != item.current_investor:
            raise ValueError(f"Retained slice changed investor: {item}")
        if item.disposition is TransitionDisposition.REDEEM:
            expected_folio = redeem_folios[(item.purpose, item.target_investor, item.target_isin)]
            if item.target_folio != expected_folio:
                raise ValueError(f"Redeemed slice resolved to the wrong target folio: {item}")
        if item.market_value != item.units * item.nav:
            raise ValueError(f"Slice market value is not units * nav: {item}")
        by_holding[(item.current_investor, item.current_folio, item.current_isin)].append(item)
        by_purpose[item.purpose] += item.market_value

    holding_index = {(row.investor, row.folio, row.isin): row for row in holdings}
    if set(by_holding) != set(holding_index):
        raise ValueError("Slices do not cover the same real holdings as the supply.")

    for key, rows in by_holding.items():
        holding = holding_index[key]
        units = sum((row.units for row in rows), ZERO)
        percentage = sum((row.percentage for row in rows), ZERO)
        if units != holding.units:
            raise ValueError(f"Slice units do not sum to the holding: {key}: {units} != {holding.units}")
        if percentage != ONE_HUNDRED:
            raise ValueError(f"Slice percentages do not sum to 100: {key}: {percentage}")

    for purpose, capital in purpose_capital.items():
        actual = by_purpose.get(purpose, ZERO)
        if abs(actual - capital) > TOLERANCE:
            raise ValueError(
                f"Purpose allocation does not match its capital: {purpose}: {actual} != {capital}"
            )

    purposes_by_position: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for item in slices:
        purposes_by_position[(item.target_investor, item.target_folio, item.target_isin)][
            item.purpose
        ].add(item.target_slice)
    for target, purpose_slices in purposes_by_position.items():
        for purpose, names in purpose_slices.items():
            if len(names) != 1:
                raise ValueError(
                    f"Purpose {purpose} uses more than one slice on {target}: {sorted(names)}"
                )
        ordered = sorted(purpose_slices)
        for index, purpose in enumerate(ordered, start=1):
            actual = next(iter(purpose_slices[purpose]))
            expected = f"slice-{index}"
            if actual != expected:
                raise ValueError(
                    f"Target slice for {target} purpose {purpose} is {actual}, expected {expected}"
                )


def build_allocation_cascade(
    positions: Sequence[LtsPosition],
    formation: TargetFormation,
    *,
    transactions: Sequence[Transaction] | None = None,
    classifications: Mapping[str, FundClassification] | None = None,
    as_of: date | None = None,
    existing_positions: Sequence[Position] | None = None,
) -> AllocationCascade:
    """Build the retain-and-cascade slice plan for one CURRENT book.

    Purpose capital and composition weights come from ``formation``. Current
    purpose tags on ``positions`` are ignored when choosing a destination.
    ``existing_positions`` is the full LPS position book, including
    zero-unit rows, used to resolve REDEEM ``target_folio``. When omitted,
    the active ``positions`` supplied to this call are used instead.
    """
    validate_purpose_target_allocation(formation)
    folio_directory = build_folio_directory(
        existing_positions if existing_positions is not None else positions
    )
    holdings = _aggregate_holdings(positions)
    if not holdings:
        raise ValueError("Allocation cascade requires at least one holding.")

    purpose_capital: dict[str, Decimal] = {}
    for row in formation.rows:
        purpose_capital[row.purpose] = row.target_capital
    supply_value = sum((holding.value for holding in holdings), ZERO)
    capital_value = sum(purpose_capital.values(), ZERO)
    if abs(supply_value - capital_value) > TOLERANCE:
        raise ValueError(
            "Holding value and purpose capital differ: "
            f"holdings={supply_value}, purposes={capital_value}"
        )

    chosen = {row.isin for row in formation.rows}
    portions = [
        portion
        for holding in holdings
        for portion in _portions_for_holding(holding, transactions, classifications, as_of)
    ]
    retained, funded, purpose_capital, nominal_value, nominal_weight = _allocate_values(
        portions,
        formation,
        chosen,
    )
    drafts = _drafts_for_portions(portions, retained, funded, chosen)
    slices = _slices_from_drafts(drafts, holdings, folio_directory)
    review = _review_rows(
        portions,
        slices,
        purpose_capital,
        nominal_value,
        nominal_weight,
    )
    _validate(slices, holdings, purpose_capital, chosen, folio_directory)
    return AllocationCascade(slices=slices, review=review)


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value.normalize(), "f")


def _display_slices(slices: Sequence[TransitionSlice]) -> list[TransitionSlice]:
    """Round slice units to the holding's precision without changing totals.

    The last slice of each holding keeps the remaining units and percentage,
    so a reader summing the CSV still gets the real holding and 100%.
    """
    grouped: dict[tuple[str, str, str], list[TransitionSlice]] = defaultdict(list)
    order: list[tuple[str, str, str]] = []
    for item in slices:
        key = (item.current_investor, item.current_folio, item.current_isin)
        if key not in grouped:
            order.append(key)
        grouped[key].append(item)

    displayed: list[TransitionSlice] = []
    percentage_quantum = Decimal("0.000001")
    for key in order:
        rows = grouped[key]
        total_units = sum((row.units for row in rows), ZERO)
        quantum = _unit_quantum(total_units)
        book_units = total_units.quantize(quantum, rounding=ROUND_HALF_EVEN)
        remaining_units = book_units
        remaining_percentage = ONE_HUNDRED
        for index, item in enumerate(rows):
            if index == len(rows) - 1:
                units = remaining_units
                percentage = remaining_percentage
            else:
                units = item.units.quantize(quantum, rounding=ROUND_HALF_EVEN)
                if units < ZERO:
                    units = ZERO
                if units > remaining_units:
                    units = remaining_units
                percentage = (units / book_units * ONE_HUNDRED).quantize(
                    percentage_quantum,
                    rounding=ROUND_DOWN,
                )
                remaining_units -= units
                remaining_percentage -= percentage
            displayed.append(TransitionSlice(
                current_investor=item.current_investor,
                current_folio=item.current_folio,
                current_isin=item.current_isin,
                target_investor=item.target_investor,
                target_folio=item.target_folio,
                target_isin=item.target_isin,
                target_slice=item.target_slice,
                purpose=item.purpose,
                disposition=item.disposition,
                locked=item.locked,
                percentage=percentage,
                units=units,
                nav=item.nav,
                market_value=units * item.nav,
                disposition_reason=item.disposition_reason,
            ))
    return displayed


def export_transition_slices_csv(
    slices: Sequence[TransitionSlice],
) -> str:
    """Return the 14-column transition slice CSV."""
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "current_investor",
        "current_folio",
        "current_isin",
        "target_investor",
        "target_folio",
        "target_isin",
        "target_slice",
        "purpose",
        "disposition",
        "locked",
        "percentage",
        "units",
        "nav",
        "market_value",
    ])
    for item in _display_slices(slices):
        writer.writerow([
            item.current_investor,
            item.current_folio,
            item.current_isin,
            item.target_investor,
            item.target_folio,
            item.target_isin,
            item.target_slice,
            item.purpose,
            item.disposition.value,
            str(item.locked).lower(),
            _format_decimal(item.percentage),
            _format_decimal(item.units),
            _format_decimal(item.nav),
            _format_decimal(item.market_value),
        ])
    return output.getvalue()


def _display_review(rows: Sequence[CascadeReviewRow]) -> list[CascadeReviewRow]:
    """Round review money to 7 decimal places without losing a purpose total."""
    money = Decimal("0.0000001")
    weight_quantum = Decimal("0.000001")
    composition = [row for row in rows if row.record_type == "COMPOSITION"]
    locks = [row for row in rows if row.record_type != "COMPOSITION"]
    by_purpose: dict[str, list[CascadeReviewRow]] = defaultdict(list)
    for row in composition:
        by_purpose[row.purpose].append(row)

    displayed: list[CascadeReviewRow] = []
    for purpose in sorted(by_purpose):
        group = by_purpose[purpose]
        capital = sum((row.nominal_value or ZERO for row in group), ZERO).quantize(
            money,
            rounding=ROUND_HALF_EVEN,
        )
        unchanged = all(row.stage == STAGE_UNCHANGED for row in group)
        remaining_nominal = capital
        remaining_actual = capital
        remaining_weight = Decimal("1")
        for index, row in enumerate(group):
            last = index == len(group) - 1
            nominal_weight = (row.nominal_weight or ZERO).quantize(weight_quantum, rounding=ROUND_HALF_EVEN)
            if last:
                nominal = remaining_nominal
                actual = remaining_actual
                adjusted_weight = nominal_weight if unchanged else remaining_weight
            else:
                nominal = (row.nominal_value or ZERO).quantize(money, rounding=ROUND_HALF_EVEN)
                actual = nominal if unchanged else (row.adjusted_value or ZERO).quantize(
                    money,
                    rounding=ROUND_HALF_EVEN,
                )
                if nominal > remaining_nominal:
                    nominal = remaining_nominal
                if actual > remaining_actual:
                    actual = remaining_actual
                if unchanged or capital <= ZERO:
                    adjusted_weight = nominal_weight
                else:
                    adjusted_weight = (actual / capital).quantize(weight_quantum, rounding=ROUND_HALF_EVEN)
                    if adjusted_weight > remaining_weight:
                        adjusted_weight = remaining_weight
                remaining_nominal -= nominal
                remaining_actual -= actual
                remaining_weight -= adjusted_weight
            if unchanged:
                actual = nominal
                adjusted_weight = nominal_weight
            delta = actual - nominal
            displayed.append(CascadeReviewRow(
                record_type=row.record_type,
                purpose=row.purpose,
                isin=row.isin,
                nominal_weight=nominal_weight,
                adjusted_weight=adjusted_weight,
                nominal_value=nominal,
                adjusted_value=actual,
                delta_value=delta,
                stage=row.stage,
                review_note=row.review_note,
            ))
    displayed.extend(locks)
    return displayed


def export_cascade_review_csv(rows: Sequence[CascadeReviewRow]) -> str:
    """Return the composition and lock review blueprint."""
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "record_type",
        "purpose",
        "isin",
        "nominal_weight",
        "adjusted_weight",
        "nominal_value",
        "adjusted_value",
        "delta_value",
        "stage",
        "review_note",
        "investor",
        "folio",
        "units",
        "locked",
        "disposition_reason",
    ])
    for row in _display_review(rows):
        writer.writerow([
            row.record_type,
            row.purpose,
            row.isin,
            _format_decimal(row.nominal_weight),
            _format_decimal(row.adjusted_weight),
            _format_decimal(row.nominal_value),
            _format_decimal(row.adjusted_value),
            _format_decimal(row.delta_value),
            row.stage,
            row.review_note,
            row.investor,
            row.folio,
            _format_decimal(row.units),
            "" if row.locked is None else str(row.locked).lower(),
            row.disposition_reason,
        ])
    return output.getvalue()


__all__ = [
    "ELSS_LOCKED",
    "STCG_LOCKED",
    "new_folio_name",
    "STAGE_CROSS_COMPOSITION",
    "STAGE_IN_COMPOSITION",
    "STAGE_UNCHANGED",
    "AllocationCascade",
    "CascadeReviewRow",
    "TransitionSlice",
    "build_allocation_cascade",
    "build_folio_directory",
    "export_cascade_review_csv",
    "export_transition_slices_csv",
    "redemption_lock_reason",
]
