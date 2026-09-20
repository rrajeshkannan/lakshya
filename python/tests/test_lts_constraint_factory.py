from lts.constraint_factory import holding_constraint_for_fund
from lts.fund_metadata import FundClassification


def test_factory_preserves_explicit_elss_classification():
    classification = FundClassification("INF123", "Equity", True, "MFAPI")

    constraint = holding_constraint_for_fund(
        classification,
        long_term_holding_months=12,
    )

    assert constraint.isin == "INF123"
    assert constraint.is_elss is True
    assert constraint.long_term_holding_months == 12
    assert constraint.elss_lock_in_years == 3


def test_factory_does_not_infer_long_term_rule():
    classification = FundClassification("INF456", "Equity", False, "DEFAULT")

    constraint = holding_constraint_for_fund(classification)

    assert constraint.isin == "INF456"
    assert constraint.is_elss is False
    assert constraint.long_term_holding_months is None


def test_factory_rejects_invalid_thresholds():
    classification = FundClassification("INF789", "Equity", False, "MFAPI")

    try:
        holding_constraint_for_fund(classification, long_term_holding_months=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid holding-period threshold to fail")
