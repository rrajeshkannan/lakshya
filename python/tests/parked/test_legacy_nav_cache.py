"""Parked regression for the inherited NAV cache era.

This test is retained as historical evidence but is deliberately excluded
from the active pytest suite. The current repository data contract no longer
includes data/cache fixtures.
"""

from pathlib import Path

import pytest

from lakshya_core.rolling_returns import calculate_rolling_cagr
from lakshya_core.parked.evidence_inventory import load_nav_cache


def test_five_year_rolling_returns_from_legacy_nav_cache():
    project_root = Path(__file__).resolve().parents[3]
    path = project_root / "data" / "cache" / "INF174K01KT2_nav.json"

    if not path.exists():
        pytest.skip("legacy data/cache NAV fixture is not present")

    df = load_nav_cache(path)
    evidence = calculate_rolling_cagr(df, 5)
    assert evidence.years == 5
    assert evidence.observations > 0
    assert evidence.minimum <= evidence.median
    assert evidence.median <= evidence.maximum
    assert evidence.negative_periods >= 0
