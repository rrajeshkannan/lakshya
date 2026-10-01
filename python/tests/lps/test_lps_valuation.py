from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from lps.nav_evidence import NavEvidenceStore
from lps.positions import Position, PositionId
from lps.valuation import total_market_value, value_position, value_positions


def make_store(tmp_path, isin="INF001"):
    path = tmp_path / f"{isin}.json"
    store = NavEvidenceStore(path)
    store.create(
        isin=isin,
        scheme_code="1001",
        source="test",
        nav=pd.DataFrame({
            "date": pd.to_datetime(["2026-08-14", "2026-08-18"]),
            "nav": [Decimal("109.78"), Decimal("109.06")],
        }),
        retrieved_at="2026-08-18T10:00:00+05:30",
    )
    return store


def position(units=Decimal("10"), isin="INF001", purpose=None):
    return Position(
        id=PositionId("Amma", "F1", isin),
        units=units,
        purpose=purpose,
    )


def test_value_position_uses_exact_nav_date(tmp_path):
    valued = value_position(position(), make_store(tmp_path), date(2026, 8, 18))
    assert valued.nav == Decimal("109.06")
    assert valued.market_value == Decimal("1090.60")


def test_value_position_uses_latest_nav_on_or_before_date(tmp_path):
    valued = value_position(position(), make_store(tmp_path), date(2026, 8, 16))
    assert valued.nav == Decimal("109.78")
    assert valued.market_value == Decimal("1097.80")


def test_value_position_preserves_accepted_purpose(tmp_path):
    valued = value_position(
        position(purpose="Retirement"),
        make_store(tmp_path),
        date(2026, 8, 18),
    )
    assert valued.purpose == "Retirement"


def test_value_position_fails_before_first_nav(tmp_path):
    with pytest.raises(ValueError):
        value_position(position(), make_store(tmp_path), date(2026, 8, 13))


def test_zero_unit_historical_position_is_retained_without_valuation(tmp_path):
    valued = value_position(
        position(units=Decimal("0"), purpose="Retirement"),
        make_store(tmp_path),
        date(2026, 8, 18),
    )
    assert valued.units == Decimal("0")
    assert valued.nav is None
    assert valued.market_value is None
    assert valued.purpose == "Retirement"


def test_value_positions_retains_all_positions_and_values_active_ones(tmp_path):
    store_a = make_store(tmp_path, "INF001")
    store_b = make_store(tmp_path, "INF002")
    positions = [position(Decimal("10"), "INF001"), position(Decimal("0"), "INF002")]

    valued = value_positions(
        positions,
        {"INF001": store_a, "INF002": store_b},
        date(2026, 8, 18),
    )

    assert len(valued) == 2
    assert valued[0].id.isin == "INF001"
    assert valued[0].market_value == Decimal("1090.60")
    assert valued[1].id.isin == "INF002"
    assert valued[1].market_value is None


def test_total_market_value_sums_position_market_values(tmp_path):
    store_a = make_store(tmp_path, "INF001")
    store_b = make_store(tmp_path, "INF002")
    positions = value_positions(
        [position(Decimal("10"), "INF001"), position(Decimal("20"), "INF002")],
        {"INF001": store_a, "INF002": store_b},
        date(2026, 8, 18),
    )
    assert total_market_value(positions) == Decimal("3271.80")


def test_value_positions_requires_nav_store_for_active_position(tmp_path):
    with pytest.raises(KeyError, match="INF001"):
        value_positions([position()], {}, date(2026, 8, 18))
