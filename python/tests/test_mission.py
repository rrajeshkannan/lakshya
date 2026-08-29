from __future__ import annotations

from lakshya_core.models import Fund
from mission import Goal, Mission, Purpose
from team_analysis.composition import Composition
from team_analysis.team import Team


def _composition() -> Composition:
    a = Fund(name="Fund A", isin="A", category="Test")
    b = Fund(name="Fund B", isin="B", category="Test")
    return Composition(team=Team(members=(a, b)), weights={"A": 0.95, "B": 0.05})


def test_mission_contract_carries_purpose_and_surviving_composition():
    purpose = Purpose(
        name="Long-term family goal",
        goals=(Goal(name="Education", horizon_years=10, target_corpus=1_000_000),),
    )
    composition = _composition()

    mission = Mission(purpose=purpose, composition=composition)

    assert mission.purpose is purpose
    assert mission.composition is composition


def test_mission_contract_does_not_score_or_rank_composition():
    purpose = Purpose(
        name="Retirement",
        goals=(Goal(name="Retirement corpus", horizon_years=15),),
    )
    mission = Mission(purpose=purpose, composition=_composition())

    assert mission.purpose.goals[0].horizon_years == 15
    assert not hasattr(mission, "score")
    assert not hasattr(mission, "rank")
