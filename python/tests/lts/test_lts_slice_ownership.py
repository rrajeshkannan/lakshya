from decimal import Decimal

import pytest
from lps.positions import Position, PositionId
from lts.position_bridge import LtsPositionId, SliceOwnership, build_owned_positions, validate_slice_percentages


def source_position():
    return Position(
        id=PositionId("Amma", "F1", "INF001"),
        units=Decimal("10"),
        nav=Decimal("100"),
        market_value=Decimal("1000"),
        purpose=None,
    )


def test_explicit_slice_ownership_preserves_physical_observation_and_attributes_percentages():
    projected = build_owned_positions(
        [source_position()],
        [
            SliceOwnership("Amma", "F1", "INF001", "Slice-1", "Edu_A", Decimal("60"), "MANUAL_OWNERSHIP"),
            SliceOwnership("Amma", "F1", "INF001", "Slice-2", "Retirement", Decimal("40"), "MANUAL_OWNERSHIP"),
        ],
    )

    assert [row.id for row in projected] == [
        LtsPositionId("Amma", "F1", "INF001", "Slice-1"),
        LtsPositionId("Amma", "F1", "INF001", "Slice-2"),
    ]
    assert [row.percentage for row in projected] == [Decimal("60"), Decimal("40")]
    assert all(row.units == Decimal("10") for row in projected)
    assert all(row.market_value == Decimal("1000") for row in projected)
    assert [row.purpose for row in projected] == ["Edu_A", "Retirement"]


def test_explicit_slice_ownership_rejects_non_100_percent_total():
    with pytest.raises(ValueError, match="sum to exactly 100%"):
        build_owned_positions(
            [source_position()],
            [
                SliceOwnership("Amma", "F1", "INF001", "Slice-1", "Edu_A", Decimal("60"), "MANUAL_OWNERSHIP"),
                SliceOwnership("Amma", "F1", "INF001", "Slice-2", "Retirement", Decimal("30"), "MANUAL_OWNERSHIP"),
            ],
        )


def test_explicit_slice_ownership_rejects_missing_physical_holding_ownership():
    with pytest.raises(ValueError, match="Missing Slice ownership"):
        build_owned_positions([source_position()], [])


def test_slice_percentage_validator_rejects_duplicate_identity():
    from lts.position_bridge import LtsPosition

    row = LtsPosition(
        id=LtsPositionId("Amma", "F1", "INF001", "Slice-2"),
        units=Decimal("10"),
        market_value=Decimal("1000"),
        percentage=Decimal("50"),
    )
    with pytest.raises(ValueError, match="Duplicate LTS Position identity"):
        validate_slice_percentages([row, row])
