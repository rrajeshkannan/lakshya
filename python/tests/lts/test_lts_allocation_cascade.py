from datetime import date
from decimal import Decimal

from lps.transactions import Transaction
from lps.positions import Position, PositionId
from lts.allocation_cascade import (
    ELSS_LOCKED,
    STCG_LOCKED,
    STAGE_CROSS_COMPOSITION,
    STAGE_IN_COMPOSITION,
    build_allocation_cascade,
    build_folio_directory,
    export_transition_slices_csv,
    redemption_lock_reason,
)
from lts.fund_metadata import FundClassification
from lts.models import FormationIntentRow, TargetFormation
from lts.position_bridge import LtsPosition, LtsPositionId
from lts.models import TransitionDisposition


AS_OF = date(2026, 9, 6)


def position(investor, folio, isin, units, nav, purpose="Edu"):
    units = Decimal(units)
    nav = Decimal(nav)
    return LtsPosition(
        id=LtsPositionId(investor, folio, isin, "Slice-1"),
        units=units,
        nav=nav,
        market_value=units * nav,
        purpose=purpose,
    )


def formation(*rows):
    return TargetFormation(rows=tuple(rows))


def row(purpose, isin, capital, weight):
    return FormationIntentRow(
        purpose=purpose,
        isin=isin,
        target_capital=Decimal(capital),
        target_weight=Decimal(weight),
    )


def classify(isin, asset_class, is_elss):
    return FundClassification(isin, asset_class, is_elss, "TEST")


def existing(investor, folio, isin, market_value=None, purpose=None):
    value = None if market_value is None else Decimal(market_value)
    return Position(
        id=PositionId(investor, folio, isin),
        units=Decimal("0") if value is None else Decimal("1"),
        nav=None,
        market_value=value,
        purpose=purpose,
    )


def purchase(investor, folio, isin, acquired_on, units, nav="10"):
    units = Decimal(units)
    nav = Decimal(nav)
    return Transaction(
        transaction_date=date.fromisoformat(acquired_on),
        event_type="Purchase",
        investor=investor,
        folio=folio,
        isin=isin,
        units=units,
        amount=units * nav,
        price=nav,
        source_description=f"{acquired_on}-{units}",
    )


def composition(plan, purpose, isin):
    return next(
        item
        for item in plan.review
        if item.record_type == "COMPOSITION" and item.purpose == purpose and item.isin == isin
    )


def test_elss_lock_is_strictly_under_three_years_and_stcg_includes_day_365():
    assert redemption_lock_reason(
        date(2023, 9, 7), AS_OF, is_elss=True, asset_class="equity"
    ) == ELSS_LOCKED
    assert redemption_lock_reason(
        date(2023, 9, 6), AS_OF, is_elss=True, asset_class="equity"
    ) is None
    assert redemption_lock_reason(
        date(2025, 9, 6), AS_OF, is_elss=False, asset_class="equity"
    ) == STCG_LOCKED
    assert redemption_lock_reason(
        date(2025, 9, 5), AS_OF, is_elss=False, asset_class="equity"
    ) is None
    assert redemption_lock_reason(
        date(2026, 9, 1), AS_OF, is_elss=False, asset_class="debt"
    ) is None
    assert redemption_lock_reason(
        date(2024, 2, 29), date(2027, 2, 27), is_elss=True, asset_class="equity"
    ) == ELSS_LOCKED
    assert redemption_lock_reason(
        date(2024, 2, 29), date(2027, 2, 28), is_elss=True, asset_class="equity"
    ) is None


def test_chosen_surplus_is_retained_and_reweights_the_same_purpose():
    plan = build_allocation_cascade(
        [
            position("I", "F1", "AAA", "70", "1"),
            position("I", "F2", "BBB", "30", "1"),
        ],
        formation(
            row("Edu", "AAA", "100", "0.4"),
            row("Edu", "BBB", "100", "0.6"),
        ),
    )

    assert {item.disposition for item in plan.slices} == {TransitionDisposition.RETAIN}
    assert composition(plan, "Edu", "AAA").stage == STAGE_IN_COMPOSITION
    assert composition(plan, "Edu", "AAA").adjusted_value == Decimal("70")
    assert composition(plan, "Edu", "BBB").adjusted_value == Decimal("30")
    assert composition(plan, "Edu", "BBB").stage == STAGE_IN_COMPOSITION
    assert all(item.stage != STAGE_CROSS_COMPOSITION for item in plan.review)


def test_unabsorbed_retained_surplus_cascades_into_another_purpose():
    plan = build_allocation_cascade(
        [
            position("I", "F1", "AAA", "80", "1", "Edu"),
            position("I", "F2", "AAA", "50", "1", "Ret"),
            position("I", "F3", "CCC", "20", "1", "Ret"),
        ],
        formation(
            row("Edu", "AAA", "80", "1"),
            row("Ret", "CCC", "70", "1"),
        ),
    )

    cascaded = [item for item in plan.slices if item.current_folio == "F2"]
    assert cascaded[0].purpose == "Ret"
    assert cascaded[0].disposition is TransitionDisposition.RETAIN
    assert cascaded[0].target_isin == "AAA"
    assert composition(plan, "Ret", "AAA").stage == STAGE_CROSS_COMPOSITION
    assert composition(plan, "Ret", "AAA").adjusted_value == Decimal("50")
    assert composition(plan, "Ret", "CCC").adjusted_value == Decimal("20")
    assert composition(plan, "Ret", "CCC").stage == STAGE_IN_COMPOSITION
    assert all(item.disposition is TransitionDisposition.RETAIN for item in plan.slices)


def test_partial_elss_lock_splits_units_and_percentages():
    plan = build_allocation_cascade(
        [position("I", "F1", "ELSS", "10", "10")],
        formation(row("Edu", "BBB", "100", "1")),
        transactions=[
            purchase("I", "F1", "ELSS", "2020-01-01", "4"),
            purchase("I", "F1", "ELSS", "2025-01-01", "6"),
        ],
        classifications={"ELSS": classify("ELSS", "equity", True), "BBB": classify("BBB", "equity", False)},
        as_of=AS_OF,
    )

    assert [(item.target_isin, item.target_slice, item.disposition, item.locked, item.units, item.percentage, item.disposition_reason) for item in plan.slices] == [
        ("ELSS", "slice-1", TransitionDisposition.RETAIN, True, Decimal("6"), Decimal("60"), ELSS_LOCKED),
        ("BBB", "slice-1", TransitionDisposition.REDEEM, False, Decimal("4"), Decimal("40"), None),
    ]
    assert plan.slices[0].target_folio == "F1"
    assert plan.slices[1].target_folio == "NEW_FOLIO_I_Edu_BBB"
    assert sum(item.units for item in plan.slices) == Decimal("10")
    assert sum(item.percentage for item in plan.slices) == Decimal("100")
    assert all(item.market_value == item.units * item.nav for item in plan.slices)


def test_equity_stcg_lock_splits_a_non_elss_holding():
    plan = build_allocation_cascade(
        [position("I", "F1", "EQ", "10", "10")],
        formation(row("Edu", "BBB", "100", "1")),
        transactions=[
            purchase("I", "F1", "EQ", "2025-09-05", "7"),
            purchase("I", "F1", "EQ", "2025-09-06", "3"),
        ],
        classifications={"EQ": classify("EQ", "equity", False), "BBB": classify("BBB", "equity", False)},
        as_of=AS_OF,
    )

    locked = next(item for item in plan.slices if item.locked)
    unlocked = next(item for item in plan.slices if not item.locked)
    assert locked.disposition is TransitionDisposition.RETAIN
    assert locked.disposition_reason == STCG_LOCKED
    assert locked.units == Decimal("3")
    assert unlocked.disposition is TransitionDisposition.REDEEM
    assert unlocked.units == Decimal("7")
    assert sum(item.percentage for item in plan.slices) == Decimal("100")


def test_recent_debt_lot_is_not_locked():
    plan = build_allocation_cascade(
        [position("I", "F1", "DEBT", "10", "10")],
        formation(row("Edu", "BBB", "100", "1")),
        transactions=[purchase("I", "F1", "DEBT", "2026-09-01", "10")],
        classifications={"DEBT": classify("DEBT", "debt", False), "BBB": classify("BBB", "equity", False)},
        as_of=AS_OF,
    )

    assert len(plan.slices) == 1
    assert plan.slices[0].locked is False
    assert plan.slices[0].disposition is TransitionDisposition.REDEEM
    assert plan.slices[0].percentage == Decimal("100")


def test_slice_csv_uses_the_fourteen_column_schema():
    plan = build_allocation_cascade(
        [position("I", "F1", "AAA", "10", "2")],
        formation(row("Edu", "AAA", "20", "1")),
    )

    header = export_transition_slices_csv(plan.slices).splitlines()[0]
    assert header == (
        "current_investor,current_folio,current_isin,target_investor,target_folio,"
        "target_isin,target_slice,purpose,disposition,locked,percentage,units,nav,market_value"
    )
    assert plan.slices[0].target_slice == "slice-1"
    assert plan.slices[0].market_value == Decimal("20")


def test_retain_target_folio_always_equals_current_folio():
    plan = build_allocation_cascade(
        [position("I", "F1", "AAA", "10", "2")],
        formation(row("Edu", "AAA", "20", "1")),
        existing_positions=[existing("I", "F9", "AAA", "999")],
    )

    assert plan.slices[0].disposition is TransitionDisposition.RETAIN
    assert plan.slices[0].target_folio == "F1"


def test_redeem_target_folio_resolves_to_investors_existing_folio():
    plan = build_allocation_cascade(
        [position("I", "F1", "AAA", "10", "10", "Edu")],
        formation(row("Edu", "BBB", "100", "1")),
        existing_positions=[
            existing("I", "F1", "AAA", "100", purpose="Retirement"),
            existing("I", "F2", "BBB", "50", purpose="Edu"),
        ],
    )

    redeemed = next(item for item in plan.slices if item.disposition is TransitionDisposition.REDEEM)
    assert redeemed.target_isin == "BBB"
    assert redeemed.target_folio == "F2"


def test_redeem_target_folio_prefers_the_highest_market_value_folio():
    directory = build_folio_directory([
        existing("I", "F_LOW", "BBB", "10", purpose="Edu"),
        existing("I", "F_HIGH", "BBB", "5000", purpose="Edu"),
        existing("I", "F_MID", "BBB", "500", purpose="Edu"),
        existing("I", "F_OTHER", "BBB", "9000", purpose="Retirement"),
    ])

    assert directory[("I", "Edu", "BBB")] == "F_HIGH"
    assert ("I", "Retirement", "BBB") in directory

    plan = build_allocation_cascade(
        [position("I", "F1", "AAA", "10", "10", "Edu")],
        formation(row("Edu", "BBB", "100", "1")),
        existing_positions=[
            existing("I", "F1", "AAA", "100", purpose="Retirement"),
            existing("I", "F_LOW", "BBB", "10", purpose="Edu"),
            existing("I", "F_HIGH", "BBB", "5000", purpose="Edu"),
            existing("I", "F_MID", "BBB", "500", purpose="Edu"),
        ],
    )
    redeemed = next(item for item in plan.slices if item.disposition is TransitionDisposition.REDEEM)
    assert redeemed.target_folio == "F_HIGH"


def test_redeem_target_folio_falls_back_to_new_folio_placeholder_when_absent():
    plan = build_allocation_cascade(
        [position("I", "F1", "AAA", "10", "10", "Edu")],
        formation(row("Edu", "BBB", "100", "1")),
        existing_positions=[existing("I", "F1", "AAA", "100")],
    )

    redeemed = next(item for item in plan.slices if item.disposition is TransitionDisposition.REDEEM)
    assert redeemed.target_folio == "NEW_FOLIO_I_Edu_BBB"


def test_redeem_reuses_a_zero_unit_folio_dedicated_to_the_purpose():
    plan = build_allocation_cascade(
        [position("I", "F1", "AAA", "10", "10", "Edu")],
        formation(row("Edu", "BBB", "100", "1")),
        existing_positions=[
            existing("I", "F1", "AAA", "100", purpose="Retirement"),
            existing("I", "F2", "BBB", purpose="Edu"),
        ],
    )

    redeemed = next(item for item in plan.slices if item.disposition is TransitionDisposition.REDEEM)
    assert redeemed.target_folio == "F2"


def test_redeem_target_folio_does_not_cross_investors():
    plan = build_allocation_cascade(
        [position("I", "F1", "AAA", "10", "10", "Edu")],
        formation(row("Edu", "BBB", "100", "1")),
        existing_positions=[
            existing("I", "F1", "AAA", "100"),
            existing("OTHER_INVESTOR", "F2", "BBB", "50", purpose="Edu"),
        ],
    )

    redeemed = next(item for item in plan.slices if item.disposition is TransitionDisposition.REDEEM)
    assert redeemed.target_folio == "NEW_FOLIO_I_Edu_BBB"


def _owned_value(plan, purpose, isin):
    totals: dict[str, Decimal] = {}
    for item in plan.slices:
        if item.purpose == purpose and item.target_isin == isin:
            totals[item.target_investor] = totals.get(item.target_investor, Decimal("0")) + item.market_value
    return totals


def test_redeemed_capital_is_split_to_an_equal_investor_share():
    plan = build_allocation_cascade(
        [
            position("Amma", "FA", "TGT", "50", "1"),
            position("Amma", "FA2", "SRC", "100", "1"),
            position("Appanna", "FB", "SRC2", "50", "1"),
        ],
        formation(row("Home_Loan", "TGT", "200", "1")),
        existing_positions=[
            existing("Amma", "FA", "TGT", "50", purpose="Home_Loan"),
            existing("Amma", "FAM", "TGT", "1", purpose="Home_Loan"),
            existing("Appanna", "FAP", "TGT", "9", purpose="Home_Loan"),
        ],
    )

    owned = _owned_value(plan, "Home_Loan", "TGT")
    assert owned["Amma"] == Decimal("100")
    assert owned["Appanna"] == Decimal("100")
    retained = [item for item in plan.slices if item.disposition is TransitionDisposition.RETAIN]
    assert len(retained) == 1
    assert retained[0].current_investor == "Amma"
    assert retained[0].target_investor == "Amma"
    assert retained[0].market_value == Decimal("50")
    routed = next(
        item
        for item in plan.slices
        if item.current_investor == "Amma"
        and item.disposition is TransitionDisposition.REDEEM
        and item.target_investor == "Appanna"
    )
    assert routed.target_folio == "FAP"
    assert routed.target_isin == "TGT"


def test_retain_above_half_sends_all_liquid_capital_to_the_other_investor():
    plan = build_allocation_cascade(
        [
            position("Amma", "FA", "TGT", "80", "1"),
            position("Amma", "FA2", "SRC", "20", "1"),
            position("Appanna", "FB", "RET", "100", "1"),
        ],
        formation(
            row("Home_Loan", "TGT", "100", "1"),
            row("Retirement", "RET", "100", "1"),
        ),
    )

    home = _owned_value(plan, "Home_Loan", "TGT")
    assert home["Amma"] == Decimal("80")
    assert home["Appanna"] == Decimal("20")
    liquid = next(item for item in plan.slices if item.disposition is TransitionDisposition.REDEEM)
    assert liquid.current_investor == "Amma"
    assert liquid.target_investor == "Appanna"
    assert liquid.purpose == "Home_Loan"
    retirement = _owned_value(plan, "Retirement", "RET")
    assert retirement == {"Appanna": Decimal("100")}
    assert all(
        item.target_investor == item.current_investor
        for item in plan.slices
        if item.disposition is TransitionDisposition.RETAIN
    )


def test_one_redeemed_holding_is_split_across_both_investors():
    plan = build_allocation_cascade(
        [
            position("Amma", "FA", "SRC", "100", "1"),
            position("Appanna", "FB", "TGT", "50", "1"),
        ],
        formation(row("Kutti", "TGT", "150", "1")),
        existing_positions=[
            existing("Amma", "FAM", "TGT", "4", purpose="Kutti"),
            existing("Appanna", "FB", "TGT", "50", purpose="Kutti"),
        ],
    )

    parts = [
        item
        for item in plan.slices
        if item.current_investor == "Amma" and item.current_isin == "SRC"
    ]
    assert sorted((item.target_investor, item.units, item.target_folio) for item in parts) == [
        ("Amma", Decimal("75"), "FAM"),
        ("Appanna", Decimal("25"), "FB"),
    ]
    assert sum(item.percentage for item in parts) == Decimal("100")
    assert sum(item.units for item in parts) == Decimal("100")
    owned = _owned_value(plan, "Kutti", "TGT")
    assert owned["Amma"] == Decimal("75")
    assert owned["Appanna"] == Decimal("75")


def _purposes_per_virtual_position(plan):
    grouped: dict[tuple[str, str, str, str], set[str]] = {}
    for item in plan.slices:
        key = (item.target_investor, item.target_folio, item.target_isin, item.target_slice)
        grouped.setdefault(key, set()).add(item.purpose)
    return grouped


def test_fresh_reinvestment_folios_are_isolated_by_purpose():
    plan = build_allocation_cascade(
        [
            position("I", "F1", "SRC", "60", "1"),
            position("I", "F2", "SRC2", "40", "1"),
        ],
        formation(
            row("Home_Loan", "TGT", "60", "1"),
            row("Kutti", "TGT", "40", "1"),
        ),
    )

    folios = {
        item.purpose: item.target_folio
        for item in plan.slices
        if item.disposition is TransitionDisposition.REDEEM
    }
    assert folios == {
        "Home_Loan": "NEW_FOLIO_I_Home_Loan_TGT",
        "Kutti": "NEW_FOLIO_I_Kutti_TGT",
    }
    assert all(item.target_slice == "slice-1" for item in plan.slices)
    assert max(len(purposes) for purposes in _purposes_per_virtual_position(plan).values()) == 1


def test_one_existing_folio_is_not_shared_across_purposes():
    plan = build_allocation_cascade(
        [
            position("I", "F1", "SRC", "50", "1"),
            position("I", "F2", "SRC2", "50", "1"),
        ],
        formation(
            row("Home_Loan", "TGT", "50", "1"),
            row("Kutti", "TGT", "50", "1"),
        ),
        existing_positions=[existing("I", "F_EXIST", "TGT", "10", purpose="Home_Loan")],
    )

    folios = {item.purpose: item.target_folio for item in plan.slices}
    assert folios["Home_Loan"] == "F_EXIST"
    assert folios["Kutti"] == "NEW_FOLIO_I_Kutti_TGT"
    by_purpose = {item.purpose: item.target_slice for item in plan.slices}
    assert by_purpose == {"Home_Loan": "slice-1", "Kutti": "slice-1"}
    virtual = _purposes_per_virtual_position(plan)
    assert max(len(purposes) for purposes in virtual.values()) == 1
    assert len(virtual) == 2
