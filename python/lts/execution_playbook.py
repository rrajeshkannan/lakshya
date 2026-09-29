"""Turn materialized transition slices into unit-based redemption orders.

NAV moves every day, so each row tells the reviewer how many units to redeem
and which account receives the net proceeds.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from io import StringIO
from pathlib import Path
from typing import Mapping, Sequence

UNIT_QUANTUM = Decimal("0.001")
PERCENT_QUANTUM = Decimal("0.000001")
REDEEM = "REDEEM"
RETAIN = "RETAIN"

SLICE_FIELDS = (
    "current_investor",
    "current_folio",
    "current_isin",
    "target_investor",
    "target_folio",
    "target_isin",
    "target_slice",
    "purpose",
    "disposition",
    "percentage",
    "units",
)

PLAYBOOK_FIELDS = (
    "source_investor",
    "source_folio",
    "source_isin",
    "units_to_redeem",
    "pct_of_folio_holding",
    "target_investor",
    "target_folio",
    "target_isin",
    "target_slice",
    "purpose",
    "execution_instruction",
)


@dataclass(frozen=True)
class ExecutionPlaybookRow:
    """One source holding redeemed into one target account."""

    source_investor: str
    source_folio: str
    source_isin: str
    units_to_redeem: Decimal
    pct_of_folio_holding: Decimal
    target_investor: str
    target_folio: str
    target_isin: str
    target_slice: str
    purpose: str
    execution_instruction: str


def _require_fields(row: Mapping[str, str], source: str) -> None:
    missing = [field for field in SLICE_FIELDS if field not in row]
    if missing:
        raise ValueError(f"{source} is missing columns: {', '.join(missing)}")


def _quantize_units(value: Decimal) -> Decimal:
    return value.quantize(UNIT_QUANTUM, rounding=ROUND_HALF_EVEN)


def _quantize_percent(value: Decimal) -> Decimal:
    return value.quantize(PERCENT_QUANTUM, rounding=ROUND_HALF_EVEN)


def _format_units(value: Decimal) -> str:
    return format(_quantize_units(value), "f")


def _format_percent(value: Decimal) -> str:
    return format(_quantize_percent(value), "f")


def _redemption_instruction(
    *,
    units: Decimal,
    folio: str,
    isin: str,
    target_isin: str,
    target_investor: str,
    target_folio: str,
    purpose: str,
) -> str:
    return (
        f"Redeem {_format_units(units)} units from Folio {folio} ({isin}) "
        f"and reinvest net proceeds into {target_isin} under {target_investor} "
        f"({target_folio}) for {purpose}"
    )


def build_execution_playbook(
    slice_rows: Sequence[Mapping[str, str]],
) -> tuple[ExecutionPlaybookRow, ...]:
    """Aggregate redeem slices into one order per source holding and target.

    Units and percentages on a row are the sum of every slice in that pair.
    Rows that share ``(current_investor, current_folio, current_isin)`` are
    the full redemption of that physical holding. ``RETAIN`` slices are not
    orders.
    """
    grouped: dict[tuple[str, ...], list[Mapping[str, str]]] = defaultdict(list)
    for index, row in enumerate(slice_rows):
        _require_fields(row, f"slice row {index + 1}")
        disposition = row["disposition"].strip()
        if disposition == RETAIN:
            continue
        if disposition != REDEEM:
            raise ValueError(f"Unsupported disposition {disposition!r} on slice row {index + 1}.")
        key = (
            row["current_investor"].strip(),
            row["current_folio"].strip(),
            row["current_isin"].strip(),
            row["target_investor"].strip(),
            row["target_folio"].strip(),
            row["target_isin"].strip(),
            row["target_slice"].strip(),
            row["purpose"].strip(),
        )
        grouped[key].append(row)

    redemptions: list[ExecutionPlaybookRow] = []
    for key in sorted(grouped):
        investor, folio, isin, target_investor, target_folio, target_isin, target_slice, purpose = key
        units = sum((Decimal(row["units"]) for row in grouped[key]), Decimal("0"))
        percentage = sum((Decimal(row["percentage"]) for row in grouped[key]), Decimal("0"))
        units = _quantize_units(units)
        percentage = _quantize_percent(percentage)
        redemptions.append(ExecutionPlaybookRow(
            source_investor=investor,
            source_folio=folio,
            source_isin=isin,
            units_to_redeem=units,
            pct_of_folio_holding=percentage,
            target_investor=target_investor,
            target_folio=target_folio,
            target_isin=target_isin,
            target_slice=target_slice,
            purpose=purpose,
            execution_instruction=_redemption_instruction(
                units=units,
                folio=folio,
                isin=isin,
                target_isin=target_isin,
                target_investor=target_investor,
                target_folio=target_folio,
                purpose=purpose,
            ),
        ))
    return tuple(redemptions)


def playbook_slices_ready(path: Path) -> bool:
    """Return whether ``path`` is a cascade slice file this playbook can read."""
    if not path.is_file():
        return False
    with path.open(newline="", encoding="utf-8") as handle:
        header = handle.readline().strip()
    columns = header.split(",")
    return all(field in columns for field in SLICE_FIELDS)


def read_transition_slice_rows(path: Path) -> tuple[dict[str, str], ...]:
    """Read cascade materialized slices. ``RETAIN`` rows stay in the file for the builder."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header.")
        missing = [field for field in SLICE_FIELDS if field not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
        return tuple(dict(row) for row in reader)


def export_execution_playbook_csv(rows: Sequence[ExecutionPlaybookRow]) -> str:
    """Return the playbook CSV text."""
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(PLAYBOOK_FIELDS)
    for row in rows:
        writer.writerow([
            row.source_investor,
            row.source_folio,
            row.source_isin,
            _format_units(row.units_to_redeem),
            _format_percent(row.pct_of_folio_holding),
            row.target_investor,
            row.target_folio,
            row.target_isin,
            row.target_slice,
            row.purpose,
            row.execution_instruction,
        ])
    return output.getvalue()


def format_redemption_summary(rows: Sequence[ExecutionPlaybookRow]) -> str:
    """Summarize unit redemption orders, with one total per physical holding."""
    redemptions = list(rows)
    if not redemptions:
        return "No unit-based redemption orders."

    holding_units: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    holding_pct: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in redemptions:
        key = (row.source_investor, row.source_folio, row.source_isin)
        holding_units[key] += row.units_to_redeem
        holding_pct[key] += row.pct_of_folio_holding

    lines = ["Unit-based redemption orders ready for sign-off:"]
    current_holding: tuple[str, str, str] | None = None
    for row in redemptions:
        key = (row.source_investor, row.source_folio, row.source_isin)
        if key != current_holding:
            current_holding = key
            lines.append(
                f"HOLDING {row.source_investor} | {row.source_folio} | {row.source_isin} | "
                f"{_format_units(holding_units[key])} units | "
                f"{_format_percent(holding_pct[key])}% of the folio"
            )
        lines.append(
            f"  {_format_units(row.units_to_redeem)} units | "
            f"{_format_percent(row.pct_of_folio_holding)}% | "
            f"-> {row.target_investor} {row.target_folio} {row.target_isin} "
            f"{row.target_slice} {row.purpose}"
        )
    lines.append(f"Redemption orders: {len(redemptions)}")
    return "\n".join(lines)


def write_execution_playbook(
    slices_path: Path,
    destination: Path,
) -> tuple[Path, tuple[ExecutionPlaybookRow, ...]]:
    """Read cascade slices and write ``execution_playbook.csv`` atomically."""
    rows = build_execution_playbook(read_transition_slice_rows(slices_path))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(export_execution_playbook_csv(rows), encoding="utf-8")
    temporary.replace(destination)
    return destination, rows


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    slices_path = root / "data" / "lts" / "materialized_transition_slices.csv"
    destination = root / "data" / "lts" / "execution_playbook.csv"
    playbook_path, rows = write_execution_playbook(slices_path, destination)
    print(format_redemption_summary(rows))
    print(f"Execution playbook: {playbook_path.relative_to(root)}")
    print("Preview:")
    print("".join(playbook_path.read_text(encoding="utf-8").splitlines(keepends=True)[:6]), end="")


if __name__ == "__main__":
    main()


__all__ = [
    "ExecutionPlaybookRow",
    "build_execution_playbook",
    "export_execution_playbook_csv",
    "format_redemption_summary",
    "playbook_slices_ready",
    "read_transition_slice_rows",
    "write_execution_playbook",
]
