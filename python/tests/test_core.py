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