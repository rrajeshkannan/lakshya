from decimal import Decimal

from lts.execution_playbook import (
    build_execution_playbook,
    export_execution_playbook_csv,
    write_execution_playbook,
)


def _slice(**overrides):
    row = {
        "current_investor": "Amma",
        "current_folio": "12799161 / 64",
        "current_isin": "INF179K01608",
        "target_investor": "Appanna",
        "target_folio": "NEW_FOLIO_1",
        "target_isin": "INF174K01LT0",
        "target_slice": "slice-1",
        "purpose": "Retirement",
        "disposition": "REDEEM",
        "locked": "false",
        "percentage": "17.947195",
        "units": "54.380",
        "nav": "2062.377",
        "market_value": "112152.06126",
    }
    row.update(overrides)
    return row


def test_redeem_slices_for_one_destination_sum_units_and_percentage():
    rows = build_execution_playbook([
        _slice(units="20.100", percentage="10.000000"),
        _slice(units="34.280", percentage="7.947195"),
        _slice(disposition="RETAIN", units="10.000", percentage="5.000000"),
    ])

    redemptions = list(rows)
    assert len(redemptions) == 1
    assert redemptions[0].units_to_redeem == Decimal("54.380")
    assert redemptions[0].pct_of_folio_holding == Decimal("17.947195")
    assert redemptions[0].execution_instruction == (
        "Redeem 54.380 units from Folio 12799161 / 64 (INF179K01608) "
        "and reinvest net proceeds into INF174K01LT0 under Appanna "
        "(NEW_FOLIO_1) for Retirement"
    )


def test_one_holding_keeps_a_separate_order_per_target():
    rows = build_execution_playbook([
        _slice(),
        _slice(
            target_investor="Amma",
            target_folio="11002736",
            target_isin="INF879O01027",
            target_slice="slice-4",
            purpose="Marriage",
            units="36.520",
            percentage="12.052805",
        ),
    ])

    redemptions = list(rows)
    assert [(row.units_to_redeem, row.purpose) for row in redemptions] == [
        (Decimal("36.520"), "Marriage"),
        (Decimal("54.380"), "Retirement"),
    ]
    assert sum(row.units_to_redeem for row in redemptions) == Decimal("90.900")
    assert sum(row.pct_of_folio_holding for row in redemptions) == Decimal("30.000000")


def test_playbook_csv_uses_three_decimal_units(tmp_path):
    slices = tmp_path / "materialized_transition_slices.csv"
    slices.write_text(
        "current_investor,current_folio,current_isin,target_investor,target_folio,"
        "target_isin,target_slice,purpose,disposition,locked,percentage,units,nav,market_value\n"
        "Amma,F1,SRC,Appanna,NEW_FOLIO_1,TGT,slice-1,Kutti,REDEEM,false,100,10.5,1,10.5\n",
        encoding="utf-8",
    )
    destination, _rows = write_execution_playbook(slices, tmp_path / "execution_playbook.csv")
    text = destination.read_text(encoding="utf-8")
    assert text.startswith(
        "source_investor,source_folio,source_isin,units_to_redeem,"
        "pct_of_folio_holding,target_investor,target_folio,target_isin,"
        "target_slice,purpose,execution_instruction\n"
    )
    assert "Amma,F1,SRC,10.500,100.000000,Appanna,NEW_FOLIO_1,TGT,slice-1,Kutti," in text
    assert "PURCHASE" not in text
    assert "action_type" not in text
    assert export_execution_playbook_csv(_rows) == text
