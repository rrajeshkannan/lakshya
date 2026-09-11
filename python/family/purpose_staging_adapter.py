"""Bridge human Purpose intent to the staging workspace.

The staging workspace may carry mutable working capital because it is the
reviewer's reconciliation state. The production Purpose source itself remains
intent-only; capital is seeded from LPS Position valuation.
"""

from __future__ import annotations

import csv
from pathlib import Path

from lps.purpose_capital import purpose_capital_from_positions


INTENT_FIELDS = {"name", "due", "desired", "monthly_plan"}


def load_intent_rows(source: Path, positions_path: Path) -> dict[str, dict[str, str]]:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not INTENT_FIELDS.issubset(rows[0]):
        raise ValueError(f"Purpose source is missing required intent columns: {source}")
    if set(rows[0]) != INTENT_FIELDS:
        raise ValueError(f"Purpose source contains non-intent columns: {source}")

    capital = purpose_capital_from_positions(positions_path)
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        name = row["name"].strip()
        if not name or name in result:
            raise ValueError(f"Blank or duplicate Purpose: {name!r}")
        if name not in capital:
            raise ValueError(f"LPS has no valued Position capital for Purpose: {name}")
        result[name] = {
            "name": name,
            "due": row["due"].strip(),
            "value": f"{capital[name]:g}",
            "desired": row["desired"].strip(),
            "monthly_plan": row["monthly_plan"].strip(),
        }
    return result
