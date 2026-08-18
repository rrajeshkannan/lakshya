from fund_analysis.universe import load_fund_universe
from lakshya_core.models import Fund


def test_fund_universe_loads_all_current_funds():
    # The current Fund universe is defined by funds_universe.csv.
    # Fund-stage analysis must operate on the complete current universe,
    # not on hard-coded funds or holdings embedded in the engine.
    funds = load_fund_universe()

    assert len(funds) == 17
    assert all(isinstance(fund, Fund) for fund in funds)


def test_fund_universe_uses_isin_as_unique_identity():
    # ISIN is the stable identity used to connect a fund across
    # universe data, NAV history, and future evidence artifacts.
    funds = load_fund_universe()

    isins = [fund.isin for fund in funds]

    assert len(isins) == len(set(isins))
    assert all(isin for isin in isins)


def test_fund_universe_contains_required_fund_identity():
    # Every Fund entering the behavioural engine must have enough
    # identity to describe whose behaviour is being analysed.
    funds = load_fund_universe()

    assert all(fund.name for fund in funds)
    assert all(fund.isin for fund in funds)
    assert all(fund.category for fund in funds)


def test_fund_universe_does_not_depend_on_current_holdings():
    # The Fund stage describes the defined Fund universe.
    # Current portfolio holdings are a later Portfolio-stage concern.
    funds = load_fund_universe()

    assert len(funds) == 17
