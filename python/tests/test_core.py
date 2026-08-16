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
    
from lakshya_core.evidence_inventory import build_evidence_inventory

from lakshya_core.evidence_inventory import build_evidence_inventory


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
    
from lakshya_core.fund_evidence import calculate_fund_evidence


def test_fund_evidence_for_one_fund():
    evidence = calculate_fund_evidence("INF174K01KT2")

    assert evidence.isin == "INF174K01KT2"

    assert evidence.returns.observations > 0
    assert evidence.returns.first_date < evidence.returns.last_date

    assert evidence.drawdown.maximum_drawdown <= 0
    assert evidence.drawdown.decline_days >= 0
    
from lakshya_core.evidence_inventory import load_nav_cache
from lakshya_core.rolling_returns import calculate_rolling_cagr

from pathlib import Path


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