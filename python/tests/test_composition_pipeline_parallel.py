from __future__ import annotations

import pandas as pd

from lakshya_core.models import Fund
from team_analysis.composition_pipeline import stream_composition_fingerprints_parallel
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_parallel_composition_pipeline_preserves_complete_grid():
    team = Team(members=(_fund("A"), _fund("B")))
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [200.0 - i for i in range(30)]}),
    }

    results = list(
        stream_composition_fingerprints_parallel(
            [team], histories, max_workers=2
        )
    )

    assert len(results) == 19
    assert all(fingerprint.composition is composition for composition, fingerprint in results)
