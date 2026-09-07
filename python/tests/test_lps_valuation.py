from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from cas_import_poc.models import Position, PositionKey
from lps.current_state import CurrentState
from lps.nav_evidence import NavEvidenceStore
from lps.valuation import build_current, current_total, value_position


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


def state(units=Decimal("10"), isin="INF001"):
    position = Position(
        key=PositionKey("Amma", "F1", isin),
        units=units,
    )
    return CurrentState(position=position, units=units)


def test_value_position_uses_exact_nav_date(tmp_path):
    valuation = value_position(state(), make_store(tmp_path), date(2026, 8, 18))
    assert valuation is not None
    assert valuation.nav_observation_date == date(2026, 8, 18)
    assert valuation.nav == Decimal("109.06")
    assert valuation.market_value == Decimal("1090.60")


def test_value_position_uses_latest_nav_on_or_before_date(tmp_path):
    valuation = value_position(state(), make_store(tmp_path), date(2026, 8, 16))
    assert valuation is not None
    assert valuation.nav_observation_date == date(2026, 8, 14)
    assert valuation.nav == Decimal("109.78")
    assert valuation.market_value == Decimal("1097.80")


def test_value_position_fails_before_first_nav(tmp_path):
    with pytest.raises(ValueError):
        value_position(state(), make_store(tmp_path), date(2026, 8, 13))


def test_zero_unit_historical_position_is_excluded_from_current(tmp_path):
    valuation = value_position(
        state(units=Decimal("0")),
        make_store(tmp_path),
        date(2026, 8, 18),
    )
    assert valuation is None


def test_build_current_uses_position_isin_and_excludes_zero_units(tmp_path):
    store_a = make_store(tmp_path, "INF001")
    store_b = make_store(tmp_path, "INF002")
    valuations = build_current(
        [state(Decimal("10"), "INF001"), state(Decimal("0"), "INF002")],
        {"INF001": store_a, "INF002": store_b},
        date(2026, 8, 18),
    )
    assert len(valuations) == 1
    assert valuations[0].current_state.position.key.isin == "INF001"


def test_current_total_sums_position_market_values(tmp_path):
    store_a = make_store(tmp_path, "INF001")
    store_b = make_store(tmp_path, "INF002")
    valuations = build_current(
        [state(Decimal("10"), "INF001"), state(Decimal("20"), "INF002")],
        {"INF001": store_a, "INF002": store_b},
        date(2026, 8, 18),
    )
    assert current_total(valuations) == Decimal("3271.80")


def test_build_current_requires_nav_store_for_active_position(tmp_path):
    with pytest.raises(KeyError, match="INF001"):
        build_current([state()], {}, date(2026, 8, 18))
