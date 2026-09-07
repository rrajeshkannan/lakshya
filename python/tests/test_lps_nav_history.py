import pandas as pd
import pytest

from lps.nav_history import normalize_nav_history


def test_nav_history_normalizes_chronological_order():
    nav = pd.DataFrame({
        "date": pd.to_datetime(["2026-08-03", "2026-08-01", "2026-08-02"]),
        "nav": [103.0, 101.0, 102.0],
    })
    normalized = normalize_nav_history(nav)
    assert list(normalized["date"]) == [
        pd.Timestamp("2026-08-01"),
        pd.Timestamp("2026-08-02"),
        pd.Timestamp("2026-08-03"),
    ]


def test_nav_history_rejects_duplicate_dates():
    nav = pd.DataFrame({
        "date": pd.to_datetime(["2026-08-01", "2026-08-01"]),
        "nav": [100.0, 101.0],
    })
    with pytest.raises(ValueError, match="duplicate"):
        normalize_nav_history(nav)


def test_nav_history_rejects_missing_nav_values():
    nav = pd.DataFrame({
        "date": pd.to_datetime(["2026-08-01", "2026-08-02"]),
        "nav": [100.0, None],
    })
    with pytest.raises(ValueError, match="missing"):
        normalize_nav_history(nav)


def test_nav_history_rejects_non_positive_nav():
    nav = pd.DataFrame({
        "date": pd.to_datetime(["2026-08-01", "2026-08-02"]),
        "nav": [100.0, 0.0],
    })
    with pytest.raises(ValueError, match="positive"):
        normalize_nav_history(nav)


def test_nav_history_preserves_missing_calendar_days():
    nav = pd.DataFrame({
        "date": pd.to_datetime(["2026-08-01", "2026-08-02", "2026-08-05"]),
        "nav": [100.0, 101.0, 102.0],
    })
    normalized = normalize_nav_history(nav)
    assert len(normalized) == 3
    assert list(normalized["date"]) == [
        pd.Timestamp("2026-08-01"),
        pd.Timestamp("2026-08-02"),
        pd.Timestamp("2026-08-05"),
    ]


def test_nav_history_returns_canonical_columns():
    nav = pd.DataFrame({
        "date": pd.to_datetime(["2026-08-02", "2026-08-01"]),
        "nav": [101.0, 100.0],
    })
    normalized = normalize_nav_history(nav)
    assert list(normalized.columns) == ["date", "nav"]
    assert pd.api.types.is_datetime64_any_dtype(normalized["date"])
    assert pd.api.types.is_numeric_dtype(normalized["nav"])
