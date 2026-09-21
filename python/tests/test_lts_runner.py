from decimal import Decimal

from lts.runner import run_lts_transition


PURPOSES = """name,due,desired,monthly_plan
Retirement,2039-04-12,10000000,50000
Edu_A,2027-04-01,4300000,25000
"""

POSITIONS = """investor,folio,isin,units,nav,market_value,purpose
Amma,F1,AAA,10,60,600,Retirement
Appanna,F2,BBB,5,200,1000,Retirement
Amma,F3,CCC,20,100,2000,Edu_A
"""

SUMMARIES = (
    "purpose,primary_winner\n"
    'Retirement,"AAA,BBB|AAA=0.6000,BBB=0.4000"\n'
    "Edu_A,CCC|CCC=1.0000\n"
)


def test_runner_composes_existing_lts_components(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    purposes.write_text(PURPOSES, encoding="utf-8")
    positions.write_text(POSITIONS, encoding="utf-8")
    summaries.write_text(SUMMARIES, encoding="utf-8")

    result = run_lts_transition(
        purposes_path=purposes,
        positions_path=positions,
        purpose_summaries_path=summaries,
    )

    assert result.plan.is_balanced
    assert [report.purpose for report in result.reports] == ["Edu_A", "Retirement"]
    assert all(report.is_balanced for report in result.reports)
    assert result.plan.portfolio_current_amount == Decimal("3600")
    assert result.plan.portfolio_target_amount == Decimal("3600")


def test_runner_does_not_reconcile_unattributed_positions(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    purposes.write_text(PURPOSES, encoding="utf-8")
    positions.write_text(
        POSITIONS.replace("Amma,F3,CCC,20,100,2000,Edu_A", "Amma,F3,CCC,20,100,2000,"),
        encoding="utf-8",
    )
    summaries.write_text(SUMMARIES, encoding="utf-8")

    import pytest

    with pytest.raises(ValueError, match="no Purpose attribution"):
        run_lts_transition(
            purposes_path=purposes,
            positions_path=positions,
            purpose_summaries_path=summaries,
        )
