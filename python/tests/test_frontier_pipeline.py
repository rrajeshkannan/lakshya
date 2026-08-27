"""[lakshya] End-to-end TEAM evidence/frontier tests."""

import pandas as pd

from lakshya_core.dominance import Dimension
from lakshya_core.models import Fund
from team_analysis.frontier_pipeline import stream_team_evidence, team_frontier_from_histories


def fund(isin: str) -> Fund:
    return Fund(name=isin, isin=isin)


def history(start, values):
    dates = pd.date_range(start=start, periods=len(values), freq="D")
    return pd.DataFrame({"date": dates, "nav": values})


def test_stream_builds_collective_fingerprint_before_yielding():
    funds = [fund("A"), fund("B")]
    histories = {
        "A": history("2020-01-01", [10, 11, 12]),
        "B": history("2020-01-01", [20, 21, 22]),
    }

    evidence = list(stream_team_evidence(funds, histories))

    assert len(evidence) == 3  # A, B, A+B
    pair = next(fp for team, fp in evidence if team.cardinality == 2)
    assert pair.team.members[0].isin == "A"
    assert pair.team.members[1].isin == "B"


def test_frontier_pipeline_can_use_the_real_collective_evidence_path():
    funds = [fund("A"), fund("B")]
    histories = {
        "A": history("2020-01-01", [10, 11, 12]),
        "B": history("2020-01-01", [20, 21, 22]),
    }

    # One dimension is sufficient to prove the pipeline wiring; the full
    # 40-D gate remains covered by the comparator/frontier tests.
    result = team_frontier_from_histories(
        funds,
        histories,
        (Dimension("elevation_3y_median", "up"),),
    )

    assert len(result) == 3
