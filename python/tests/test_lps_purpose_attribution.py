from decimal import Decimal

import pytest

from lps.positions import Position, PositionId
from lps.purpose_attribution import (
    ATTRIBUTION_FIELDS,
    PositionPurposeAttribution,
    purpose_by_position,
    read_attributions,
    validate_attributions,
    write_attributions,
)


def _position(investor="Amma", folio="123", isin="INF000"):
    return Position(PositionId(investor, folio, isin), Decimal("10"))


def test_attribution_is_keyed_by_full_position_identity():
    position = _position()
    attribution = PositionPurposeAttribution(position.id, "Retirement")

    assert purpose_by_position([attribution]) == {position.id: "Retirement"}


def test_same_isin_in_different_investor_or_folio_is_distinct():
    first = _position("Amma", "123", "INF000")
    second = _position("Appanna", "123", "INF000")
    third = _position("Amma", "999", "INF000")

    attributions = [
        PositionPurposeAttribution(first.id, "Retirement"),
        PositionPurposeAttribution(second.id, "Edu_B"),
        PositionPurposeAttribution(third.id, "Marriage"),
    ]

    validate_attributions([first, second, third], attributions)


def test_unknown_position_cannot_be_attributed():
    with pytest.raises(ValueError, match="unknown Position"):
        validate_attributions(
            [_position()],
            [
                PositionPurposeAttribution(
                    PositionId("Amma", "999", "INF000"), "Retirement"
                )
            ],
        )


def test_position_can_have_only_one_accepted_purpose():
    position = _position()
    attributions = [
        PositionPurposeAttribution(position.id, "Retirement"),
        PositionPurposeAttribution(position.id, "Edu_B"),
    ]

    with pytest.raises(ValueError, match="Duplicate Purpose attribution"):
        validate_attributions([position], attributions)


def test_unattributed_positions_are_allowed_during_review():
    first = _position()
    second = _position("Amma", "999", "INF000")

    validate_attributions(
        [first, second],
        [PositionPurposeAttribution(first.id, "Retirement")],
    )


def test_attribution_persistence_round_trip(tmp_path):
    path = tmp_path / "position_purpose.csv"
    attributions = [
        PositionPurposeAttribution(PositionId("Appanna", "2", "INF002"), "Edu_B"),
        PositionPurposeAttribution(PositionId("Amma", "1", "INF001"), "Retirement"),
    ]

    write_attributions(path, attributions)

    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(ATTRIBUTION_FIELDS)
    assert read_attributions(path) == sorted(
        attributions,
        key=lambda item: (item.position_id.investor, item.position_id.folio, item.position_id.isin),
    )
