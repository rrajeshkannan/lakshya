from lps.run_nav import load_in_scope_isins


def test_load_in_scope_isins_reads_valid_scope(tmp_path):
    scope = tmp_path / "funds_in_scope.csv"
    scope.write_text(
        "isin,asset_class,is_elss\n"
        "ISIN_A,equity,no\n"
        "ISIN_B,equity,yes\n",
        encoding="utf-8",
    )

    assert load_in_scope_isins(scope) == ["ISIN_A", "ISIN_B"]


def test_load_in_scope_isins_rejects_blank_classification(tmp_path):
    scope = tmp_path / "funds_in_scope.csv"
    scope.write_text(
        "isin,asset_class,is_elss\n"
        "ISIN_A,,\n",
        encoding="utf-8",
    )

    try:
        load_in_scope_isins(scope)
    except ValueError as exc:
        assert "blank asset_class" in str(exc)
    else:
        raise AssertionError("Expected blank classification to fail")


def test_load_in_scope_isins_rejects_debt_elss(tmp_path):
    scope = tmp_path / "funds_in_scope.csv"
    scope.write_text(
        "isin,asset_class,is_elss\n"
        "ISIN_A,debt,yes\n",
        encoding="utf-8",
    )

    try:
        load_in_scope_isins(scope)
    except ValueError as exc:
        assert "Debt fund cannot be marked ELSS" in str(exc)
    else:
        raise AssertionError("Expected debt ELSS classification to fail")
