from datetime import date, datetime, timezone
from decimal import Decimal

from lts.availability_report import build_holding_availability_report
from lts.evidence import TransitionEvidence, TransitionEvidencePosition
from lts.holding_constraints import HoldingTaxConstraint
from lps.positions import PositionId
from lps.transactions import Transaction


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


def test_report_projects_transition_evidence_into_reviewer_availability():
    evidence = TransitionEvidence(
        positions=(
            TransitionEvidencePosition(
                id=PositionId("Amma", "F1", "A"),
                units=Decimal("30"),
                nav=Decimal("150"),
                nav_observation_date=date(2026, 9, 20),
                market_value=Decimal("4500"),
                purpose="Edu",
            ),
        ),
        transactions=(
            tx("2020-01-01", 10, 1000),
            tx("2025-01-01", 20, 2000),
        ),
        fund_metadata=(),
    )

    report = build_holding_availability_report(
        evidence=evidence,
        as_of=date(2026, 9, 20),
        constraints={"A": HoldingTaxConstraint(isin="A", is_elss=True)},
    )

    assert len(report) == 1
    assert report[0].unlocked_units == Decimal("10")
    assert report[0].unlocked_value == Decimal("1500")
    assert report[0].locked_units == Decimal("20")
    assert report[0].locked_lots[0].locked_until == date(2028, 1, 1)


def test_report_requires_explicit_constraint_for_each_non_zero_position():
    evidence = TransitionEvidence(
        positions=(
            TransitionEvidencePosition(
                id=PositionId("Amma", "F1", "A"),
                units=Decimal("10"),
                nav=Decimal("150"),
                nav_observation_date=date(2026, 9, 20),
                market_value=Decimal("1500"),
                purpose="Edu",
            ),
        ),
        transactions=(tx("2020-01-01", 10, 1000),),
        fund_metadata=(),
    )

    try:
        build_holding_availability_report(
            evidence=evidence,
            as_of=date(2026, 9, 20),
            constraints={},
        )
    except KeyError as exc:
        assert "No holding constraint supplied" in str(exc)
    else:
        raise AssertionError("Expected missing constraint to fail fast")
