from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from lakshya_core.drawdown_episodes import DrawdownEpisode, calculate_resilience
from lakshya_core.drawdown_severity import calculate_protection
from lakshya_core.elevation import calculate_elevation
from lakshya_core.models import ElevationEvidence, ResilienceEvidence
from lakshya_core.rolling_returns import RollingReturnEvidence, calculate_rolling_cagr
from lakshya_core.nav_history import normalize_nav_history
from lakshya_core.parked.evidence_inventory import load_nav_cache


def test_elevation_can_have_missing_long_horizon_evidence():
    # Elevation evidence can be constructed with only short-horizon evidence.
    # Unavailable evidence remains unavailable. We don't turn insufficient history into zeros.
    rolling_3y = RollingReturnEvidence(
        years=3,
        observations=100,
        minimum=-5.0,
        percentile_25=8.0,
        median=12.0,
        percentile_75=16.0,
        maximum=25.0,
        mean=12.5,
        standard_deviation=5.0,
        positive_periods=95,
        negative_periods=5,
        positive_period_pct=95.0,
        latest=14.0,
    )

    elevation = ElevationEvidence(
        rolling_3y=rolling_3y,
        rolling_5y=None,
        rolling_7y=None,
        rolling_10y=None,
    )

    assert elevation.rolling_3y is not None
    assert elevation.rolling_5y is None
    assert elevation.rolling_7y is None
    assert elevation.rolling_10y is None


def test_resilience_retains_episode_level_evidence():
    # Resilience evidence can be constructed from a list of drawdown episodes.
    # This explicitly prevents us from building a system that calculates medians and throws away the journeys that produced them.
    episode = DrawdownEpisode(
        peak_date=date(2020, 1, 1),
        peak_value=100.0,
        trough_date=date(2020, 3, 1),
        trough_value=60.0,
        drawdown_pct=-0.40,
        decline_days=60,
        recovery_date=date(2020, 9, 1),
        recovery_days=184,
        underwater_days=244,
        status="recovered",
        history_before_peak_days=1000,
    )

    resilience = ResilienceEvidence(
        episode_count=1,
        recovered_count=1,
        ongoing_count=0,
        median_depth_pct=40.0,
        worst_depth_pct=40.0,
        median_decline_days_recovered=60.0,
        median_recovery_days=184.0,
        median_underwater_days_recovered=244.0,
        median_underwater_days_ongoing=None,
        episodes=[episode],
    )

    assert resilience.episode_count == 1
    assert resilience.recovered_count == 1
    assert resilience.ongoing_count == 0

    assert len(resilience.episodes) == 1
    assert resilience.episodes[0] is episode


def test_elevation_preserves_horizon_evidence_state():
    # Elevation assembles each rolling-return horizon independently.
    # Insufficient history remains unavailable rather than becoming zero.

    dates = pd.date_range("2020-01-01", periods=1500, freq="D")

    nav = pd.DataFrame(
        {
            "date": dates,
            "nav": range(100, 1600),
        }
    )

    elevation = calculate_elevation(nav)

    assert elevation.rolling_3y is not None
    assert elevation.rolling_5y is None
    assert elevation.rolling_7y is None
    assert elevation.rolling_10y is None


def test_protection_measures_severity_from_funds_own_high_water_mark():
    # Protection measures adversity against the fund's own historical
    # high-water mark, not against a benchmark.
    #
    # A NAV path of 100 -> 90 -> 80 -> 90 produces:
    #   0% severity at the high-water mark,
    #   10% severity at 90,
    #   20% severity at 80,
    #   10% severity after the partial recovery.

    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-04",
                ]
            ),
            "nav": [100.0, 90.0, 80.0, 90.0],
        }
    )

    protection = calculate_protection(nav)

    assert protection.observations == 4
    assert protection.median_severity_pct == pytest.approx(10.0)
    assert protection.maximum_severity_pct == pytest.approx(20.0)

    assert protection.days_at_or_above_threshold[5] == 3
    assert protection.days_at_or_above_threshold[10] == 3
    assert protection.days_at_or_above_threshold[15] == 1
    assert protection.days_at_or_above_threshold[20] == 1


def test_resilience_separates_recovered_and_ongoing_evidence():
    # Resilience retains the individual drawdown journeys.
    #
    # Recovery statistics are calculated only from episodes whose
    # recovery has actually been observed.
    #
    # An ongoing episode contributes to episode_count and ongoing_count,
    # but it must not contaminate recovery-duration statistics.

    recovered_episode = DrawdownEpisode(
        peak_date=date(2020, 1, 1),
        peak_value=100.0,
        trough_date=date(2020, 3, 1),
        trough_value=60.0,
        drawdown_pct=-0.40,
        decline_days=60,
        recovery_date=date(2020, 9, 1),
        recovery_days=184,
        underwater_days=244,
        status="recovered",
        history_before_peak_days=1000,
    )

    ongoing_episode = DrawdownEpisode(
        peak_date=date(2024, 1, 1),
        peak_value=120.0,
        trough_date=date(2024, 6, 1),
        trough_value=90.0,
        drawdown_pct=-0.25,
        decline_days=152,
        recovery_date=None,
        recovery_days=None,
        underwater_days=500,
        status="ongoing",
        history_before_peak_days=2000,
    )

    resilience = calculate_resilience(
        [recovered_episode, ongoing_episode]
    )

    assert resilience.episode_count == 2
    assert resilience.recovered_count == 1
    assert resilience.ongoing_count == 1

    assert resilience.median_depth_pct == pytest.approx(32.5)
    assert resilience.worst_depth_pct == pytest.approx(40.0)

    # Only the recovered episode contributes to recovery statistics.
    assert resilience.median_decline_days_recovered == 60.0
    assert resilience.median_recovery_days == 184.0
    assert resilience.median_underwater_days_recovered == 244.0

    # The ongoing episode has its own underwater journey, but no
    # recovery duration because recovery has not been observed.
    assert resilience.median_underwater_days_ongoing == 500.0

    # Most importantly: the underlying journeys remain available.
    assert len(resilience.episodes) == 2
    assert resilience.episodes[0] == recovered_episode
    assert resilience.episodes[1] == ongoing_episode


def test_nav_history_normalizes_chronological_order():
    # External NAV sources may not arrive in chronological order.
    # The analytical engine consumes a canonical ascending date order.
    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-03",
                    "2026-08-01",
                    "2026-08-02",
                ]
            ),
            "nav": [103.0, 101.0, 102.0],
        }
    )

    normalized = normalize_nav_history(nav)

    assert list(normalized["date"]) == [
        pd.Timestamp("2026-08-01"),
        pd.Timestamp("2026-08-02"),
        pd.Timestamp("2026-08-03"),
    ]


def test_nav_history_rejects_duplicate_dates():
    # Two observations for the same date are ambiguous.
    # We must not silently choose one and thereby rewrite observed history.
    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-01",
                    "2026-08-01",
                ]
            ),
            "nav": [100.0, 101.0],
        }
    )

    with pytest.raises(ValueError, match="duplicate"):
        normalize_nav_history(nav)


def test_nav_history_rejects_missing_nav_values():
    # Missing observed NAV values remain missing.
    # We do not interpolate or manufacture historical observations.
    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-01",
                    "2026-08-02",
                ]
            ),
            "nav": [100.0, None],
        }
    )

    with pytest.raises(ValueError, match="missing"):
        normalize_nav_history(nav)


def test_nav_history_rejects_non_positive_nav():
    # NAV must represent a valid positive fund value.
    # Zero or negative observations are invalid input, not evidence of behaviour.
    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-01",
                    "2026-08-02",
                ]
            ),
            "nav": [100.0, 0.0],
        }
    )

    with pytest.raises(ValueError, match="positive"):
        normalize_nav_history(nav)


def test_nav_history_preserves_missing_calendar_days():
    # Mutual-fund NAV history does not need an observation for every
    # calendar day. Missing calendar dates are not missing NAV observations.
    # We must not fabricate values for weekends or other non-observation days.
    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-01",
                    "2026-08-02",
                    "2026-08-05",
                ]
            ),
            "nav": [100.0, 101.0, 102.0],
        }
    )

    normalized = normalize_nav_history(nav)

    assert len(normalized) == 3
    assert list(normalized["date"]) == [
        pd.Timestamp("2026-08-01"),
        pd.Timestamp("2026-08-02"),
        pd.Timestamp("2026-08-05"),
    ]


def test_nav_history_returns_canonical_columns():
    # The rest of Lakshya should consume one canonical NAV representation,
    # regardless of how the source originally represented the observations.
    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-08-02",
                    "2026-08-01",
                ]
            ),
            "nav": [101.0, 100.0],
        }
    )

    normalized = normalize_nav_history(nav)

    assert list(normalized.columns) == ["date", "nav"]
    assert pd.api.types.is_datetime64_any_dtype(normalized["date"])
    assert pd.api.types.is_numeric_dtype(normalized["nav"])


def test_five_year_rolling_returns():
    project_root = Path(__file__).resolve().parents[2]

    path = (
        project_root
        / "data"
        / "cache"
        / "INF174K01KT2_nav.json"
    )

    df = load_nav_cache(path)

    evidence = calculate_rolling_cagr(df, 5)

    assert evidence.years == 5
    assert evidence.observations > 0
    assert evidence.minimum <= evidence.median
    assert evidence.median <= evidence.maximum
    assert evidence.negative_periods >= 0


def test_drawdown_episode_distinguishes_recovered_and_ongoing():
    # A recovered episode has a known recovery story.
    # An ongoing episode has an unknown recovery story.
    # Not zero. Not estimated. Unknown.
    recovered = DrawdownEpisode(
        peak_date=date(2020, 1, 1),
        peak_value=100.0,
        trough_date=date(2020, 3, 1),
        trough_value=60.0,
        drawdown_pct=-0.40,
        decline_days=60,
        recovery_date=date(2020, 9, 1),
        recovery_days=184,
        underwater_days=244,
        status="recovered",
        history_before_peak_days=1000,
    )

    ongoing = DrawdownEpisode(
        peak_date=date(2025, 1, 1),
        peak_value=100.0,
        trough_date=date(2025, 3, 1),
        trough_value=70.0,
        drawdown_pct=-0.30,
        decline_days=59,
        recovery_date=None,
        recovery_days=None,
        underwater_days=300,
        status="ongoing",
        history_before_peak_days=1000,
    )

    assert recovered.status == "recovered"
    assert recovered.recovery_date is not None
    assert recovered.recovery_days is not None

    assert ongoing.status == "ongoing"
    assert ongoing.recovery_date is None
    assert ongoing.recovery_days is None
