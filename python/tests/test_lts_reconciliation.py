from decimal import Decimal

import pytest

from lps.positions import Position, PositionId
from lts.models import EconomicReconciliation, FormationIntentRow, PositionReconciliation, TargetFormation
from lts.position_bridge import LtsPosition, LtsPositionId, bridge_positions
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


def lts_positions(*positions):
    return bridge_positions(list(positions))


def test_economic_reconciliation_matches_before_excess_and_gap():
    current = lts_positions(position("Amma", "F1", "A", "500"))
    intent = [FormationIntentRow("Retirement", "A", Decimal("800"), Decimal("0.75"))]

    row = reconcile_economically(current, TargetFormation(rows=tuple(intent)))[0]

    assert row.current_value == Decimal("500")
    assert row.target_value == Decimal("600")
    assert row.matched_value == Decimal("500")
    assert row.current_excess == Decimal("0")
    assert row.target_gap == Decimal("100")


def test_position_reconciliation_does_not_split_factual_position():
    current = lts_positions(position("Amma", "F1", "A", "500"))
    intent = [FormationIntentRow("Retirement", "A", Decimal("800"), Decimal("0.75"))]

    rows = reconcile_positions(current, reconcile_economically(current, intent))

    assert len(rows) == 1
    assert rows[0].position_id == LtsPositionId("Amma", "F1", "A", "Slice-1")
    assert rows[0].matched_value == Decimal("500")
    assert rows[0].unmatched_current_value == Decimal("0")


def test_multiple_positions_are_matched_deterministically():
    current = lts_positions(
        position("Appanna", "F2", "A", "200"),
        position("Amma", "F1", "A", "500"),
    )
    intent = [FormationIntentRow("Retirement", "A", Decimal("600"), Decimal("1"))]

    rows = reconcile_positions(current, reconcile_economically(current, intent))

    assert [row.position_id for row in rows] == [
        LtsPositionId("Amma", "F1", "A", "Slice-1"),
        LtsPositionId("Appanna", "F2", "A", "Slice-1"),
    ]
    assert [row.matched_value for row in rows] == [Decimal("500"), Decimal("100")]
    assert [row.unmatched_current_value for row in rows] == [Decimal("0"), Decimal("100")]


def test_partial_slice_percentage_contributes_only_its_allocated_value():
    current = [
        LtsPosition(
            id=LtsPositionId("Amma", "F1", "A", "Slice-1"),
            units=Decimal("1"),
            market_value=Decimal("1000"),
            purpose="Retirement",
            percentage=Decimal("60"),
        ),
        LtsPosition(
            id=LtsPositionId("Amma", "F1", "A", "Slice-2"),
            units=Decimal("1"),
            market_value=Decimal("1000"),
            purpose="Education",
            percentage=Decimal("40"),
        ),
    ]

    intent = [
        FormationIntentRow("Retirement", "A", Decimal("600"), Decimal("1")),
        FormationIntentRow("Education", "A", Decimal("400"), Decimal("1")),
    ]

    rows = reconcile_economically(current, TargetFormation(rows=tuple(intent)))

    assert {(row.purpose, row.current_value) for row in rows} == {
        ("Retirement", Decimal("600")),
        ("Education", Decimal("400")),
    }




def test_slice_percentages_must_sum_to_100_per_physical_holding():
    current = [
        LtsPosition(
            id=LtsPositionId("Amma", "F1", "A", "Slice-1"),
            units=Decimal("1"),
            market_value=Decimal("600"),
            purpose="Retirement",
            percentage=Decimal("60"),
        ),
        LtsPosition(
            id=LtsPositionId("Amma", "F1", "A", "Slice-2"),
            units=Decimal("1"),
            market_value=Decimal("400"),
            purpose="Education",
            percentage=Decimal("30"),
        ),
    ]

    with pytest.raises(ValueError, match="sum to exactly 100%"):
        reconcile_economically(
            current,
            [
                FormationIntentRow("Retirement", "A", Decimal("600"), Decimal("1")),
                FormationIntentRow("Education", "A", Decimal("400"), Decimal("1")),
            ],
        )


def test_duplicate_slice_identity_is_rejected():
    current = [
        LtsPosition(
            id=LtsPositionId("Amma", "F1", "A", "Slice-1"),
            units=Decimal("1"),
            market_value=Decimal("600"),
            purpose="Retirement",
            percentage=Decimal("50"),
        ),
        LtsPosition(
            id=LtsPositionId("Amma", "F1", "A", "Slice-1"),
            units=Decimal("1"),
            market_value=Decimal("400"),
            purpose="Education",
            percentage=Decimal("50"),
        ),
    ]

    with pytest.raises(ValueError, match="Duplicate LTS Position identity"):
        reconcile_economically(
            current,
            [
                FormationIntentRow("Retirement", "A", Decimal("500"), Decimal("1")),
                FormationIntentRow("Education", "A", Decimal("500"), Decimal("1")),
            ],
        )


def test_invalid_slice_percentage_is_rejected():
    current = [
        LtsPosition(
            id=LtsPositionId("Amma", "F1", "A", "Slice-1"),
            units=Decimal("1"),
            market_value=Decimal("1000"),
            purpose="Retirement",
            percentage=Decimal("101"),
        )
    ]

    with pytest.raises(ValueError, match="between 0 and 100"):
        reconcile_economically(
            current,
            [FormationIntentRow("Retirement", "A", Decimal("1000"), Decimal("1"))],
        )


def test_unvalued_position_is_not_treated_as_zero():
    current = lts_positions(
        Position(
            id=PositionId("Amma", "F1", "A"),
            units=Decimal("10"),
            market_value=None,
            purpose="Retirement",
        )
    )
    with pytest.raises(ValueError, match="unvalued Position"):
        reconcile_economically(
            current,
            [FormationIntentRow("Retirement", "A", Decimal("100"), Decimal("1"))],
        )


def test_treatments_distinguish_retain_partial_switch_and_exit():
    p = LtsPositionId("Amma", "F1", "A", "Slice-1")

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


def test_economic_reconciliation_reports_current_excess():
    current = lts_positions(position("Amma", "F1", "A", "900"))
    intent = [FormationIntentRow("Retirement", "A", Decimal("800"), Decimal("1"))]

    row = reconcile_economically(current, TargetFormation(rows=tuple(intent)))[0]

    assert row.current_value == Decimal("900")
    assert row.target_value == Decimal("800")
    assert row.matched_value == Decimal("800")
    assert row.current_excess == Decimal("100")
    assert row.target_gap == Decimal("0")


def test_economic_reconciliation_reports_target_only_gap():
    current = []
    intent = [FormationIntentRow("Retirement", "A", Decimal("800"), Decimal("1"))]

    row = reconcile_economically(current, TargetFormation(rows=tuple(intent)))[0]

    assert row.current_value == Decimal("0")
    assert row.target_value == Decimal("800")
    assert row.matched_value == Decimal("0")
    assert row.current_excess == Decimal("0")
    assert row.target_gap == Decimal("800")


def test_economic_reconciliation_ignores_unattributed_positions():
    current = lts_positions(position("Amma", "F1", "A", "500", purpose=None))
    intent = [FormationIntentRow("Retirement", "A", Decimal("500"), Decimal("1"))]

    row = reconcile_economically(current, TargetFormation(rows=tuple(intent)))[0]

    assert row.current_value == Decimal("0")
    assert row.target_value == Decimal("500")
    assert row.matched_value == Decimal("0")
    assert row.target_gap == Decimal("500")


def test_economic_reconciliation_rejects_non_finite_target_values():
    current = []
    intent = [FormationIntentRow("Retirement", "A", Decimal("100"), Decimal("NaN"))]

    with pytest.raises(ValueError, match="finite and non-negative"):
        reconcile_economically(current, TargetFormation(rows=tuple(intent)))


def test_position_reconciliation_leaves_target_gap_for_later():
    current = lts_positions(position("Amma", "F1", "A", "500"))
    intent = [FormationIntentRow("Retirement", "A", Decimal("800"), Decimal("1"))]

    economic = reconcile_economically(current, TargetFormation(rows=tuple(intent)))
    rows = reconcile_positions(current, economic)

    assert rows[0].matched_value == Decimal("500")
    assert rows[0].unmatched_current_value == Decimal("0")
    assert economic[0].target_gap == Decimal("300")


def test_position_reconciliation_reports_full_current_excess():
    current = lts_positions(position("Amma", "F1", "A", "900"))
    intent = [FormationIntentRow("Retirement", "A", Decimal("800"), Decimal("1"))]

    rows = reconcile_positions(current, reconcile_economically(current, TargetFormation(rows=tuple(intent))))

    assert rows[0].current_value == Decimal("900")
    assert rows[0].matched_value == Decimal("800")
    assert rows[0].unmatched_current_value == Decimal("100")


def test_position_reconciliation_keeps_zero_unit_position_as_zero_value():
    current = lts_positions(Position(
        id=PositionId("Amma", "F1", "A"),
        units=Decimal("0"),
        market_value=None,
        purpose="Retirement",
    ))
    economic = [FormationIntentRow("Retirement", "A", Decimal("0"), Decimal("1"))]

    rows = reconcile_positions(
        current,
        reconcile_economically(current, TargetFormation(rows=tuple(economic))),
    )

    assert rows[0].current_value == Decimal("0")
    assert rows[0].matched_value == Decimal("0")
    assert rows[0].unmatched_current_value == Decimal("0")


def test_position_reconciliation_does_not_allocate_unattributed_position():
    current = lts_positions(position("Amma", "F1", "A", "500", purpose=None))
    economic = [
        FormationIntentRow("Retirement", "A", Decimal("500"), Decimal("1"))
    ]

    rows = reconcile_positions(
        current,
        reconcile_economically(current, TargetFormation(rows=tuple(economic))),
    )

    assert rows == []


def test_position_reconciliation_rejects_unvalued_position():
    current = lts_positions(Position(
        id=PositionId("Amma", "F1", "A"),
        units=Decimal("10"),
        market_value=None,
        purpose="Retirement",
    ))

    with pytest.raises(ValueError, match="unvalued Position"):
        reconcile_positions(
            current,
            [EconomicReconciliation(
                "Retirement",
                "A",
                Decimal("100"),
                Decimal("100"),
                Decimal("100"),
                Decimal("0"),
                Decimal("0"),
            )],
        )


def test_position_reconciliation_consumes_duplicate_economic_rows_by_key():
    current = lts_positions(position("Amma", "F1", "A", "300"))
    economic = [
        EconomicReconciliation(
            "Retirement",
            "A",
            Decimal("0"),
            Decimal("100"),
            Decimal("100"),
            Decimal("0"),
            Decimal("0"),
        ),
        EconomicReconciliation(
            "Retirement",
            "A",
            Decimal("0"),
            Decimal("200"),
            Decimal("200"),
            Decimal("0"),
            Decimal("0"),
        ),
    ]

    rows = reconcile_positions(current, economic)

    assert rows[0].matched_value == Decimal("300")
    assert rows[0].unmatched_current_value == Decimal("0")
