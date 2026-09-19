"""Per-holding transition constraint evidence.

This module deliberately works at one LTS Position (holding line) at a time.
It does not choose a transition action. It reports consequences that a later
proposal may consume.

Tax rates/slabs are outside LTS. The analysis exposes gain, holding
classification when its threshold is supplied, WAIT-UNTIL when waiting would
cross that threshold, and ELSS lock-in availability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .lots import HoldingLot, fifo_holding_lots
from lps.positions import Position, PositionId
from lps.transactions import Transaction

ZERO = Decimal("0")


@dataclass(frozen=True)
class HoldingTaxConstraint:
    """Minimal fund-specific tax/lock-in facts supplied to LTS.

    long_term_holding_months is evidence supplied by the fund/tax metadata
    boundary. LTS does not infer it from a fund name.
    """

    isin: str
    is_elss: bool = False
    elss_lock_in_years: int = 3
    long_term_holding_months: int | None = None


@dataclass(frozen=True)
class LotTaxAnalysis:
    """Tax-relevant consequence for one remaining FIFO acquisition lot."""

    acquired_on: date
    units: Decimal
    cost_basis: Decimal | None
    current_value: Decimal | None
    gain: Decimal | None
    classification: str | None
    wait_until: date | None
    elss_locked_until: date | None


@dataclass(frozen=True)
class HoldingConstraintAnalysis:
    """Constraint analysis for one holding line / LTS Position."""

    holding_id: PositionId
    as_of: date
    lots: tuple[LotTaxAnalysis, ...]
    total_gain: Decimal | None
    classification: str | None
    wait_until: date | None
    elss_locked: bool


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    import calendar

    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        # 29-Feb -> 28-Feb in a non-leap year.
        return value.replace(year=value.year + years, day=28)


def _lot_cost_basis(lot: HoldingLot) -> Decimal | None:
    if lot.transaction_amount is None:
        return None
    if lot.units_acquired <= ZERO:
        return None
    return lot.transaction_amount * lot.units_remaining / lot.units_acquired


def analyze_holding(
    position: Position,
    transactions: list[Transaction] | tuple[Transaction, ...],
    as_of: date,
    constraint: HoldingTaxConstraint,
) -> HoldingConstraintAnalysis:
    """Analyse the remaining lots behind one holding line.

    Current value is allocated to each lot using the Position's observed
    market value pro-rata by remaining units. Transaction amount is carried
    into gain calculation only as source acquisition-cost evidence; it is not
    a universal statutory tax-basis engine.
    """
    if constraint.isin != position.id.isin:
        raise ValueError(
            f"Constraint ISIN {constraint.isin} does not match Position "
            f"{position.id.isin}."
        )

    lots = fifo_holding_lots(transactions, position.id, as_of=as_of)

    if not lots:
        return HoldingConstraintAnalysis(
            holding_id=position.id,
            as_of=as_of,
            lots=(),
            total_gain=ZERO,
            classification=None,
            wait_until=None,
            elss_locked=False,
        )

    if position.units < ZERO:
        raise ValueError(f"Position units cannot be negative: {position.id}")

    if position.market_value is not None and position.units > ZERO:
        nav = position.market_value / position.units
    else:
        nav = None

    analyses: list[LotTaxAnalysis] = []
    gains: list[Decimal] = []
    classifications: list[str] = []
    waits: list[date] = []
    locked = False

    for lot in lots:
        cost_basis = _lot_cost_basis(lot)
        current_value = lot.units_remaining * nav if nav is not None else None
        gain = (
            current_value - cost_basis
            if current_value is not None and cost_basis is not None
            else None
        )
        if gain is not None:
            gains.append(gain)

        classification = None
        wait_until = None
        if constraint.long_term_holding_months is not None:
            long_term_on = _add_months(
                lot.transaction_date,
                constraint.long_term_holding_months,
            )
            classification = "LTCG" if as_of >= long_term_on else "STCG"
            if classification == "STCG":
                wait_until = long_term_on
                waits.append(long_term_on)
            classifications.append(classification)

        elss_locked_until = None
        if constraint.is_elss:
            elss_locked_until = _add_years(
                lot.transaction_date,
                constraint.elss_lock_in_years,
            )
            if as_of < elss_locked_until:
                locked = True

        analyses.append(
            LotTaxAnalysis(
                acquired_on=lot.transaction_date,
                units=lot.units_remaining,
                cost_basis=cost_basis,
                current_value=current_value,
                gain=gain,
                classification=classification,
                wait_until=wait_until,
                elss_locked_until=elss_locked_until,
            )
        )

    # A holding line may contain multiple lots with different classifications.
    # In that case the line itself has no single STCG/LTCG label.
    classification = (
        classifications[0]
        if classifications and all(c == classifications[0] for c in classifications)
        else None
    )

    wait_until = min(waits) if waits else None
    total_gain = sum(gains, ZERO) if len(gains) == len(lots) else None

    return HoldingConstraintAnalysis(
        holding_id=position.id,
        as_of=as_of,
        lots=tuple(analyses),
        total_gain=total_gain,
        classification=classification,
        wait_until=wait_until,
        elss_locked=locked,
    )


__all__ = [
    "HoldingConstraintAnalysis",
    "HoldingTaxConstraint",
    "LotTaxAnalysis",
    "analyze_holding",
]
