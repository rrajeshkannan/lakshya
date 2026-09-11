"""Build the human-facing Purpose review surface for an annual staging review.

This is a presentation/checkpoint layer. It does not alter LFS decisions,
Purpose intent, or staging semantics. It reads the staged Purpose state and
latest FINAL/achievability evidence, then writes a compact review CSV.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from pathlib import Path

from mission.achievability import required_annual_return
from mission.models import Purpose

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

REVIEW_FIELDS = [
    "purpose",
    "current_corpus",
    "target_corpus",
    "gap_today",
    "monthly_sip",
    "due",
    "horizon_years",
    "selected_composition",
    "selected_formation",
    "observed_upper_return",
    "required_annual_return",
    "achievability_status",
]

PURPOSE_FIELDS = ["name", "due", "value", "desired", "monthly_plan"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def _number(raw: str) -> float | None:
    text = str(raw).strip()
    if not text:
        return None
    return float(text)


def _parse_due(raw: str) -> date | None:
    text = raw.strip()
    if not text or text.upper() == "NA":
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text, "%d-%b-%Y").date()


def _floor_years(start: date, due: date) -> int:
    years = due.year - start.year
    try:
        anniversary = start.replace(year=start.year + years)
    except ValueError:
        anniversary = start.replace(year=start.year + years, day=28)
    if anniversary > due:
        years -= 1
    return years


def _format_money(raw: str) -> str:
    value = _number(raw)
    return "" if value is None else f"{value:.2f}"


def _format_percent(raw: str) -> str:
    value = _number(raw)
    return "" if value is None else f"{value * 100:.2f}%"


def _format_formation(identity: str) -> str:
    try:
        _, weights_raw = identity.split("|", 1)
        parts = []
        for token in weights_raw.split(","):
            isin, weight = token.split("=", 1)
            parts.append(f"{isin}:{float(weight) * 100:.0f}%")
        return " | ".join(parts)
    except (ValueError, TypeError):
        return identity


def _final_evidence(data_dir: Path, as_of: str) -> dict[str, tuple[str, float]]:
    review_dir = data_dir / "reviews" / as_of
    output_dir = data_dir.parent / "output"
    result: dict[str, tuple[str, float]] = {}
    for summary in sorted(review_dir.glob("*_summary.csv")):
        rows = _read_csv(summary)
        if len(rows) != 1:
            continue
        purpose = rows[0].get("purpose", "").strip()
        winner = rows[0].get("primary_winner", "").strip()
        if not purpose or not winner:
            continue
        checkpoint = output_dir / f"achievability_{purpose}.csv"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Achievability checkpoint missing: {checkpoint}")
        matches = [row for row in _read_csv(checkpoint) if row.get("composition") == winner]
        if len(matches) != 1:
            raise ValueError(f"Cannot recover selected achievability evidence for {purpose}")
        upper = _number(matches[0].get("observed_upper_return", ""))
        if upper is None:
            raise ValueError(f"Selected achievability evidence has no observed upper return: {purpose}")
        result[purpose] = (winner, upper)
    return result


def refresh_review_surface(as_of: str, *, data_dir: Path = DATA_DIR) -> Path:
    date.fromisoformat(as_of)
    directory = data_dir / "reviews" / as_of / "purpose_staging"
    staged_path = directory / "purposes_staged.csv"
    rows = _read_csv(staged_path)
    if not rows or set(rows[0]) != set(PURPOSE_FIELDS):
        raise ValueError(f"Staged Purpose file has an unexpected column layout: {staged_path}")

    evidence = _final_evidence(data_dir, as_of)
    review_rows: list[dict[str, str]] = []
    normalized_rows: list[dict[str, str]] = []
    as_of_date = date.fromisoformat(as_of)

    for row in rows:
        current = _number(row["value"])
        target = _number(row["desired"])
        monthly = _number(row["monthly_plan"])
        if current is None:
            raise ValueError(f"Missing current corpus for {row['name']}")
        due = _parse_due(row["due"])
        horizon = "" if due is None else str(_floor_years(as_of_date, due))
        gap = "" if target is None else f"{current - target:.2f}"

        winner, upper = evidence.get(row["name"], ("", None))
        required_text = ""
        status = "not_applicable"
        if target is not None and due is not None:
            purpose = Purpose(
                name=row["name"],
                due=due,
                capital=current,
                desired_target=target,
                monthly_contribution=monthly,
                horizon_years=int(horizon),
            )
            required = required_annual_return(purpose)
            if required is not None:
                required_text = f"{required:.10f}"
                status = (
                    "within_observed_terrain"
                    if upper is not None and required <= upper
                    else "beyond_observed_terrain"
                    if upper is not None
                    else "insufficient_evidence"
                )

        normalized_rows.append({
            "name": row["name"],
            "due": row["due"],
            "value": f"{current:.2f}",
            "desired": "" if target is None else f"{target:.2f}",
            "monthly_plan": "" if monthly is None else f"{monthly:.2f}",
        })
        review_rows.append({
            "purpose": row["name"],
            "current_corpus": f"{current:.2f}",
            "target_corpus": "" if target is None else f"{target:.2f}",
            "gap_today": gap,
            "monthly_sip": "" if monthly is None else f"{monthly:.2f}",
            "due": row["due"],
            "horizon_years": horizon,
            "selected_composition": winner,
            "selected_formation": _format_formation(winner),
            "observed_upper_return": "" if upper is None else _format_percent(str(upper)),
            "required_annual_return": required_text,
            "achievability_status": status,
        })

    _write_csv(staged_path, PURPOSE_FIELDS, normalized_rows)
    output = directory / "purpose_review_latest.csv"
    _write_csv(output, REVIEW_FIELDS, review_rows)
    return output
