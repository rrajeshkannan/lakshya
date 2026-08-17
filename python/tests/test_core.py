import pandas as pd
import pytest

from lakshya_core.elevation import calculate_elevation
from lakshya_core.drawdown_severity import calculate_protection
from lakshya_core.drawdown_episodes import calculate_resilience
from lakshya_core.fund_fingerprint import build_fund_behavioural_fingerprint
from lakshya_core.parked.evidence_inventory import load_nav_cache

from pathlib import Path
from lakshya_core.rolling_returns import calculate_rolling_cagr
from datetime import date

from lakshya_core.models import (
    Goal,
    Fund,
    ElevationEvidence,
    ProtectionEvidence,
    ResilienceEvidence,
    FundBehaviouralFingerprint,
)

from lakshya_core.drawdown_episodes import DrawdownEpisode
from lakshya_core.rolling_returns import RollingReturnEvidence

from lakshya_core.load_data import (
    load_current_holdings,
    load_funds_universe,
    load_goals,
)


def test_goal_can_be_created():
    goal = Goal(
        name="Retirement",
        purpose="Lifetime financial independence",
        target_corpus=8_50_00_000,
        target_date=date(2039, 4, 30),
        flexibility="low",
        consequence_of_shortfall="high",
        lifecycle="accumulation",
    )

    assert goal.name == "Retirement"
    assert goal.target_corpus == 8_50_00_000


def test_existing_data_can_be_loaded():
    goals = load_goals()
    funds = load_funds_universe()
    holdings = load_current_holdings()

    assert not goals.empty
    assert not funds.empty
    assert not holdings.empty


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


def test_fund_behavioural_fingerprint_contains_three_compass_dimensions():
    # A fund's behavioural fingerprint contains three compass dimensions: elevation, protection, and resilience.
    elevation = ElevationEvidence(
        rolling_3y=None,
        rolling_5y=None,
        rolling_7y=None,
        rolling_10y=None,
    )

    protection = ProtectionEvidence(
        observations=100,
        median_severity_pct=5.0,
        percentile_75_severity_pct=10.0,
        percentile_90_severity_pct=15.0,
        percentile_95_severity_pct=20.0,
        percentile_99_severity_pct=30.0,
        maximum_severity_pct=40.0,
        days_at_or_above_threshold={
            5: 50,
            10: 25,
            15: 10,
            20: 5,
            25: 2,
            30: 1,
        },
        pct_days_at_or_above_threshold={
            5: 50.0,
            10: 25.0,
            15: 10.0,
            20: 5.0,
            25: 2.0,
            30: 1.0,
        },
    )

    resilience = ResilienceEvidence(
        episode_count=0,
        recovered_count=0,
        ongoing_count=0,
        median_depth_pct=None,
        worst_depth_pct=None,
        median_decline_days_recovered=None,
        median_recovery_days=None,
        median_underwater_days_recovered=None,
        median_underwater_days_ongoing=None,
        episodes=[],
    )

    fund = Fund(
        name="Example Fund",
        isin="EXAMPLE",
        category="Flexi Cap",
    )

    fingerprint = FundBehaviouralFingerprint(
        fund=fund,
        elevation=elevation,
        protection=protection,
        resilience=resilience,
    )

    assert fingerprint.fund == fund
    assert fingerprint.elevation is elevation
    assert fingerprint.protection is protection
    assert fingerprint.resilience is resilience


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


def test_fund_behavioural_fingerprint_composes_three_evidence_dimensions():
    # The Fund Behavioural Fingerprint is a composition of the three
    # independent Fund-stage compass dimensions.
    #
    # Composition does not calculate, score, rank, weight, or judge them.
    # It simply preserves the evidence produced by each dimension.
    #
    # The fund identity is retained alongside the three dimensions.

    fund = Fund(
        name="Test Fund",
        isin="TEST123",
        category="Flexi Cap",
    )

    elevation = ElevationEvidence(
        rolling_3y=None,
        rolling_5y=None,
        rolling_7y=None,
        rolling_10y=None,
    )

    protection = ProtectionEvidence(
        observations=0,
        median_severity_pct=0.0,
        percentile_75_severity_pct=0.0,
        percentile_90_severity_pct=0.0,
        percentile_95_severity_pct=0.0,
        percentile_99_severity_pct=0.0,
        maximum_severity_pct=0.0,
        days_at_or_above_threshold={},
        pct_days_at_or_above_threshold={},
    )

    resilience = ResilienceEvidence(
        episodes=[],
        episode_count=0,
        recovered_count=0,
        ongoing_count=0,
        median_depth_pct=None,
        worst_depth_pct=None,
        median_decline_days_recovered=None,
        median_recovery_days=None,
        median_underwater_days_recovered=None,
        median_underwater_days_ongoing=None,
    )

    fingerprint = FundBehaviouralFingerprint(
        fund=fund,
        elevation=elevation,
        protection=protection,
        resilience=resilience,
    )

    assert fingerprint.fund is fund
    assert fingerprint.elevation is elevation
    assert fingerprint.protection is protection
    assert fingerprint.resilience is resilience


def test_fund_behavioural_fingerprint_can_be_built_from_nav_history():
    # The Fund-stage engine assembles the three independent behavioural
    # dimensions from the same observed NAV history.
    #
    # No scoring, ranking, suitability judgement, or benchmark comparison
    # happens at this orchestration boundary.

    fund = Fund(
        name="Test Fund",
        isin="TEST123",
        category="Flexi Cap",
    )

    dates = pd.date_range("2010-01-01", periods=4500, freq="D")

    # Start with a steadily rising NAV so that all long-horizon
    # Elevation calculations have sufficient history.
    values = list(range(100, 4600))

    # Introduce one deliberate drawdown journey:
    #
    #   3100  ← high-water mark
    #     ↓
    #   2500  ← >5% adversity, therefore an episode
    #     ↓
    #   3100  ← recovery to the previous high-water mark
    #
    # The surrounding NAV path continues upward.
    drawdown_start = 3000
    drawdown_trough = 3100
    recovery_end = 3300

    peak_value = values[drawdown_start]
    trough_value = 2500

    for i in range(drawdown_start, drawdown_trough):
        progress = (i - drawdown_start) / (
            drawdown_trough - drawdown_start
        )
        values[i] = peak_value - (
            (peak_value - trough_value) * progress
        )

    values[drawdown_trough] = trough_value

    for i in range(drawdown_trough + 1, recovery_end):
        progress = (i - drawdown_trough) / (
            recovery_end - drawdown_trough
        )
        values[i] = trough_value + (
            (peak_value - trough_value) * progress
        )

    values[recovery_end] = peak_value

    nav = pd.DataFrame(
        {
            "date": dates,
            "nav": values,
        }
    )

    fingerprint = build_fund_behavioural_fingerprint(
        fund=fund,
        nav=nav,
    )

    assert fingerprint.fund is fund

    assert fingerprint.elevation.rolling_3y is not None
    assert fingerprint.elevation.rolling_5y is not None
    assert fingerprint.elevation.rolling_7y is not None
    assert fingerprint.elevation.rolling_10y is not None

    assert fingerprint.protection.observations == len(nav)

    assert fingerprint.resilience.episode_count >= 1
    assert fingerprint.resilience.recovered_count >= 1
