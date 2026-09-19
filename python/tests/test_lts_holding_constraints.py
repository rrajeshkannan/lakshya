from datetime import date
from decimal import Decimal

from lts.holding_constraints import (
    HoldingConstraintAnalysis,
    HoldingTaxConstraint,
    LotTaxAnalysis,
    analyze_holding,
)
from lps.positions import Position, PositionId
from lps.transactions import Transaction


POSITION = Position(
    id=PositionId("Amma", "F1", "A"),
    units=Decimal("10"),
    nav=Decimal("150"),
    market_value=Decimal("1500"),
    purpose="Edu",
)


def tx(d, units, amount):
    return Transaction(
        transaction_date=date.fromisoformat(d),
        event_type="Any",
        investor="Amma",
        folio="F1",
        isin="A",
        units=Decimal(str(units)),
        amount=Decimal(str(amount)) if amount is not None else None,
        price=None,
        source_description=f"{d}-{units}",
    )


def test_analysis_is_per_holding_line_and_exposes_gain_and_wait_until():
    result = analyze_holding(
        POSITION,
        [
            tx("2025-01-15", 10, 1000),
        ],
        date(2026, 9, 19),
        HoldingTaxConstraint(
            isin="A",
            long_term_holding_months=12,
        ),
    )

    assert result.holding_id == POSITION.id
    assert result.total_gain == Decimal("500")
    assert result.classification == "LTCG"
    assert result.wait_until is None
    assert result.elss_locked is False


def test_stcg_gets_wait_until_date():
    result = analyze_holding(
        POSITION,
        [tx("2026-03-19", 10, 1000)],
        date(2026, 9, 19),
        HoldingTaxConstraint(
            isin="A",
            long_term_holding_months=12,
        ),
    )

    assert result.total_gain == Decimal("500")
    assert result.classification == "STCG"
    assert result.wait_until == date(2027, 3, 19)


def test_elss_lock_in_is_lot_specific():
    result = analyze_holding(
        POSITION,
        [tx("2025-10-01", 10, 1000)],
        date(2026, 9, 19),
        HoldingTaxConstraint(isin="A", is_elss=True),
    )

    assert result.elss_locked is True
    assert result.lots[0].elss_locked_until == date(2028, 10, 1)


def test_missing_cost_evidence_does_not_invent_gain():
    result = analyze_holding(
        POSITION,
        [tx("2025-01-15", 10, None)],
        date(2026, 9, 19),
        HoldingTaxConstraint(isin="A", long_term_holding_months=12),
    )

    assert result.total_gain is None
    assert result.lots[0].gain is None
