from decimal import Decimal

from lts.models import FormationIntentRow, TargetFormation
from lts.position_bridge import LtsPosition, LtsPositionId
from lts.purpose_transition import build_purpose_transition_plan
from lts.purpose_transition_report import build_purpose_transition_report


def position(isin, value, purpose="Edu_A"):
    return LtsPosition(
        id=LtsPositionId("I1", "F1", isin, "Slice-1"),
        units=Decimal("1"),
        market_value=Decimal(value),
        purpose=purpose,
    )


def row(purpose, isin, capital, weight):
    return FormationIntentRow(
        purpose=purpose,
        isin=isin,
        target_capital=Decimal(capital),
        target_weight=Decimal(weight),
    )


def test_report_aggregates_retention_redemption_and_destinations():
    positions = [position("AAA", "60"), position("CCC", "40")]
    formation = TargetFormation(rows=(row("Edu_A", "AAA", "100", "0.6"), row("Edu_A", "BBB", "100", "0.4")))
    plan = build_purpose_transition_plan(positions, formation)

    report = build_purpose_transition_report(positions, formation, plan)

    assert len(report) == 1
    item = report[0]
    assert item.purpose == "Edu_A"
    assert item.current_amount == Decimal("100")
    assert item.target_amount == Decimal("100")
    assert item.retained_amount == Decimal("60")
    assert item.redemption_amount == Decimal("40")
    assert item.locked_redemption_amount == Decimal("0")
    assert item.investment_by_destination == (("AAA", Decimal("60")), ("BBB", Decimal("40")))
    assert item.is_balanced is True


def test_report_preserves_locked_redemption_category():
    positions = [position("CCC", "100")]
    formation = TargetFormation(rows=(row("Edu_A", "AAA", "100", "1"),))
    plan = build_purpose_transition_plan(positions, formation, locked_position_ids={positions[0].id})

    item = build_purpose_transition_report(positions, formation, plan)[0]

    assert item.redemption_amount == Decimal("0")
    assert item.locked_redemption_amount == Decimal("100")
    assert item.is_balanced is True


def test_report_is_deterministically_sorted_by_purpose():
    positions = [position("AAA", "100", "Retirement"), position("BBB", "100", "Edu_A")]
    formation = TargetFormation(rows=(row("Retirement", "AAA", "100", "1"), row("Edu_A", "BBB", "100", "1")))
    plan = build_purpose_transition_plan(positions, formation)

    report = build_purpose_transition_report(positions, formation, plan)

    assert [item.purpose for item in report] == ["Edu_A", "Retirement"]
