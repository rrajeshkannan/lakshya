"""[lakshya] Tests for FUND Pareto elimination observability."""

from lakshya_core.dominance import Dimension
from lakshya_core.models import Fund
from team_analysis.fund_frontier import fund_frontier_from_histories


def test_fund_frontier_audit_identifies_a_real_dominator(monkeypatch):
    funds = [Fund(name=isin, isin=isin) for isin in ("A", "B", "C")]
    values = {
        "A": {"x": 10, "y": 5},
        "B": {"x": 9, "y": 6},
        "C": {"x": 8, "y": 4},
    }

    def fake_comparator(fund, nav):
        return fund, values[fund.isin]

    monkeypatch.setattr(
        "team_analysis.fund_frontier.fund_comparator_values",
        fake_comparator,
    )

    events = []
    dimensions = (Dimension("x", "up"), Dimension("y", "down"))
    frontier = fund_frontier_from_histories(
        funds,
        {},
        dimensions=dimensions,
        on_dominated=lambda loser, dominator: events.append((loser.isin, dominator.isin)),
    )

    assert [fund.isin for fund in frontier] == ["A", "C"]
    assert events == [("B", "A")]


def test_fund_frontier_audit_is_observability_only(monkeypatch):
    funds = [Fund(name=isin, isin=isin) for isin in ("A", "B")]
    values = {
        "A": {"x": 10},
        "B": {"x": 9},
    }

    monkeypatch.setattr(
        "team_analysis.fund_frontier.fund_comparator_values",
        lambda fund, nav: (fund, values[fund.isin]),
    )

    dimensions = (Dimension("x", "up"),)
    without_callback = fund_frontier_from_histories(funds, {}, dimensions=dimensions)
    with_callback = fund_frontier_from_histories(
        funds,
        {},
        dimensions=dimensions,
        on_dominated=lambda loser, dominator: None,
    )

    assert [fund.isin for fund in without_callback] == ["A"]
    assert [fund.isin for fund in with_callback] == ["A"]
