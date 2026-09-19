from lts.fund_metadata import (
    FundClassification,
    TransitionFundMetadata,
    classify_fund,
    project_fund_metadata,
)


def test_project_fund_metadata_exposes_only_transition_relevant_fields():
    metadata = project_fund_metadata(
        "INF001",
        {
            "schemeName": "Example Equity Fund",
            "schemeCategory": "Equity Scheme - Large Cap",
            "schemeType": "Open Ended Schemes",
            "schemeCode": 12345,
            "unrelated": "not exposed",
        },
    )
    assert metadata == TransitionFundMetadata(
        isin="INF001",
        scheme_name="Example Equity Fund",
        scheme_category="Equity Scheme - Large Cap",
        scheme_type="Open Ended Schemes",
    )


def test_classify_elss_from_scheme_category():
    assert classify_fund(
        TransitionFundMetadata("INF001", scheme_category="Equity Scheme - ELSS")
    ) == FundClassification("INF001", "Equity", True, "MFAPI")


def test_classify_equity_non_elss_from_scheme_category():
    result = classify_fund(
        TransitionFundMetadata("INF001", scheme_category="Equity Scheme - Large Cap")
    )
    assert result.asset_class == "Equity"
    assert result.is_elss is False
    assert result.source == "MFAPI"


def test_classify_debt_from_scheme_category():
    result = classify_fund(
        TransitionFundMetadata("INF001", scheme_category="Debt Scheme - Corporate Bond")
    )
    assert result.asset_class == "Debt"
    assert result.is_elss is False
    assert result.source == "MFAPI"


def test_classify_missing_metadata_uses_explicit_default():
    assert classify_fund(TransitionFundMetadata("INF001")) == FundClassification(
        "INF001", "Equity", False, "DEFAULT"
    )
