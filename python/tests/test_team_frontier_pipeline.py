"""[lakshya] End-to-end TEAM frontier pipeline tests."""

import pandas as pd

from lakshya_core.dominance import Dimension
from lakshya_core.models import Fund
from team_analysis.frontier_pipeline import stream_team_evidence, team_frontier_from_histories


def fund(isin):
    return Fund(name=isin, isin=isin)


def history(values):
    return pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"]),
        "nav": values,
    })


def test_stream_team_evidence_builds_collective_fingerprint_one_team_at_a_time():
    funds = [fund("B"), fund("A")]
    histories = {"A": history([100, 110, 120, 130]), "B": history([50, 60, 70, 80])}

    stream = stream_team_evidence(funds, histories)
    team, fingerprint = next(stream)

    assert team.is_singleton
    assert team.members[0].isin == "A"
    assert fingerprint.team == team
    assert fingerprint.elevation is not None
    assert fingerprint.protection is not None


def test_end_to_end_team_frontier_accepts_collective_evidence():
    funds = [fund("A"), fund("B")]
    histories = {"A": history([100, 110, 120, 130]), "B": history([50, 60, 70, 80])}

    # [lakshya] Wiring test: use one real declared dimension so the test
    # exercises candidate -> collective NAV -> fingerprint -> comparator -> frontier.
    dimensions = (Dimension("elevation_3y_median", "up"),)
    frontier = team_frontier_from_histories(funds, histories, dimensions)

    assert frontier
    assert all(1 <= team.cardinality <= 3 for team in frontier)
