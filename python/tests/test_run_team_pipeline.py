"""[lakshya] Tests for the public TEAM-stage pipeline runner."""

import pandas as pd

from lakshya_core.dominance import Dimension
from lakshya_core.models import Fund
from team_analysis.run_team_pipeline import run_team_pipeline


def fund(isin: str) -> Fund:
    return Fund(name=isin, isin=isin)


def history(values):
    return pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"]),
        "nav": values,
    })


def test_runner_delegates_to_team_frontier_with_explicit_dimensions():
    funds = [fund("A"), fund("B")]
    histories = {
        "A": history([100, 110, 120, 130]),
        "B": history([50, 60, 70, 80]),
    }

    frontier = run_team_pipeline(
        funds=funds,
        fund_histories=histories,
        dimensions=(Dimension("elevation_3y_median", "up"),),
    )

    assert frontier
    assert all(1 <= team.cardinality <= 3 for team in frontier)


def test_runner_uses_declared_team_gate_by_default(monkeypatch):
    captured = {}

    def fake_frontier(funds, fund_histories, dimensions):
        captured["funds"] = funds
        captured["histories"] = fund_histories
        captured["dimensions"] = dimensions
        return ["frontier"]

    monkeypatch.setattr(
        "team_analysis.run_team_pipeline.team_frontier_from_histories",
        fake_frontier,
    )

    funds = [fund("A")]
    histories = {"A": history([100, 110, 120, 130])}

    result = run_team_pipeline(funds=funds, fund_histories=histories)

    assert result == ["frontier"]
    assert captured["funds"] == funds
    assert captured["histories"] == histories
    assert len(captured["dimensions"]) == 40
