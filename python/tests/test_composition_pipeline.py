from __future__ import annotations

import pandas as pd

from lakshya_core.models import Fund
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition_pipeline import stream_composition_fingerprints
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_stream_composition_fingerprints_expands_each_admitted_team():
    team = Team(members=(_fund("A"), _fund("B")))
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [200.0 - i for i in range(30)]}),
    }

    results = list(stream_composition_fingerprints([team], histories))

    assert len(results) == 21
    assert all(isinstance(fingerprint, CompositionFingerprint) for _, fingerprint in results)
    assert all(fingerprint.composition is composition for composition, fingerprint in results)


def test_stream_composition_fingerprints_preserves_three_member_coordinate_space():
    team = Team(members=(_fund("A"), _fund("B"), _fund("C")))
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [200.0 - i for i in range(30)]}),
        "C": pd.DataFrame({"date": dates, "nav": [120.0 + 0.5 * i for i in range(30)]}),
    }

    results = list(stream_composition_fingerprints([team], histories))

    assert len(results) == 231
    assert any(
        composition.weights == {"A": 0.90, "B": 0.05, "C": 0.05}
        for composition, _ in results
    )
    assert any(
        composition.weights == {"A": 0.90, "B": 0.10, "C": 0.0}
        for composition, _ in results
    )
