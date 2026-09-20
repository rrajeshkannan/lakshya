import pytest

from fund_analysis.funds_in_scope import (
    load_fund_scope_rows,
    validate_scope_covers_positions,
)


def test_load_fund_scope_rows_rejects_unexpected_entry_type_column(tmp_path):
    scope = tmp_path / "funds_in_scope.csv"
    scope.write_text(
        "entry_type,isin,asset_class,is_elss\nCURRENT,ISIN_A,equity,no\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unexpected columns"):
        load_fund_scope_rows(scope)


def test_load_fund_scope_rows_accepts_equity_elss_and_debt_non_elss(tmp_path):
    scope = tmp_path / "funds_in_scope.csv"
    scope.write_text(
        "isin,asset_class,is_elss\n"
        "ISIN_A,equity,yes\n"
        "ISIN_B,debt,no\n",
        encoding="utf-8",
    )

    assert load_fund_scope_rows(scope) == [
        {"isin": "ISIN_A", "asset_class": "equity", "is_elss": "yes"},
        {"isin": "ISIN_B", "asset_class": "debt", "is_elss": "no"},
    ]


def test_validate_scope_covers_positions_is_asymmetric():
    validate_scope_covers_positions(
        scope_isins=["ISIN_A", "ISIN_B"],
        position_isins=["ISIN_A"],
    )

    with pytest.raises(ValueError, match="ISIN_B"):
        validate_scope_covers_positions(
            scope_isins=["ISIN_A"],
            position_isins=["ISIN_A", "ISIN_B"],
        )
