from decimal import Decimal

from lts.models import FormationIntentRow, TargetFormation
from lts.position_bridge import LtsPosition, LtsPositionId
from lts.purpose_transition import (
    TransitionDisposition,
    build_purpose_transition_plan,
)


def position(investor, folio, isin, value, purpose="Edu_A"):
    return LtsPosition(
        id=LtsPositionId(investor, folio, isin, "Slice-1"),
        units=Decimal("1"),
        market_value=Decimal(value),
        purpose=purpose,
    )


def formation(*rows):
    return TargetFormation(rows=tuple(rows))


def row(purpose, isin, capital, weight):
    return FormationIntentRow(
        purpose=purpose,
        isin=isin,
        target_capital=Decimal(capital),
        target_weight=Decimal(weight),
    )


def test_retain_and_invest_selected_target_gap():
    plan = build_purpose_transition_plan(
        [position("I1", "F1", "AAA", "60")],
        formation(
            row("Edu_A", "AAA", "100", "0.5"),
            row("Edu_A", "BBB", "100", "0.5"),
        ),
    )

    assert [(item.disposition, item.amount, item.destination_isin) for item in plan.rows] == [
        (TransitionDisposition.RETAIN, Decimal("50.0"), "AAA"),
        (TransitionDisposition.REDEEM, Decimal("10.0"), "AAA"),
        (TransitionDisposition.INVEST, Decimal("50.0"), "BBB"),
    ]


def test_non_selected_capital_is_redeemable_and_purpose_owned():
    plan = build_purpose_transition_plan(
        [position("I1", "F1", "CCC", "80")],
        formation(row("Edu_A", "AAA", "100", "1")),
    )

    assert len(plan.rows) == 2
    assert plan.rows[0].purpose == "Edu_A"
    assert plan.rows[0].disposition is TransitionDisposition.REDEEM
    assert plan.rows[0].amount == Decimal("80")
    assert plan.rows[1].disposition is TransitionDisposition.INVEST
    assert plan.rows[1].destination_isin == "AAA"
    assert plan.rows[1].amount == Decimal("100")


def test_locked_excess_is_preserved_as_locked_redemption():
    source = position("I1", "F1", "CCC", "80")
    plan = build_purpose_transition_plan(
        [source],
        formation(row("Edu_A", "AAA", "100", "1")),
        locked_position_ids={source.id},
    )

    assert plan.rows[0].disposition is TransitionDisposition.REDEEM_LOCKED
    assert plan.rows[0].locked is True
    assert plan.rows[0].purpose == "Edu_A"


def test_purposes_are_not_cross_subsidized():
    plan = build_purpose_transition_plan(
        [position("I1", "F1", "AAA", "100", "Edu_A")],
        formation(
            row("Edu_A", "AAA", "100", "1"),
            row("Retirement", "BBB", "100", "1"),
        ),
    )

    investment = [item for item in plan.rows if item.disposition is TransitionDisposition.INVEST]
    assert len(investment) == 1
    assert investment[0].purpose == "Retirement"
    assert investment[0].destination_isin == "BBB"


def test_unvalued_position_is_rejected():
    source = LtsPosition(
        id=LtsPositionId("I1", "F1", "AAA", "Slice-1"),
        units=Decimal("1"),
        market_value=None,
        purpose="Edu_A",
    )

    try:
        build_purpose_transition_plan(
            [source],
            formation(row("Edu_A", "AAA", "100", "1")),
        )
    except ValueError as error:
        assert "unvalued" in str(error)
    else:
        raise AssertionError("Expected unvalued Position to be rejected")
