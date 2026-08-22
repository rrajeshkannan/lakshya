import pandas as pd
import pytest

from team_analysis.collective_timeline import build_collective_nav


def history(dates, navs):
    return pd.DataFrame({"date": pd.to_datetime(dates), "nav": navs})


def test_singleton_team_reproduces_fund_trajectory():
    fund = history(
        ["2020-01-01", "2020-01-03", "2020-01-05"],
        [100, 102, 101],
    )

    result = build_collective_nav({"A": fund})

    pd.testing.assert_frame_equal(
        result,
        fund.sort_values("date").reset_index(drop=True),
    )


def test_pair_uses_as_of_nav_for_missing_observation_dates():
    a = history(
        ["2020-01-01", "2020-01-03", "2020-01-05"],
        [100, 102, 104],
    )
    b = history(
        ["2020-01-02", "2020-01-04", "2020-01-05"],
        [200, 201, 203],
    )

    result = build_collective_nav({"A": a, "B": b})

    expected = history(
        ["2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05"],
        [300, 302, 303, 307],
    )

    pd.testing.assert_frame_equal(result, expected)


def test_trio_sums_all_members_on_common_observation_timeline():
    a = history(["2020-01-01", "2020-01-03"], [100, 110])
    b = history(["2020-01-02", "2020-01-03"], [200, 220])
    c = history(["2020-01-01", "2020-01-02", "2020-01-03"], [300, 330, 360])

    result = build_collective_nav({"A": a, "B": b, "C": c})

    expected = history(
        ["2020-01-02", "2020-01-03"],
        [630, 690],
    )

    pd.testing.assert_frame_equal(result, expected)


def test_no_common_history_is_rejected():
    a = history(["2020-01-01", "2020-01-02"], [100, 101])
    b = history(["2020-01-03", "2020-01-04"], [200, 201])

    with pytest.raises(ValueError, match="no common period"):
        build_collective_nav({"A": a, "B": b})


def test_empty_team_is_rejected():
    with pytest.raises(ValueError, match="at least one Fund"):
        build_collective_nav({})


def test_input_histories_are_not_mutated():
    a = history(["2020-01-01", "2020-01-03"], [100, 110])
    original = a.copy(deep=True)

    build_collective_nav({"A": a})

    pd.testing.assert_frame_equal(a, original)
