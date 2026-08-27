"""[lakshya] TEAM fingerprint fractal and trajectory tests."""

import pandas as pd

from lakshya_core.drawdown_severity import calculate_protection
from lakshya_core.elevation import calculate_elevation
from lakshya_core.models import Fund
from team_analysis.collective_timeline import build_collective_nav
from team_analysis.team import Team
from team_analysis.team_fingerprint import TeamFingerprint


def nav_history(dates, navs):
    return pd.DataFrame({"date": pd.to_datetime(dates), "nav": navs})


def fund(isin):
    return Fund(name=isin, isin=isin)


def test_singleton_team_fingerprint_matches_fund_trajectory_fingerprint():
    nav = nav_history(
        ["2010-01-01", "2015-01-01", "2020-01-01", "2025-01-01"],
        [100, 130, 180, 150],
    )
    team = Team((fund("A"),))
    collective = build_collective_nav({"A": nav})
    result = TeamFingerprint(team, collective)

    assert result.elevation == calculate_elevation(nav)
    assert result.protection == calculate_protection(nav)


def test_pair_team_fingerprint_is_calculated_from_collective_nav():
    a = nav_history(
        ["2010-01-01", "2015-01-01", "2020-01-01", "2025-01-01"],
        [100, 130, 180, 150],
    )
    b = nav_history(
        ["2010-01-02", "2015-01-02", "2020-01-02", "2025-01-02"],
        [200, 220, 260, 300],
    )
    team = Team(tuple(sorted((fund("A"), fund("B")), key=lambda f: f.isin)))
    collective = build_collective_nav({"A": a, "B": b})
    result = TeamFingerprint(team, collective)

    assert result.elevation == calculate_elevation(collective)
    assert result.protection == calculate_protection(collective)


def test_team_fingerprint_is_reproducible_from_collective_trajectory_alone():
    a = nav_history(
        ["2010-01-01", "2015-01-01", "2020-01-01", "2025-01-01"],
        [100, 130, 180, 150],
    )
    b = nav_history(
        ["2010-01-02", "2015-01-02", "2020-01-02", "2025-01-02"],
        [200, 220, 260, 300],
    )
    collective = build_collective_nav({"A": a, "B": b})
    team = Team(tuple(sorted((fund("A"), fund("B")), key=lambda f: f.isin)))

    result = TeamFingerprint(team, collective)

    assert result.elevation == calculate_elevation(collective)
    assert result.protection == calculate_protection(collective)
