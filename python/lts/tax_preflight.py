"""Advance-tax estimate for the cascade redemption book.

Cost is the FIFO acquisition amount on lots the lock rules leave sellable.
The seller is the source investor. Section 112A's ₹1,25,000 exemption and
the 12.5% rate are applied to that investor's realized gain.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

from fund_analysis.funds_in_scope import load_fund_scope_rows
from lps.positions import PositionId
from lps.transaction_persistence import read_transactions

from .allocation_cascade import redemption_lock_reason
from .fund_metadata import FundClassification, classify_scope_row
from .lots import HoldingLot, fifo_holding_lots

ZERO = Decimal("0")
PAISE = Decimal("0.01")
EXEMPTION = Decimal("125000")
LTCG_RATE = Decimal("0.125")
UNIT_TOLERANCE = Decimal("0.05")
INVESTORS = ("Amma", "Appanna")
RULE = "=" * 68


@dataclass(frozen=True)
class InvestorTax:
    investor: str
    proceeds: Decimal
    cost: Decimal

    @property
    def gain(self) -> Decimal:
        return self.proceeds - self.cost

    @property
    def taxable(self) -> Decimal:
        excess = self.gain - EXEMPTION
        return excess if excess > ZERO else ZERO

    @property
    def tax(self) -> Decimal:
        return (self.taxable * LTCG_RATE).quantize(PAISE, rounding=ROUND_HALF_EVEN)


def format_inr(amount: Decimal) -> str:
    """Format a rupee amount with Indian digit grouping and two paise places."""
    quantized = amount.quantize(PAISE, rounding=ROUND_HALF_EVEN)
    sign = "-" if quantized < ZERO else ""
    whole, frac = f"{abs(quantized):.2f}".split(".")
    if len(whole) > 3:
        tail = whole[-3:]
        head = whole[:-3]
        groups: list[str] = []
        while head:
            groups.append(head[-2:])
            head = head[:-2]
        whole = ",".join(reversed(groups)) + "," + tail
    return f"{sign}₹{whole}.{frac}"


def _unit_cost(lot: HoldingLot) -> Decimal:
    if lot.units_acquired <= ZERO:
        raise ValueError(f"Acquisition lot has no units: {lot.source_description}")
    if lot.transaction_amount is not None:
        return lot.transaction_amount / lot.units_acquired
    if lot.transaction_price is not None:
        return lot.transaction_price
    raise ValueError(
        "Acquisition lot has no amount and no price: "
        f"{lot.transaction_date.isoformat()} {lot.source_description}"
    )


def _redeem_cost(
    lots: tuple[HoldingLot, ...],
    *,
    holding_units: Decimal,
    redeemed_units: Decimal,
    as_of: date,
    classification: FundClassification,
) -> Decimal:
    """FIFO cost of ``redeemed_units``, taken from lots the lock rules allow to be sold."""
    if redeemed_units <= ZERO:
        return ZERO
    lot_units = sum((lot.units_remaining for lot in lots), ZERO)
    if lot_units <= ZERO:
        raise ValueError("Redeemed holding has no remaining acquisition lots.")
    sellable: list[tuple[Decimal, Decimal]] = []
    for lot in lots:
        reason = redemption_lock_reason(
            lot.transaction_date,
            as_of,
            is_elss=classification.is_elss,
            asset_class=classification.asset_class,
        )
        if reason is not None:
            continue
        scaled_units = lot.units_remaining * holding_units / lot_units
        if scaled_units > ZERO:
            sellable.append((scaled_units, _unit_cost(lot)))
    remaining = redeemed_units
    cost = ZERO
    for units, unit_cost in sellable:
        take = min(units, remaining)
        cost += take * unit_cost
        remaining -= take
        if remaining <= ZERO:
            break
    if remaining > UNIT_TOLERANCE:
        raise ValueError(
            "Redeemed units exceed the unlocked FIFO lots available for cost: "
            f"short {remaining} units."
        )
    if remaining > ZERO and sellable:
        cost += remaining * sellable[-1][1]
    return cost


def _load_classifications(fund_scope_path: Path) -> dict[str, FundClassification]:
    return {
        row["isin"]: classify_scope_row(row)
        for row in load_fund_scope_rows(fund_scope_path)
    }


def investor_tax_from_slices(
    slice_rows: list[dict[str, str]],
    *,
    transactions_path: Path,
    fund_scope_path: Path,
    as_of: date,
) -> tuple[InvestorTax, ...]:
    """Sum redemption proceeds and FIFO cost by the investor who sells."""
    holdings: dict[tuple[str, str, str], dict[str, Decimal]] = defaultdict(
        lambda: {"units": ZERO, "redeemed_units": ZERO, "proceeds": ZERO}
    )
    for row in slice_rows:
        key = (row["current_investor"].strip(), row["current_folio"].strip(), row["current_isin"].strip())
        units = Decimal(row["units"])
        holdings[key]["units"] += units
        if row["disposition"].strip() == "REDEEM":
            holdings[key]["redeemed_units"] += units
            holdings[key]["proceeds"] += Decimal(row["market_value"])

    classifications = _load_classifications(fund_scope_path)
    transactions = read_transactions(transactions_path)
    proceeds = {name: ZERO for name in INVESTORS}
    cost = {name: ZERO for name in INVESTORS}
    for (investor, folio, isin), totals in holdings.items():
        if totals["redeemed_units"] <= ZERO:
            continue
        if investor not in proceeds:
            proceeds[investor] = ZERO
            cost[investor] = ZERO
        try:
            classification = classifications[isin]
        except KeyError as exc:
            raise KeyError(f"No fund classification for redeemed ISIN {isin}") from exc
        lots = fifo_holding_lots(
            transactions,
            PositionId(investor, folio, isin),
            as_of=as_of,
        )
        proceeds[investor] += totals["proceeds"]
        cost[investor] += _redeem_cost(
            lots,
            holding_units=totals["units"],
            redeemed_units=totals["redeemed_units"],
            as_of=as_of,
            classification=classification,
        )
    names = list(INVESTORS) + sorted(set(proceeds) - set(INVESTORS))
    return tuple(
        InvestorTax(investor=name, proceeds=proceeds.get(name, ZERO), cost=cost.get(name, ZERO))
        for name in names
    )


def render_tax_preflight(results: tuple[InvestorTax, ...]) -> str:
    """Render the FY 2026-27 advance-tax sheet."""
    labels = (
        "Gross Redemption Proceeds:",
        "Total Cost of Acquisition:",
        "Total Realized LTCG:",
        "Annual Exemption (112A):",
        "Net Taxable LTCG:",
        "TAX PAYABLE (@ 12.5%):",
    )
    width = max(len(label) for label in labels)
    lines = [
        RULE,
        "               LTS PRE-FLIGHT ADVANCE TAX REPORT (FY 2026-27)",
        RULE,
        "",
    ]
    family_tax = ZERO
    for index, result in enumerate(results, start=1):
        amounts = (
            result.proceeds,
            result.cost,
            result.gain,
            EXEMPTION,
            result.taxable,
            result.tax,
        )
        lines.append(f"--- INVESTOR {index}: {result.investor.upper()} ---")
        for label, amount in zip(labels, amounts, strict=True):
            rendered = f" {label:<{width}} {format_inr(amount)}"
            if label.startswith("TAX PAYABLE"):
                rendered += " [Earmark for March 15 Advance Tax]"
            lines.append(rendered)
            if label == "Total Realized LTCG:":
                lines.append(" " + "-" * 50)
        lines.append("")
        family_tax += result.tax
    lines.extend([
        RULE,
        f" TOTAL ADVANCE TAX TO EARMARK ACROSS FAMILY: {format_inr(family_tax)}",
        RULE,
        "",
    ])
    return "\n".join(lines)


def write_tax_preflight_report(
    *,
    slices_path: Path,
    transactions_path: Path,
    fund_scope_path: Path,
    as_of: date,
    destination: Path,
) -> tuple[Path, str]:
    """Read cascade slices and write the advance-tax report."""
    with slices_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    text = render_tax_preflight(investor_tax_from_slices(
        rows,
        transactions_path=transactions_path,
        fund_scope_path=fund_scope_path,
        as_of=as_of,
    ))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(destination)
    return destination, text


__all__ = [
    "EXEMPTION",
    "LTCG_RATE",
    "InvestorTax",
    "format_inr",
    "investor_tax_from_slices",
    "render_tax_preflight",
    "write_tax_preflight_report",
]
