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


def long_history(values):
    return pd.DataFrame({
        "date": pd.date_range("2010-01-01", periods=len(values), freq="YS"),
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

    def fake_frontier(funds, fund_histories, dimensions, **kwargs):
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


def test_runner_removes_fund_dominated_before_team(monkeypatch):
    captured = {}

    def fake_frontier(funds, fund_histories, dimensions, **kwargs):
        captured["funds"] = list(funds)
        return ["frontier"]

    monkeypatch.setattr(
        "team_analysis.run_team_pipeline.team_frontier_from_histories",
        fake_frontier,
    )

    funds = [fund("A"), fund("B")]
    histories = {
        "A": long_history([100 + i for i in range(11)]),
        "B": long_history([200 + 3 * i for i in range(11)]),
    }

    result = run_team_pipeline(
        funds=funds,
        fund_histories=histories,
        dimensions=(Dimension("elevation_3y_median", "up"),),
    )

    assert result == ["frontier"]
    assert [item.isin for item in captured["funds"]] == ["B"]


def test_runner_emits_fund_dominator_audit(monkeypatch):
    captured = []

    def fake_fund_frontier(funds, fund_histories, dimensions, *, on_dominated=None):
        assert on_dominated is not None
        on_dominated(funds[0], funds[1])
        return [funds[1]]

    def fake_team_frontier(funds, fund_histories, dimensions, **kwargs):
        return ["frontier"]

    monkeypatch.setattr(
        "team_analysis.run_team_pipeline.fund_frontier_from_histories",
        fake_fund_frontier,
    )
    monkeypatch.setattr(
        "team_analysis.run_team_pipeline.team_frontier_from_histories",
        fake_team_frontier,
    )

    funds = [fund("A"), fund("B")]
    run_team_pipeline(
        funds=funds,
        fund_histories={"A": history([100, 110, 120, 130]), "B": history([50, 60, 70, 80])},
        dimensions=(Dimension("elevation_3y_median", "up"),),
        detail=captured.append,
    )

    assert "FUND_DOMINATED loser=A dominator=B" in captured
    assert "FUND_FRONTIER admitted=2 survivors=1 eliminated=1" in captured
    assert "TEAM_CANDIDATE_UNIVERSE size_1=1 total=1" in captured
