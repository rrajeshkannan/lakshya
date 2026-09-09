"""Assemble the MISSION Purpose from intent and LPS factual evidence."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from .models import Purpose
from lps.purpose_capital import purpose_capital_from_positions

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PURPOSES_PATH = DATA_DIR / "purpose" / "purposes.csv"
POSITIONS_PATH = DATA_DIR / "lps" / "positions.csv"


INTENT_FIELDS = {"name", "due", "desired", "monthly_plan"}


def _parse_due(raw: str, name: str) -> date:
    """Parse the human Purpose-source date format, with ISO compatibility."""
    try:
        return date.fromisoformat(raw)
    except ValueError:
        try:
            return datetime.strptime(raw, "%d-%b-%Y").date()
        except ValueError as exc:
            raise ValueError(f"Invalid Purpose due date for {name}: {raw!r}") from exc


def _floor_years(start: date, due: date) -> int:
    years = due.year - start.year
    try:
        anniversary = start.replace(year=start.year + years)
    except ValueError:
        anniversary = start.replace(year=start.year + years, day=28)
    if anniversary > due:
        years -= 1
    return years


def load_purposes(
    as_of: date,
    *,
    purposes_path: Path = PURPOSES_PATH,
    positions_path: Path = POSITIONS_PATH,
) -> list[Purpose]:
    """Build flat MISSION Purpose objects from human intent + LPS capital."""
    with purposes_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not INTENT_FIELDS.issubset(rows[0]):
        raise ValueError(f"Purpose source is missing required intent columns: {purposes_path}")
    unexpected = set(rows[0]) - INTENT_FIELDS
    if unexpected:
        raise ValueError(
            f"Purpose source contains non-intent columns: {sorted(unexpected)}"
        )

    capital_by_purpose = purpose_capital_from_positions(positions_path)
    purposes: list[Purpose] = []
    seen: set[str] = set()
    for row in rows:
        name = row["name"].strip()
        if not name or name in seen:
            raise ValueError(f"Blank or duplicate Purpose: {name!r}")
        seen.add(name)
        if name not in capital_by_purpose:
            raise ValueError(f"LPS has no valued Position capital for Purpose: {name}")

        due_raw = row["due"].strip()
        due = None
        horizon = 7
        if due_raw and due_raw.upper() != "NA":
            due = _parse_due(due_raw, name)
            horizon = _floor_years(as_of, due)
            if horizon <= 0:
                raise ValueError(f"Purpose due date is not beyond as-of date: {name}")

        desired_raw = row["desired"].strip()
        monthly_raw = row["monthly_plan"].strip()
        desired = float(desired_raw) if desired_raw else None
        monthly = float(monthly_raw) if monthly_raw else None
        if desired is not None and desired < 0:
            raise ValueError(f"Negative desired target for Purpose: {name}")
        if monthly is not None and monthly < 0:
            raise ValueError(f"Negative monthly contribution for Purpose: {name}")

        purposes.append(
            Purpose(
                name=name,
                due=due,
                capital=capital_by_purpose[name],
                desired_target=desired,
                monthly_contribution=monthly,
                horizon_years=horizon if due is not None else None,
            )
        )
    return purposes


__all__ = ["load_purposes"]
