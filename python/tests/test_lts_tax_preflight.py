from datetime import date
from decimal import Decimal

from lts.fund_metadata import FundClassification
from lts.lots import HoldingLot
from lts.tax_preflight import (
    EXEMPTION,
    InvestorTax,
    _redeem_cost,
    format_inr,
    render_tax_preflight,
)

AS_OF = date(2026, 9, 6)
EQUITY = FundClassification("INF000000000", "equity", False, "TEST")
ELSS = FundClassification("INF000000000", "equity", True, "TEST")


def _lot(acquired: date, units: str, amount: str) -> HoldingLot:
    quantity = Decimal(units)
    return HoldingLot(
        transaction_date=acquired,
        units_acquired=quantity,
        units_remaining=quantity,
        transaction_amount=Decimal(amount),
        transaction_price=Decimal(amount) / quantity,
        source_description="test",
    )


def test_short_term_equity_lot_is_excluded_from_acquisition_cost():
    cost = _redeem_cost(
        (
            _lot(date(2026, 1, 1), "10", "1000"),
            _lot(date(2020, 1, 1), "10", "500"),
        ),
        holding_units=Decimal("20"),
        redeemed_units=Decimal("10"),
        as_of=AS_OF,
        classification=EQUITY,
    )
    assert cost == Decimal("500")


def test_elss_lot_inside_three_years_is_excluded_from_acquisition_cost():
    cost = _redeem_cost(
        (
            _lot(date(2024, 9, 7), "10", "1000"),
            _lot(date(2020, 1, 1), "10", "400"),
        ),
        holding_units=Decimal("20"),
        redeemed_units=Decimal("10"),
        as_of=AS_OF,
        classification=ELSS,
    )
    assert cost == Decimal("400")


def test_tax_is_twelve_and_a_half_percent_above_the_exemption():
    below = InvestorTax("Amma", Decimal("200000"), Decimal("100000"))
    assert below.gain == Decimal("100000")
    assert below.taxable == Decimal("0")
    assert below.tax == Decimal("0.00")

    above = InvestorTax("Appanna", Decimal("300000"), Decimal("50000"))
    assert above.gain - EXEMPTION == Decimal("125000")
    assert above.tax == Decimal("15625.00")


def test_report_uses_indian_grouping_and_the_family_total():
    text = render_tax_preflight((
        InvestorTax("Amma", Decimal("500000"), Decimal("200000")),
        InvestorTax("Appanna", Decimal("100000"), Decimal("100000")),
    ))
    assert "--- INVESTOR 1: AMMA ---" in text
    assert "--- INVESTOR 2: APPANNA ---" in text
    assert "Annual Exemption (112A):" in text
    assert format_inr(EXEMPTION) == "₹1,25,000.00"
    assert "₹1,25,000.00" in text
    assert "[Earmark for March 15 Advance Tax]" in text
    assert "TOTAL ADVANCE TAX TO EARMARK ACROSS FAMILY: ₹21,875.00" in text
