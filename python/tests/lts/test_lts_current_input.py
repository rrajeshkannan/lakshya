from decimal import Decimal

import pytest

from lps.positions import Position, PositionId
from lts.current_input import classify_current_positions


def _position(*, isin: str, units: str, market_value: str | None, purpose: str | None):
    return Position(
        id=PositionId(investor="Sri", folio="F1", isin=isin),
        units=Decimal(units),
        market_value=None if market_value is None else Decimal(market_value),
        purpose=purpose,
    )


def test_classifies_zero_unit_records_as_inactive():
    result = classify_current_positions(
        [
            _position(isin="AAA", units="0", market_value=None, purpose=None),
            _position(isin="BBB", units="10", market_value="1000", purpose="Retirement"),
        ]
    )

    assert result.active_positions[0].id.isin == "BBB"
    assert result.inactive_positions[0].id.isin == "AAA"
    assert result.diagnostics.total_records == 2
    assert result.diagnostics.active_records == 1
    assert result.diagnostics.inactive_records == 1
    assert result.diagnostics.invalid_active_records == 0


def test_rejects_active_position_without_purpose():
    with pytest.raises(ValueError, match="no Purpose attribution"):
        classify_current_positions(
            [_position(isin="AAA", units="10", market_value="1000", purpose=None)]
        )


def test_rejects_active_position_without_market_value():
    with pytest.raises(ValueError, match="no market value"):
        classify_current_positions(
            [_position(isin="AAA", units="10", market_value=None, purpose="Retirement")]
        )


def test_rejects_negative_active_units():
    with pytest.raises(ValueError, match="negative units"):
        classify_current_positions(
            [_position(isin="AAA", units="-1", market_value="100", purpose="Retirement")]
        )
