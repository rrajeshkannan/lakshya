from datetime import date
from decimal import Decimal

import pandas as pd

from lps.nav_evidence import NavEvidenceStore
from lps.position_persistence import read_positions
from lps.transaction_persistence import write_transactions
from lps.transactions import Transaction
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
    assert result.current_input.diagnostics.total_records == 3
    assert result.current_input.diagnostics.active_records == 3
    assert result.current_input.diagnostics.inactive_records == 0


def test_runner_excludes_zero_unit_inactive_records(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    purposes.write_text(PURPOSES, encoding="utf-8")
    positions.write_text(
        POSITIONS.replace(
            "Amma,F3,CCC,20,100,2000,Edu_A",
            "Amma,F3,CCC,20,100,2000,Edu_A\nAmma,F4,DDD,0,,,",
        ),
        encoding="utf-8",
    )
    summaries.write_text(SUMMARIES, encoding="utf-8")

    result = run_lts_transition(
        purposes_path=purposes,
        positions_path=positions,
        purpose_summaries_path=summaries,
    )

    assert result.plan.is_balanced
    assert result.current_input.diagnostics.total_records == 4
    assert result.current_input.diagnostics.active_records == 3
    assert result.current_input.diagnostics.inactive_records == 1
    assert [position.id.isin for position in result.positions] == ["AAA", "BBB", "CCC"]


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


def test_runner_uses_transaction_and_nav_evidence_when_available(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    transactions = tmp_path / "transactions.csv"
    nav_root = tmp_path / "nav"

    purposes.write_text(PURPOSES, encoding="utf-8")
    positions.write_text(POSITIONS, encoding="utf-8")
    summaries.write_text(SUMMARIES, encoding="utf-8")

    persisted_positions = read_positions(positions)
    write_transactions(
        transactions,
        [
            Transaction(
                transaction_date=date(2020, 1, 1),
                event_type="Purchase",
                investor=position.id.investor,
                folio=position.id.folio,
                isin=position.id.isin,
                units=position.units,
                amount=position.market_value,
                price=position.nav,
                source_description="test fixture",
            )
            for position in persisted_positions
        ],
    )

    for position in persisted_positions:
        store = NavEvidenceStore(nav_root / f"{position.id.isin}.json")
        store.create(
            isin=position.id.isin,
            scheme_code=1,
            source="test",
            nav=pd.DataFrame(
                [{"date": "2026-09-20", "nav": str(position.nav)}]
            ),
            retrieved_at="2026-09-21T00:00:00Z",
        )

    result = run_lts_transition(
        purposes_path=purposes,
        positions_path=positions,
        transactions_path=transactions,
        nav_root=nav_root,
        purpose_summaries_path=summaries,
        as_of=date(2026, 9, 20),
    )

    assert len(result.evidence.positions) == 3
    assert len(result.evidence.transactions) == 3
    assert len(result.availability) == 3
    assert all(report.locked_units == Decimal("0") for report in result.availability)
    assert all(report.unlocked_units > Decimal("0") for report in result.availability)
