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

from lakshya_core.models import Goal, Fund
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
