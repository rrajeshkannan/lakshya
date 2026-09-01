"""Experimental runner for the surviving-Composition trajectory study."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from fund_analysis.admissible_funds import load_admissible_funds
from lakshya_core.nav_history import normalize_nav_history
from team_analysis.analyze_composition import analyze_composition
from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition_frontier import global_composition_frontier
from team_analysis.composition_pipeline import stream_composition_fingerprints
from team_analysis.protection_frontier import protection_frontier
from team_analysis.run_team_pipeline import run_team_pipeline
from team_analysis.team import Team

from .achievability_interpretation import AchievabilityStatus, assess_achievability
from .models import Purpose
from .survivor_trajectory_experiment import observe_survivors_for_purpose

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NAV_DIR = PROJECT_ROOT / "data" / "nav"
PURPOSES_PATH = PROJECT_ROOT / "data" / "purpose" / "purposes.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_PATH = OUTPUT_DIR / "trajectory_pipeline.log"


def _log(message: str) -> None:
    """Write one timestamped progress line to both terminal and persistent log."""
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"{timestamp} | {message}"
    print(f"[trajectory-runner] {message}", flush=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _load_fund_histories(funds) -> dict[str, pd.DataFrame]:
    histories: dict[str, pd.DataFrame] = {}
    _log(f"Loading NAV histories for {len(funds)} admitted funds")
    for index, fund in enumerate(funds, start=1):
        path = NAV_DIR / f"{fund.isin}.json"
        _log(f"  NAV {index}/{len(funds)}: {fund.isin}")
        if not path.exists():
            raise FileNotFoundError(f"Missing NAV evidence for {fund.isin}: {path}")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        observations = payload.get("observations")
        if not isinstance(observations, list):
            raise ValueError(f"Invalid NAV evidence observations: {path}")
        histories[fund.isin] = normalize_nav_history(pd.DataFrame(observations))
    return histories


def _floor_years(start: pd.Timestamp, due: pd.Timestamp) -> int:
    years = due.year - start.year
    anniversary = start + pd.DateOffset(years=years)
    if anniversary > due:
        years -= 1
    return years


def _load_purposes(as_of: pd.Timestamp) -> list[Purpose]:
    df = pd.read_csv(PURPOSES_PATH, keep_default_na=False)
    required = {"name", "due", "value", "desired", "monthly_plan"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Purpose input is missing required columns: {sorted(missing)}")

    purposes: list[Purpose] = []
    for row in df.to_dict("records"):
        due_raw = str(row["due"]).strip()
        if due_raw.upper() == "NA" or not due_raw:
            purposes.append(Purpose(name=str(row["name"]), current_capital=float(row["value"])))
            continue
        due = pd.Timestamp(due_raw)
        horizon = _floor_years(as_of, due)
        if horizon <= 0:
            raise ValueError(f"Purpose due date is not beyond as-of date: {row['name']}")
        purposes.append(Purpose(name=str(row["name"]), current_capital=float(row["value"]), desired_target=float(row["desired"]), horizon_years=horizon, monthly_contribution=float(row["monthly_plan"])))

    _log("Loaded purposes: " + ", ".join(f"{p.name}={p.horizon_years}Y" for p in purposes))
    return purposes


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    _log(f"  wrote {path.relative_to(PROJECT_ROOT)} ({len(rows)} rows)")


def _composition_from_identity(identity: str, funds_by_isin) -> Composition:
    try:
        members_raw, weights_raw = identity.split("|", 1)
    except ValueError as exc:
        raise ValueError(f"Invalid Composition identity: {identity}") from exc
    member_isins = [value for value in members_raw.split(",") if value]
    weights: dict[str, float] = {}
    for token in weights_raw.split(","):
        isin, value = token.split("=", 1)
        weights[isin] = float(value)
    if set(member_isins) != set(weights):
        raise ValueError(f"Composition identity has inconsistent members/weights: {identity}")
    try:
        members = tuple(funds_by_isin[isin] for isin in sorted(member_isins))
    except KeyError as exc:
        raise ValueError(f"Composition references unknown Fund: {exc.args[0]}") from exc
    return Composition(team=Team(members=members), weights=weights)


def _reconstruct_global_survivors(funds_by_isin, fund_histories: dict[str, pd.DataFrame]) -> list[tuple[Composition, CompositionFingerprint]]:
    """Rebuild fingerprints for the persisted global Composition frontier."""
    path = OUTPUT_DIR / "global_survivors.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing global frontier checkpoint: {path}")
    df = pd.read_csv(path, keep_default_na=False)
    if "composition" not in df.columns:
        raise ValueError(f"Invalid global frontier checkpoint: {path}")
    identities = df["composition"].tolist()
    _log(f"[RESUME GLOBAL] Reconstructing {len(identities)} global survivor fingerprints")
    pairs: list[tuple[Composition, CompositionFingerprint]] = []
    started = time.perf_counter()
    for index, identity in enumerate(identities, start=1):
        composition = _composition_from_identity(identity, funds_by_isin)
        histories = {member.isin: fund_histories[member.isin] for member in composition.team.members}
        pairs.append((composition, analyze_composition(composition, histories)))
        if index == len(identities) or index % 1000 == 0:
            elapsed = time.perf_counter() - started
            rate = index / elapsed if elapsed else 0.0
            eta = max(0.0, (len(identities) - index) / rate) if rate else 0.0
            _log(f"  global reconstruction: {index}/{len(identities)} | elapsed={elapsed:.1f}s | rate={rate:.1f}/s | ETA~{eta:.0f}s")
    _log(f"[RESUME GLOBAL] Reconstruction complete | elapsed={time.perf_counter() - started:.1f}s")
    return pairs


def _observe_mission_survivors(purpose: Purpose, protected: list[Composition], fingerprints: dict[str, CompositionFingerprint]) -> None:
    """Persist descriptive trajectory observations for protected Compositions."""
    if purpose.horizon_years is None:
        _log(f"  {purpose.name}: no finite horizon; skipping trajectory")
        return
    protected_pairs = [(composition, fingerprints[composition_identity(composition)]) for composition in protected]
    _log(f"  {purpose.name}: observing trajectories for {len(protected_pairs)} survivors")
    observations = observe_survivors_for_purpose(protected_pairs, purpose.horizon_years)
    trajectory_rows: list[dict] = []
    for composition, _ in protected_pairs:
        observation = observations[composition_identity(composition)]
        for point in observation.points:
            trajectory_rows.append({"composition": composition_identity(composition), "horizon_years": observation.horizon_years, "date": point.date.strftime("%Y-%m-%d"), "elapsed_days": point.elapsed_days, "nav": point.nav, "normalized_nav": point.normalized_nav})
    _write_rows(OUTPUT_DIR / "trajectory_observations" / f"{purpose.name}.csv", trajectory_rows)


def _run_mission_for_purposes(purposes: list[Purpose], global_pairs: list[tuple[Composition, CompositionFingerprint]], *, skip_existing_checkpoints: bool) -> None:
    """Apply existing MISSION gates and observe trajectories for each Purpose."""
    fingerprints = {composition_identity(composition): fingerprint for composition, fingerprint in global_pairs}
    for purpose in purposes:
        if purpose.horizon_years is None:
            _log(f"  {purpose.name}: no finite horizon; skipping MISSION trajectory")
            continue
        mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
        if skip_existing_checkpoints and mission_path.exists():
            _log(f"  {purpose.name}: MISSION checkpoint exists; preserving it")
            continue
        _log(f"  {purpose.name}: assessing {len(global_pairs)} global survivors")
        achievability_survivors: list[tuple[Composition, CompositionFingerprint]] = []
        assessments: list[dict] = []
        for composition, fingerprint in global_pairs:
            assessment = assess_achievability(purpose, fingerprint)
            assessments.append({"composition": composition_identity(composition), "status": assessment.status.value, "required_annual_return": assessment.required_annual_return, "comparison_horizon_years": assessment.comparison_horizon_years, "observed_upper_return": assessment.observed_upper_return})
            if assessment.status == AchievabilityStatus.WITHIN_OBSERVED_TERRAIN:
                achievability_survivors.append((composition, fingerprint))
        _write_rows(OUTPUT_DIR / f"achievability_{purpose.name}.csv", assessments)
        _log(f"  {purpose.name}: achievability survivors: {len(achievability_survivors)}")
        protected = protection_frontier(achievability_survivors)
        _log(f"  {purpose.name}: protection survivors: {len(protected)}")
        _write_rows(mission_path, [{"composition": composition_identity(composition)} for composition in protected])
        _observe_mission_survivors(purpose, protected, fingerprints)


def _observe_persisted_mission_outputs(purposes: list[Purpose], funds_by_isin, fund_histories: dict[str, pd.DataFrame]) -> None:
    """Resume trajectory observation from Purpose-specific MISSION checkpoints."""
    for purpose in purposes:
        if purpose.horizon_years is None:
            _log(f"  {purpose.name}: no finite horizon; skipping trajectory")
            continue
        mission_path = OUTPUT_DIR / f"mission_survivors_{purpose.name}.csv"
        if not mission_path.exists():
            _log(f"  {purpose.name}: no persisted MISSION checkpoint; skipping")
            continue
        df = pd.read_csv(mission_path, keep_default_na=False)
        identities = df["composition"].tolist()
        _log(f"  {purpose.name}: resuming {len(identities)} MISSION survivors")
        pairs: list[tuple[Composition, CompositionFingerprint]] = []
        started = time.perf_counter()
        for index, identity in enumerate(identities, start=1):
            composition = _composition_from_identity(identity, funds_by_isin)
            histories = {member.isin: fund_histories[member.isin] for member in composition.team.members}
            pairs.append((composition, analyze_composition(composition, histories)))
            if index == len(identities) or index % 50 == 0:
                elapsed = time.perf_counter() - started
                _log(f"  {purpose.name}: reconstructed {index}/{len(identities)} fingerprints | elapsed={elapsed:.1f}s")
        observations = observe_survivors_for_purpose(pairs, purpose.horizon_years)
        rows: list[dict] = []
        for composition, _ in pairs:
            observation = observations[composition_identity(composition)]
            for point in observation.points:
                rows.append({"composition": composition_identity(composition), "horizon_years": observation.horizon_years, "date": point.date.strftime("%Y-%m-%d"), "elapsed_days": point.elapsed_days, "nav": point.nav, "normalized_nav": point.normalized_nav})
        _write_rows(OUTPUT_DIR / "trajectory_observations" / f"{purpose.name}.csv", rows)
    _log("RESUME DONE")


def run(as_of: str, resume_from: str | None = None) -> None:
    valuation_date = pd.Timestamp(as_of)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _log(f"START as-of {valuation_date.date()} mode={resume_from or 'full'}")
    if resume_from == "mission":
        _log("[RESUME] Loading admitted funds, NAV evidence and Purpose inputs")
        funds = load_admissible_funds()
        histories = _load_fund_histories(funds)
        purposes = _load_purposes(valuation_date)
        funds_by_isin = {fund.isin: fund for fund in funds}
        _observe_persisted_mission_outputs(purposes, funds_by_isin, histories)
        return
    if resume_from == "global":
        _log("[RESUME] Loading admitted funds, NAV evidence and Purpose inputs")
        funds = load_admissible_funds()
        histories = _load_fund_histories(funds)
        purposes = _load_purposes(valuation_date)
        funds_by_isin = {fund.isin: fund for fund in funds}
        global_pairs = _reconstruct_global_survivors(funds_by_isin, histories)
        _run_mission_for_purposes(purposes, global_pairs, skip_existing_checkpoints=True)
        _log("RESUME GLOBAL DONE")
        return

    _log("[1/7] Loading admitted funds")
    funds = load_admissible_funds()
    _log(f"  admitted funds: {len(funds)}")
    _log("[2/7] Loading persisted NAV evidence")
    fund_histories = _load_fund_histories(funds)
    _log("[3/7] Loading Purpose inputs")
    purposes = _load_purposes(valuation_date)
    _log("[4/7] Running TEAM pipeline — this may be computationally heavy")
    stage_started = time.perf_counter()
    teams = run_team_pipeline(funds=funds, fund_histories=fund_histories)
    _log(f"  TEAM survivors: {len(teams)} | elapsed={time.perf_counter() - stage_started:.1f}s")
    _write_rows(OUTPUT_DIR / "team_survivors.csv", [{"team": "|".join(member.isin for member in team.members), "members": len(team.members)} for team in teams])
    _log("[5/7] Generating Composition fingerprints")
    candidates: list[tuple[Composition, CompositionFingerprint]] = []
    expected_total = sum({1: 1, 2: 19, 3: 171}[team.cardinality] for team in teams)
    _log(f"  expected Composition grid size: {expected_total}")
    started = time.perf_counter()
    for index, pair in enumerate(stream_composition_fingerprints(teams, fund_histories), start=1):
        candidates.append(pair)
        if index % 1000 == 0:
            elapsed = time.perf_counter() - started
            rate = index / elapsed if elapsed else 0.0
            eta = max(0.0, (expected_total - index) / rate) if rate else 0.0
            _log(f"  Composition progress: {index} candidates | elapsed={elapsed:.1f}s | rate={rate:.1f}/s | ETA~{eta:.0f}s")
    _log(f"  Composition candidates: {len(candidates)} | elapsed={time.perf_counter() - started:.1f}s")
    _write_rows(OUTPUT_DIR / "composition_candidates.csv", [{"composition": composition_identity(composition), "team": "|".join(member.isin for member in composition.team.members)} for composition, _ in candidates])
    fingerprints = {composition_identity(composition): fingerprint for composition, fingerprint in candidates}
    _log("[6/7] Applying existing MISSION gates")
    stage_started = time.perf_counter()
    global_survivors = global_composition_frontier(candidates)
    _log(f"  global Composition frontier: {len(global_survivors)} | elapsed={time.perf_counter() - stage_started:.1f}s")
    global_pairs = [(composition, fingerprints[composition_identity(composition)]) for composition in global_survivors]
    _write_rows(OUTPUT_DIR / "global_survivors.csv", [{"composition": composition_identity(composition)} for composition in global_survivors])
    _run_mission_for_purposes(purposes, global_pairs, skip_existing_checkpoints=False)
    _write_rows(OUTPUT_DIR / "pipeline_summary.csv", [{"stage": "admissible_funds", "count": len(funds)}, {"stage": "team_frontier", "count": len(teams)}, {"stage": "composition_candidates", "count": len(candidates)}, {"stage": "global_composition_frontier", "count": len(global_survivors)}])
    _log("DONE")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="Purpose valuation date, e.g. 2026-08-31")
    parser.add_argument("--resume-from", choices=("mission", "global"), help="Resume from persisted MISSION or global frontier checkpoints")
    args = parser.parse_args()
    run(args.as_of, args.resume_from)


if __name__ == "__main__":
    main()
