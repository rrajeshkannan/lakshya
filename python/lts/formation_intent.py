"""LFS -> LTS Formation Intent projection.

Formation Intent combines the reviewed Purpose state with the selected FINAL
Composition for each Purpose. Purpose capital remains an LPS factual value;
the committed Purpose file establishes the LFS Purpose set and its reviewed
formation context. Monthly-plan commitment is not folded into the immediate
TARGET capital: it is a forward funding commitment outside the economic
CURRENT -> TARGET capital boundary.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from lts.models import FormationIntentRow, TargetFormation


PURPOSE_FIELDS = {"name", "due", "desired", "monthly_plan"}
POSITION_FIELDS = {
    "investor",
    "folio",
    "isin",
    "units",
    "nav",
    "market_value",
    "purpose",
}
SUMMARY_FIELDS = {"purpose", "primary_winner"}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _purpose_capital(positions_path: Path) -> dict[str, Decimal]:
    rows = _read_csv(positions_path)
    if not rows or set(rows[0]) != POSITION_FIELDS:
        raise ValueError(f"Positions file has an unexpected column layout: {positions_path}")

    result: dict[str, Decimal] = {}
    for row in rows:
        purpose = row["purpose"].strip()
        if not purpose:
            continue
        raw = row["market_value"].strip()
        if not raw:
            raise ValueError(
                f"Position assigned to Purpose {purpose!r} has no market value: "
                f"{row['investor']}/{row['folio']}/{row['isin']}"
            )
        value = Decimal(raw)
        if not value.is_finite() or value < 0:
            raise ValueError(f"Invalid market value for Position: {row}")
        result[purpose] = result.get(purpose, Decimal("0")) + value
    return result


def _purpose_state(purposes_path: Path) -> dict[str, dict[str, str]]:
    rows = _read_csv(purposes_path)
    if not rows or set(rows[0]) != PURPOSE_FIELDS:
        raise ValueError(f"Purpose source has an unexpected column layout: {purposes_path}")

    result: dict[str, dict[str, str]] = {}
    for row in rows:
        name = row["name"].strip()
        if not name or name in result:
            raise ValueError(f"Blank or duplicate Purpose: {name!r}")
        result[name] = row
    return result


def _selected_compositions(summary_path: Path) -> dict[str, str]:
    rows = _read_csv(summary_path)
    if not rows or not SUMMARY_FIELDS.issubset(rows[0]):
        raise ValueError(f"FINAL Purpose summary has an unexpected column layout: {summary_path}")

    result: dict[str, str] = {}
    for row in rows:
        purpose = row["purpose"].strip()
        winner = row["primary_winner"].strip()
        if not purpose or not winner or purpose in result:
            raise ValueError(f"Invalid or duplicate FINAL Purpose summary row: {row}")
        result[purpose] = winner
    return result


def _weights_from_identity(identity: str) -> dict[str, Decimal]:
    try:
        _members, weights_raw = identity.split("|", 1)
    except ValueError as exc:
        raise ValueError(f"Invalid Composition identity: {identity!r}") from exc

    weights: dict[str, Decimal] = {}
    for token in weights_raw.split(","):
        try:
            isin, raw_weight = token.split("=", 1)
        except ValueError as exc:
            raise ValueError(f"Invalid Composition weight token: {token!r}") from exc
        isin = isin.strip()
        if not isin or isin in weights:
            raise ValueError(f"Invalid Composition weights: {identity!r}")
        weight = Decimal(raw_weight)
        if not weight.is_finite() or weight < 0:
            raise ValueError(f"Invalid Composition weight: {token!r}")
        weights[isin] = weight

    if not weights:
        raise ValueError(f"Composition identity has no weights: {identity!r}")
    return weights


def build_formation_intent(
    *,
    purposes_path: Path,
    positions_path: Path,
    purpose_summaries_path: Path,
) -> TargetFormation:
    """Build Formation Intent without re-solving FINAL.

    Capital is the factual Purpose capital observed by LPS at the transition
    boundary. The committed Purpose file supplies the reviewed LFS Purpose set;
    FINAL summaries supply the already-selected Composition for each Purpose.
    """

    purposes = _purpose_state(purposes_path)
    capital = _purpose_capital(positions_path)
    winners = _selected_compositions(purpose_summaries_path)

    if set(winners) != set(purposes):
        missing = sorted(set(purposes) - set(winners))
        extra = sorted(set(winners) - set(purposes))
        raise ValueError(
            f"Purpose/FINAL mismatch: missing={missing}, extra={extra}"
        )

    rows: list[FormationIntentRow] = []
    for purpose in sorted(purposes):
        if purpose not in capital:
            raise ValueError(f"LPS has no valued Position capital for Purpose: {purpose}")
        for isin, weight in sorted(_weights_from_identity(winners[purpose]).items()):
            rows.append(
                FormationIntentRow(
                    purpose=purpose,
                    isin=isin,
                    target_capital=capital[purpose],
                    target_weight=weight,
                )
            )

    return TargetFormation(rows=tuple(rows))


__all__ = ["build_formation_intent"]
