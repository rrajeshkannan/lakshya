import pandas as pd
from lakshya_core.evidence_inventory import load_nav_cache
from lakshya_core.fund_evidence import calculate_fund_evidence
from lakshya_core.evidence_inventory import build_evidence_inventory
from lakshya_core.downside import calculate_downside_deviation
from lakshya_core.benchmark_evidence import (
    load_benchmark_history,
    calculate_benchmark_evidence,
)
from lakshya_core.capture import (
    CaptureEvidence,
    calculate_capture,
)
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


def test_nav_evidence_inventory():
    inventory = build_evidence_inventory()

    assert not inventory.empty
    assert len(inventory) == 17

    assert inventory["Observations"].min() > 0
    assert inventory["First_NAV"].notna().all()
    assert inventory["Last_NAV"].notna().all()

    assert (inventory["Last_NAV"] >= inventory["First_NAV"]).all()

    assert (inventory["Duplicate_Dates"] == 0).all()
    assert (inventory["Duplicate_Records"] == 0).all()

    assert (inventory["Invalid_Dates"] == 0).all()
    assert (inventory["Invalid_NAV"] == 0).all()


def test_fund_evidence_for_one_fund():
    evidence = calculate_fund_evidence("INF174K01KT2")

    assert evidence.isin == "INF174K01KT2"

    assert evidence.returns.observations > 0
    assert evidence.returns.first_date < evidence.returns.last_date

    assert evidence.drawdown.maximum_drawdown <= 0
    assert evidence.drawdown.decline_days >= 0


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


def test_downside_deviation():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]

    path = (
        project_root
        / "data"
        / "cache"
        / "INF174K01KT2_nav.json"
    )

    df = load_nav_cache(path)

    evidence = calculate_downside_deviation(df)

    assert evidence.negative_observations > 0
    assert evidence.downside_rms_daily >= 0
    assert evidence.downside_rms_annualized >= 0


def test_benchmark_evidence():
    project_root = Path(__file__).resolve().parents[2]

    path = (
        project_root
        / "data"
        / "benchmarks_consolidated.csv"
    )

    df = load_benchmark_history(path)

    evidence = calculate_benchmark_evidence(
        df,
        "NIFTY 500",
    )

    assert evidence.observations > 0
    assert evidence.first_date == date(1996, 1, 1)
    assert evidence.last_date == date(2026, 8, 11)
    assert evidence.invalid_dates == 0
    assert evidence.invalid_values == 0
    assert evidence.duplicate_dates == 0
    assert evidence.max_gap_days > 0
    assert evidence.missing_values == 0


def test_capture_100_percent():
    dates = pd.date_range(
        "2024-01-01",
        periods=14,
        freq="ME",
    )

    values = [
        100.0,
        110.0,
        99.0,
        108.9,
        98.01,
        107.811,
        97.0299,
        106.73289,
        96.059601,
        105.6655611,
        95.099005,
        104.6089055,
        94.1480149,
        103.5628164,
    ]

    fund = pd.Series(
        values,
        index=dates,
    )

    benchmark = pd.Series(
        values,
        index=dates,
    )

    evidence = calculate_capture(
        fund,
        benchmark,
    )

    assert evidence.upside_capture_pct == 100.0
    assert evidence.downside_capture_pct == 100.0
    assert evidence.capture_months_used == 13


def test_capture_downside_half():
    dates = pd.date_range(
        "2024-01-01",
        periods=13,
        freq="ME",
    )

    # Benchmark alternates +10%, -20%.
    benchmark = pd.Series(
        [
            100,
            110,
            88,
            96.8,
            77.44,
            85.184,
            68.1472,
            74.96192,
            59.969536,
            65.9664896,
            52.77319168,
            58.050510848,
            46.4404086784,
        ],
        index=dates,
    )

    # Fund participates fully in upside, but loses only 10%
    # whenever benchmark loses 20%.
    fund = pd.Series(
        [
            100,
            110,
            99,
            108.9,
            98.01,
            107.811,
            97.0299,
            106.73289,
            96.059601,
            105.6655611,
            95.099005,
            104.6089055,
            94.1480149,
        ],
        index=dates,
    )

    evidence = calculate_capture(
        fund,
        benchmark,
    )

    assert evidence.capture_months_used == 12
    assert evidence.upside_capture_pct is not None
    assert evidence.downside_capture_pct is not None
