from pathlib import Path

from lps.run_nav import load_in_scope_isins


def test_load_in_scope_isins_reads_isin_column_and_deduplicates(tmp_path):
    scope = tmp_path / "funds_in_scope.csv"
    scope.write_text(
        "entry_type,isin\nCURRENT,ISIN_A\nPOTENTIAL,ISIN_B\nCURRENT,ISIN_A\n",
        encoding="utf-8",
    )

    assert load_in_scope_isins(scope) == ["ISIN_A", "ISIN_B"]


def test_load_in_scope_isins_rejects_empty_scope(tmp_path):
    scope = tmp_path / "funds_in_scope.csv"
    scope.write_text("entry_type,isin\nCURRENT,\n", encoding="utf-8")

    try:
        load_in_scope_isins(scope)
    except ValueError as exc:
        assert "No ISINs found" in str(exc)
    else:
        raise AssertionError("Expected empty scope to fail")
