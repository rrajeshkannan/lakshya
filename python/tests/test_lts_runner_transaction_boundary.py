from datetime import date
from decimal import Decimal

import pandas as pd

from lps.nav_evidence import NavEvidenceStore
from lps.position_persistence import read_positions
from lps.transaction_persistence import write_transactions
from lps.transactions import Transaction
from lts.runner import run_lts_transition


def test_runner_uses_as_of_for_lock_in_analysis_and_human_scope(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    transactions = tmp_path / "transactions.csv"
    nav_root = tmp_path / "nav"
    scope = tmp_path / "funds_in_scope.csv"

    purposes.write_text("name,due,desired,monthly_plan\nEdu_A,2027-04-01,1000,0\n", encoding="utf-8")
    positions.write_text(
        "investor,folio,isin,units,nav,market_value,purpose\n"
        "Appanna,F1,ELSS,10,100,1000,Edu_A\n", encoding="utf-8"
    )
    summaries.write_text("purpose,primary_winner\nEdu_A,ELSS|ELSS=1.0000\n", encoding="utf-8")
    scope.write_text("isin,asset_class,is_elss\nELSS,equity,yes\n", encoding="utf-8")

    position = read_positions(positions)[0]
    write_transactions(
        transactions,
        [
            Transaction(date(2023, 1, 1), "Purchase", position.id.investor, position.id.folio, position.id.isin, Decimal("5"), Decimal("500"), Decimal("100"), "before boundary"),
            Transaction(date(2026, 1, 1), "Purchase", position.id.investor, position.id.folio, position.id.isin, Decimal("5"), Decimal("500"), Decimal("100"), "after boundary"),
        ],
    )

    store = NavEvidenceStore(nav_root / "ELSS.json")
    store.create(
        isin="ELSS",
        scheme_code=1,
        source="test",
        nav=pd.DataFrame([
            {"date": "2024-12-31", "nav": "100"},
            {"date": "2026-09-20", "nav": "100"},
        ]),
        retrieved_at="2026-09-21T00:00:00Z",
    )

    result = run_lts_transition(
        purposes_path=purposes,
        positions_path=positions,
        transactions_path=transactions,
        nav_root=nav_root,
        purpose_summaries_path=summaries,
        fund_scope_path=scope,
        as_of=date(2024, 12, 31),
    )

    assert len(result.evidence.transactions) == 1
    assert result.evidence.transactions[0].source_description == "before boundary"
    assert result.availability[0].locked_units == Decimal("5")
    assert result.availability[0].unlocked_units == Decimal("0")
