from datetime import date

from lakshya_core.models import Goal


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
