from datetime import date

import pandas as pd

from fund_analysis.fund_admission import evaluate_potential_fund


REVIEW_DATE = date(2026, 8, 20)


def make_fund(
    *,
    category="Equity Scheme - Small Cap Fund",
    category_sub="Small Cap Fund",
    scheme_type="Open Ended Schemes",
    plan="Direct",
    option="Growth",
    first_date="2015-01-01",
    is_active=True,
):
    return pd.Series(
        {
            "category": category,
            "category_sub": category_sub,
            "scheme_type": scheme_type,
            "plan": plan,
            "option": option,
            "first_date": first_date,
            "is_active": is_active,
        }
    )


def test_valid_potential_fund():
    fund = make_fund()

    assert evaluate_potential_fund(
        fund,
        REVIEW_DATE,
    ) == "ADMIT"


def test_regular_and_direct_plans_have_same_admission_treatment():
    direct = make_fund(plan="Direct")
    regular = make_fund(plan="Regular")

    assert evaluate_potential_fund(direct, REVIEW_DATE) == "ADMIT"
    assert evaluate_potential_fund(regular, REVIEW_DATE) == "ADMIT"


def test_elss_is_rejected():
    fund = make_fund(
        category="Equity Scheme - ELSS Fund",
        category_sub="ELSS",
    )

    assert evaluate_potential_fund(
        fund,
        REVIEW_DATE,
    ) == "REJECT"


def test_non_growth_option_is_rejected():
    fund = make_fund(
        option="IDCW",
    )

    assert evaluate_potential_fund(
        fund,
        REVIEW_DATE,
    ) == "REJECT"


def test_young_fund_is_waitlisted():
    fund = make_fund(
        first_date="2020-08-21",
    )

    assert evaluate_potential_fund(
        fund,
        REVIEW_DATE,
    ) == "WAITLIST"


def test_exactly_eight_years_is_admitted():
    fund = make_fund(
        first_date="2018-08-20",
    )

    assert evaluate_potential_fund(
        fund,
        REVIEW_DATE,
    ) == "ADMIT"


def test_closed_ended_fund_is_rejected():
    fund = make_fund(
        scheme_type="Close Ended Schemes",
    )

    assert evaluate_potential_fund(
        fund,
        REVIEW_DATE,
    ) == "REJECT"


def test_inactive_fund_is_rejected():
    fund = make_fund(
        is_active=False,
    )

    assert evaluate_potential_fund(
        fund,
        REVIEW_DATE,
    ) == "REJECT"
