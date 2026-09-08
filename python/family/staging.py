"""Human-in-the-loop Purpose staging and common-pool reconciliation.

The production Purpose source remains untouched while the reviewer iterates.
The same dated workspace is updated in place; ``working_revision`` advances
with each successful turn and never resets the underlying staged state.
Each turn applies reviewer-selected Purpose lever values, records any capital
or SIP released by lower values, then allocates the resulting pool according
to explicit acquisition percentages. Acquisition amounts are applied to the
recipient Purpose's staged value/SIP. Achievability is then recalculated using
the observed upper return already persisted for that Purpose's FINAL winner.

The module is deliberately a review-stage tool, not an optimizer and not a
replacement for FUND -> TEAM -> COMPOSITION -> MISSION -> FINAL.
"""
from __future__ import annotations

from lakshya_core.hashing import sha256_file

import argparse
import csv
import json
import logging
import os
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from mission.achievability import required_annual_return
from mission.achievability_interpretation import AchievabilityStatus
from mission.models import Purpose
from .purpose_staging_adapter import load_intent_rows

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PURPOSES_PATH = DATA_DIR / "purpose" / "purposes.csv"
SCHEMA_VERSION = 1
EPSILON = 1e-8
INTENT_FIELDS = ["name", "due", "desired", "monthly_plan"]
PURPOSE_FIELDS = ["name", "due", "value", "desired", "monthly_plan", "analytical_horizon_years"]
TURN_FIELDS = [
    "purpose", "value", "monthly_plan", "desired", "due", "analytical_horizon_years",
    "capital_acquire_pct", "sip_acquire_pct",
]
LEDGER_FIELDS = ["turn", "kind", "purpose", "amount", "pool_after"]
RESULT_FIELDS = [
    "purpose", "value", "monthly_plan", "desired", "due", "horizon_years",
    "required_annual_return", "observed_upper_return", "status",
]


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    from io import StringIO
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    _atomic_write(path, buffer.getvalue())


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _number(value: str, field: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        result = float(text)
    except ValueError as exc:
        raise ValueError(f"Invalid {field}: {value!r}") from exc
    if not result == result or result in (float("inf"), float("-inf")):
        raise ValueError(f"Non-finite {field}: {value!r}")
    return result


def _integer(value: str, field: str) -> int | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        result = int(text)
    except ValueError as exc:
        raise ValueError(f"Invalid {field}: {value!r}") from exc
    return result


def _load_staged_rows(path: Path) -> dict[str, dict[str, str]]:
    rows = _read_csv(path)
    if not rows or set(rows[0]) != set(PURPOSE_FIELDS):
        raise ValueError(f"Staged Purpose file has an unexpected column layout: {path}")
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        name = row["name"].strip()
        if not name or name in result:
            raise ValueError(f"Blank or duplicate Purpose: {name!r}")
        value = _number(row["value"], "value")
        if value is None or value < 0:
            raise ValueError(f"Purpose value must be finite and non-negative: {name}")
        result[name] = {field: row.get(field, "") for field in PURPOSE_FIELDS}
    return result


def _purpose(row: dict[str, str], as_of: date) -> Purpose:
    value = _number(row["value"], "value")
    assert value is not None
    desired = _number(row.get("desired", ""), "desired")
    monthly = _number(row.get("monthly_plan", ""), "monthly_plan")
    if desired is not None and desired < 0:
        raise ValueError(f"Negative desired target: {row['name']}")
    if monthly is not None and monthly < 0:
        raise ValueError(f"Negative monthly plan: {row['name']}")
    due_raw = row.get("due", "").strip()
    if due_raw and due_raw.upper() != "NA":
        due = date.fromisoformat(due_raw)
        years = due.year - as_of.year
        anniversary = date(as_of.year + years, due.month, due.day)
        if anniversary > due:
            years -= 1
        if years <= 0:
            raise ValueError(f"Purpose due date is not beyond as-of date: {row['name']}")
        return Purpose(
            name=row["name"],
            due=due,
            capital=value,
            desired_target=desired,
            monthly_contribution=monthly,
            horizon_years=years,
        )
    return Purpose(
        name=row["name"],
        capital=value,
        desired_target=None,
        monthly_contribution=None,
        horizon_years=None,
    )


def _directory(data_dir: Path, as_of: str) -> Path:
    return data_dir / "reviews" / as_of / "purpose_staging"


def initialize_staging(as_of: str, *, data_dir: Path = DATA_DIR) -> Path:
    date.fromisoformat(as_of)
    source = data_dir / "purpose" / "purposes.csv"
    positions_path = data_dir / "lps" / "positions.csv"
    rows = load_intent_rows(source, positions_path)
    directory = _directory(data_dir, as_of)
    directory.mkdir(parents=True, exist_ok=True)
    _write_csv(directory / "purposes_staged.csv", PURPOSE_FIELDS, list(rows.values()))
    _write_csv(directory / "reconciliation_ledger.csv", LEDGER_FIELDS, [])
    _write_csv(directory / "achievability_latest.csv", RESULT_FIELDS, [])
    state = {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "source_purposes_sha256": sha256_file(source),
        "turn": 0,
        "working_revision": 0,
        "pool_capital": 0.0,
        "pool_monthly_sip": 0.0,
        "status": "STAGING",
    }
    _atomic_write(directory / "staging_state.json", json.dumps(state, indent=2, sort_keys=True) + "\n")
    _atomic_write(directory / "staging.log", f"START as_of={as_of} source={source}\n")
    return directory


def _state(directory: Path) -> dict[str, Any]:
    path = directory / "staging_state.json"
    if not path.is_file():
        raise FileNotFoundError(f"Staging state missing; initialize first: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _logger(path: Path) -> logging.Logger:
    logger = logging.getLogger(f"lakshya.family.staging.{path}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def _acquisition_percentages(rows: list[dict[str, str]]) -> tuple[float, float]:
    capital = 0.0
    sip = 0.0
    for row in rows:
        for field in ("capital_acquire_pct", "sip_acquire_pct"):
            value = _number(row.get(field, ""), field)
            if value is None:
                continue
            if not 0.0 <= value <= 100.0:
                raise ValueError(f"{field} must be between 0 and 100: {row['purpose']}")
            if field == "capital_acquire_pct":
                capital += value
            else:
                sip += value
    if capital > 100.0 + EPSILON or sip > 100.0 + EPSILON:
        raise ValueError("Acquisition percentages cannot exceed 100%")
    return capital, sip


def _apply_levers(staged: dict[str, dict[str, str]], rows: list[dict[str, str]], turn: int, logger: logging.Logger) -> dict[str, dict[str, str]]:
    names = [row["purpose"].strip() for row in rows]
    if len(names) != len(set(names)):
        raise ValueError("Turn input contains duplicate Purposes")
    unknown = set(names) - set(staged)
    if unknown:
        raise ValueError(f"Turn references unknown Purposes: {sorted(unknown)}")
    updated = {name: dict(row) for name, row in staged.items()}
    for change in rows:
        name = change["purpose"].strip()
        current = updated[name]
        for field in ("value", "monthly_plan", "desired", "due", "analytical_horizon_years"):
            proposed = change.get(field, "").strip()
            if not proposed:
                continue
            if field in ("value", "monthly_plan", "desired"):
                number = _number(proposed, field)
                assert number is not None
                if number < 0:
                    raise ValueError(f"Negative {field} for {name}")
                current[field] = f"{number:g}"
                logger.info("TURN=%s LEVER purpose=%s field=%s value=%s", turn, name, field, number)
            elif field == "analytical_horizon_years":
                horizon = _integer(proposed, field)
                if horizon is None or horizon <= 0:
                    raise ValueError(f"{field} must be positive for {name}")
                current[field] = str(horizon)
                logger.info("TURN=%s LEVER purpose=%s field=%s value=%s", turn, name, field, horizon)
            else:
                current[field] = proposed
                logger.info("TURN=%s LEVER purpose=%s field=%s value=%s", turn, name, field, proposed)
    return updated


def _release_deltas(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]], turn: int, logger: logging.Logger, pool_capital: float, pool_sip: float, ledger: list[dict[str, Any]]) -> tuple[float, float]:
    for name in sorted(before):
        old_value = _number(before[name]["value"], "value") or 0.0
        new_value = _number(after[name]["value"], "value") or 0.0
        delta = old_value - new_value
        if delta > EPSILON:
            pool_capital += delta
            ledger.append({"turn": turn, "kind": "RELEASE_CAPITAL", "purpose": name, "amount": f"{delta:.2f}", "pool_after": f"{pool_capital:.2f}"})
            logger.info("TURN=%s RELEASE_CAPITAL purpose=%s amount=%.2f pool=%.2f", turn, name, delta, pool_capital)
        elif delta < -EPSILON:
            raise ValueError(f"Purpose {name} increased value by {-delta:.2f}; fund increases through pool percentages, not silent money creation")
        old_sip = _number(before[name]["monthly_plan"], "monthly_plan") or 0.0
        new_sip = _number(after[name]["monthly_plan"], "monthly_plan") or 0.0
        delta_sip = old_sip - new_sip
        if delta_sip > EPSILON:
            pool_sip += delta_sip
            ledger.append({"turn": turn, "kind": "RELEASE_SIP", "purpose": name, "amount": f"{delta_sip:.2f}", "pool_after": f"{pool_sip:.2f}"})
            logger.info("TURN=%s RELEASE_SIP purpose=%s amount=%.2f pool=%.2f", turn, name, delta_sip, pool_sip)
        elif delta_sip < -EPSILON:
            raise ValueError(f"Purpose {name} increased monthly_plan by {-delta_sip:.2f}; fund increases through pool percentages, not silent SIP creation")
    return pool_capital, pool_sip


def _apply_acquisitions(staged: dict[str, dict[str, str]], rows: list[dict[str, str]], turn: int, pool_capital: float, pool_sip: float, ledger: list[dict[str, Any]], logger: logging.Logger) -> tuple[float, float]:
    capital_pct, sip_pct = _acquisition_percentages(rows)
    base_capital = pool_capital
    base_sip = pool_sip
    acquired_capital = 0.0
    acquired_sip = 0.0
    for row in rows:
        name = row["purpose"].strip()
        cp = _number(row.get("capital_acquire_pct", ""), "capital_acquire_pct") or 0.0
        if cp:
            amount = base_capital * cp / 100.0
            acquired_capital += amount
            staged[name]["value"] = f"{(_number(staged[name]['value'], 'value') or 0.0) + amount:g}"
            ledger.append({"turn": turn, "kind": "ACQUIRE_CAPITAL", "purpose": name, "amount": f"{amount:.2f}", "pool_after": f"{base_capital - acquired_capital:.2f}"})
            logger.info("TURN=%s ACQUIRE_CAPITAL purpose=%s pct=%.4f amount=%.2f pool=%.2f", turn, name, cp, amount, base_capital - acquired_capital)
        sp = _number(row.get("sip_acquire_pct", ""), "sip_acquire_pct") or 0.0
        if sp:
            amount = base_sip * sp / 100.0
            acquired_sip += amount
            staged[name]["monthly_plan"] = f"{(_number(staged[name]['monthly_plan'], 'monthly_plan') or 0.0) + amount:g}"
            ledger.append({"turn": turn, "kind": "ACQUIRE_SIP", "purpose": name, "amount": f"{amount:.2f}", "pool_after": f"{base_sip - acquired_sip:.2f}"})
            logger.info("TURN=%s ACQUIRE_SIP purpose=%s pct=%.4f amount=%.2f pool=%.2f", turn, name, sp, amount, base_sip - acquired_sip)
    pool_capital = base_capital - base_capital * capital_pct / 100.0
    pool_sip = base_sip - base_sip * sip_pct / 100.0
    return pool_capital, pool_sip


def _observed_upper_returns(data_dir: Path, as_of: str) -> dict[str, float]:
    review_dir = data_dir / "reviews" / as_of
    output_dir = data_dir.parent / "output"
    result: dict[str, float] = {}
    for summary in sorted(review_dir.glob("*_summary.csv")):
        rows = _read_csv(summary)
        if len(rows) != 1:
            continue
        purpose = rows[0].get("purpose", "")
        winner = rows[0].get("primary_winner", "")
        if not purpose or not winner:
            continue
        checkpoint = output_dir / f"achievability_{purpose}.csv"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Achievability checkpoint missing: {checkpoint}")
        matches = [row for row in _read_csv(checkpoint) if row.get("composition") == winner]
        if len(matches) != 1 or not matches[0].get("observed_upper_return"):
            raise ValueError(f"Cannot recover observed upper return for {purpose}")
        result[purpose] = float(matches[0]["observed_upper_return"])
    return result


def run_turn(as_of: str, turn_path: Path, *, data_dir: Path = DATA_DIR) -> Path:
    date.fromisoformat(as_of)
    directory = _directory(data_dir, as_of)
    state = _state(directory)
    if state.get("status") != "STAGING":
        raise ValueError("Staging workspace is already committed")
    rows = _read_csv(turn_path)
    if not rows or not set(TURN_FIELDS).issubset(rows[0]):
        raise ValueError(f"Turn input is missing required columns: {turn_path}")
    staged_path = directory / "purposes_staged.csv"
    before = _load_staged_rows(staged_path)
    logger = _logger(directory / "staging.log")
    turn = int(state["turn"]) + 1
    logger.info("TURN_START turn=%s input=%s", turn, turn_path)
    after = _apply_levers(before, rows, turn, logger)
    ledger = _read_csv(directory / "reconciliation_ledger.csv")
    pool_capital, pool_sip = _release_deltas(before, after, turn, logger, float(state["pool_capital"]), float(state["pool_monthly_sip"]), ledger)
    pool_capital, pool_sip = _apply_acquisitions(after, rows, turn, pool_capital, pool_sip, ledger, logger)
    _write_csv(staged_path, PURPOSE_FIELDS, list(after.values()))
    _write_csv(directory / "reconciliation_ledger.csv", LEDGER_FIELDS, ledger)

    observed = _observed_upper_returns(data_dir, as_of)
    results: list[dict[str, Any]] = []
    for name, row in after.items():
        purpose = _purpose(row, date.fromisoformat(as_of))
        required = required_annual_return(purpose)
        upper = observed.get(name)
        if required is None:
            status = AchievabilityStatus.NOT_APPLICABLE.value
        elif upper is None:
            status = AchievabilityStatus.INSUFFICIENT_EVIDENCE.value
        else:
            status = (AchievabilityStatus.WITHIN_OBSERVED_TERRAIN.value if required <= upper else AchievabilityStatus.BEYOND_OBSERVED_TERRAIN.value)
        results.append({
            "purpose": name,
            "value": row["value"],
            "monthly_plan": row["monthly_plan"],
            "desired": row["desired"],
            "due": row["due"],
            "horizon_years": purpose.horizon_years or purpose.trajectory_horizon_years or "",
            "required_annual_return": "" if required is None else f"{required:.10f}",
            "observed_upper_return": "" if upper is None else f"{upper:.10f}",
            "status": status,
        })
    _write_csv(directory / "achievability_latest.csv", RESULT_FIELDS, results)
    state.update({"turn": turn, "working_revision": turn, "pool_capital": pool_capital, "pool_monthly_sip": pool_sip, "last_turn_input_sha256": sha256_file(turn_path)})
    _atomic_write(directory / "staging_state.json", json.dumps(state, indent=2, sort_keys=True) + "\n")
    logger.info("TURN_COMPLETE turn=%s pool_capital=%.2f pool_monthly_sip=%.2f", turn, pool_capital, pool_sip)
    return directory


def commit_staging(as_of: str, *, data_dir: Path = DATA_DIR) -> Path:
    date.fromisoformat(as_of)
    directory = _directory(data_dir, as_of)
    state = _state(directory)
    if state.get("status") != "STAGING":
        raise ValueError("Staging workspace is not committable")
    if abs(float(state["pool_capital"])) > EPSILON or abs(float(state["pool_monthly_sip"])) > EPSILON:
        raise ValueError("Cannot commit while common-pool balances remain")
    authoritative = data_dir / "purpose" / "purposes.csv"
    staged = directory / "purposes_staged.csv"
    backup = directory / "purposes_before_commit.csv"
    shutil.copy2(authoritative, backup)
    staged_rows = _load_staged_rows(staged)
    intent_rows = [
        {
            "name": row["name"],
            "due": row["due"],
            "desired": row["desired"],
            "monthly_plan": row["monthly_plan"],
        }
        for row in staged_rows.values()
    ]
    _write_csv(authoritative, INTENT_FIELDS, intent_rows)
    state["status"] = "COMMITTED"
    state["committed_working_revision"] = state["working_revision"]
    state["committed_source_sha256"] = sha256_file(authoritative)
    _atomic_write(directory / "staging_state.json", json.dumps(state, indent=2, sort_keys=True) + "\n")
    with (directory / "staging.log").open("a", encoding="utf-8") as handle:
        handle.write(f"COMMIT as_of={as_of} source={authoritative}\n")
    return authoritative


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("--as-of", required=True)
    p = sub.add_parser("turn")
    p.add_argument("--as-of", required=True)
    p.add_argument("--input", required=True, type=Path)
    p = sub.add_parser("commit")
    p.add_argument("--as-of", required=True)
    args = parser.parse_args()
    if args.command == "init":
        print(initialize_staging(args.as_of))
    elif args.command == "turn":
        print(run_turn(args.as_of, args.input))
    else:
        print(commit_staging(args.as_of))


if __name__ == "__main__":
    main()
