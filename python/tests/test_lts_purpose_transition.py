from decimal import Decimal

from lts.models import FormationIntentRow, TargetFormation
from lts.position_bridge import LtsPosition, LtsPositionId
from lts.purpose_transition import (
    TransitionDisposition,
    TransitionSourceKind,
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


def test_retention_and_released_capital_are_mapped_to_target_gap():
    plan = build_purpose_transition_plan(
        [
            position("I1", "F1", "AAA", "60"),
            position("I1", "F2", "CCC", "40"),
        ],
        formation(
            row("Edu_A", "AAA", "100", "0.6"),
            row("Edu_A", "BBB", "100", "0.4"),
        ),
    )

    assert plan.is_balanced is True
    assert [(item.disposition, item.amount, item.destination_isin) for item in plan.rows] == [
        (TransitionDisposition.RETAIN, Decimal("60.0"), "AAA"),
        (TransitionDisposition.REDEEM, Decimal("40"), "CCC"),
        (TransitionDisposition.INVEST, Decimal("40"), "BBB"),
    ]
    assert plan.mappings[-1].source_kind is TransitionSourceKind.REDEMPTION_PROCEEDS
    assert plan.mappings[-1].destination_isin == "BBB"


def test_non_selected_capital_is_mapped_without_cross_purpose_subsidy():
    plan = build_purpose_transition_plan(
        [position("I1", "F1", "CCC", "100")],
        formation(row("Edu_A", "AAA", "100", "1")),
    )

    assert plan.is_balanced is True
    assert plan.mappings[0].source_kind is TransitionSourceKind.REDEMPTION_PROCEEDS
    assert plan.mappings[0].source_isin == "CCC"
    assert plan.mappings[0].destination_isin == "AAA"
    assert plan.mappings[0].amount == Decimal("100")


def test_locked_excess_is_rejected_instead_of_marked_as_redeemable():
    source = position("I1", "F1", "CCC", "100")

    try:
        build_purpose_transition_plan(
            [source],
            formation(row("Edu_A", "AAA", "100", "1")),
            locked_position_ids={source.id},
        )
    except ValueError as error:
        assert "Locked Position has excess capital" in str(error)
    else:
        raise AssertionError("Expected locked excess to be rejected")


def test_purpose_capital_mismatch_is_rejected():
    try:
        build_purpose_transition_plan(
            [position("I1", "F1", "AAA", "90")],
            formation(row("Edu_A", "AAA", "100", "1")),
        )
    except ValueError as error:
        assert "must be conserved" in str(error)
    else:
        raise AssertionError("Expected Purpose capital mismatch to be rejected")


def test_purposes_are_not_cross_subsidized():
    plan = build_purpose_transition_plan(
        [
            position("I1", "F1", "AAA", "100", "Edu_A"),
            position("I1", "F2", "CCC", "100", "Retirement"),
        ],
        formation(
            row("Edu_A", "AAA", "100", "1"),
            row("Retirement", "BBB", "100", "1"),
        ),
    )

    assert plan.is_balanced is True
    assert all(item.purpose == "Retirement" for item in plan.mappings if item.source_isin == "CCC")
    assert all(item.purpose == "Edu_A" for item in plan.mappings if item.source_isin == "AAA")


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
