from decimal import Decimal

import pytest

from lps.positions import Position, PositionId
from lts.models import FormationIntentRow, PositionReconciliation
from lts.reconciliation import reconcile_economically, reconcile_positions
from lts.treatments import TransitionTreatment, classify_position_treatment


def position(investor, folio, isin, value, purpose="Retirement"):
    value = Decimal(value)
    return Position(
        id=PositionId(investor, folio, isin),
        units=Decimal("1"),
        nav=value,
        market_value=value,
        purpose=purpose,
    )


def test_economic_reconciliation_matches_before_excess_and_gap():
    current = [position("Amma", "F1", "A", "500")]
    intent = [FormationIntentRow("Retirement", "A", Decimal("800"), Decimal("0.75"))]

    row = reconcile_economically(current, intent)[0]

    assert row.current_value == Decimal("500")
    assert row.target_value == Decimal("600")
    assert row.matched_value == Decimal("500")
    assert row.current_excess == Decimal("0")
    assert row.target_gap == Decimal("100")


def test_position_reconciliation_does_not_split_factual_position():
    current = [position("Amma", "F1", "A", "500")]
    intent = [FormationIntentRow("Retirement", "A", Decimal("800"), Decimal("0.75"))]

    rows = reconcile_positions(current, reconcile_economically(current, intent))

    assert len(rows) == 1
    assert rows[0].position_id == PositionId("Amma", "F1", "A")
    assert rows[0].matched_value == Decimal("500")
    assert rows[0].unmatched_current_value == Decimal("0")


def test_multiple_positions_are_matched_deterministically():
    current = [
        position("Appanna", "F2", "A", "200"),
        position("Amma", "F1", "A", "500"),
    ]
    intent = [FormationIntentRow("Retirement", "A", Decimal("600"), Decimal("1"))]

    rows = reconcile_positions(current, reconcile_economically(current, intent))

    assert [row.position_id for row in rows] == [
        PositionId("Amma", "F1", "A"),
        PositionId("Appanna", "F2", "A"),
    ]
    assert [row.matched_value for row in rows] == [Decimal("500"), Decimal("100")]
    assert [row.unmatched_current_value for row in rows] == [Decimal("0"), Decimal("100")]


def test_unvalued_position_is_not_treated_as_zero():
    current = [Position(
        id=PositionId("Amma", "F1", "A"),
        units=Decimal("10"),
        market_value=None,
        purpose="Retirement",
    )]
    with pytest.raises(ValueError, match="unvalued Position"):
        reconcile_economically(
            current,
            [FormationIntentRow("Retirement", "A", Decimal("100"), Decimal("1"))],
        )


def test_treatments_distinguish_retain_partial_switch_and_exit():
    p = PositionId("Amma", "F1", "A")

    assert classify_position_treatment(
        PositionReconciliation(p, "Retirement", "A", Decimal("100"), Decimal("100"), Decimal("0"))
    ) == TransitionTreatment.RETAIN

    assert classify_position_treatment(
        PositionReconciliation(p, "Retirement", "A", Decimal("100"), Decimal("60"), Decimal("40"))
    ) == TransitionTreatment.PARTIALLY_TRANSFORM

    assert classify_position_treatment(
        PositionReconciliation(p, "Retirement", "A", Decimal("100"), Decimal("0"), Decimal("100")),
        destination_isin="B",
    ) == TransitionTreatment.SWITCH

    assert classify_position_treatment(
        PositionReconciliation(p, "Retirement", "A", Decimal("100"), Decimal("0"), Decimal("100"))
    ) == TransitionTreatment.EXIT
