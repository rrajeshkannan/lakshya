"""Local experimental runner for the surviving-Composition trajectory study.

This module is orchestration only. It reconstructs the existing FUND -> TEAM
-> COMPOSITION -> MISSION path from persisted inputs, then hands the surviving
Compositions to the descriptive trajectory experiment.

Generated intermediate evidence is intentionally written under ``output/``
and is not part of the Lakshya decision architecture.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from fund_analysis.admissible_funds import load_admissible_funds
from lakshya_core.nav_history import normalize_nav_history
from team_analysis.composition_pipeline import stream_composition_fingerprints
from team_analysis.composition_frontier import global_composition_frontier
from team_analysis.composition import Composition
from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.protection_frontier import protection_frontier
from team_analysis.run_team_pipeline import run_team_pipeline

from .achievability_interpretation import (
    AchievabilityStatus,
    assess_achievability,
)
from .models import Purpose
from .survivor_trajectory_experiment import observe_survivors_for_purpose

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NAV_DIR = PROJECT_ROOT / "data" / "nav"
PURPOSES_PATH = PROJECT_ROOT / "data" / "purpose" / "purposes.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"


def _log(message: str) -> None:
    """Emit a flushed progress marker for this deliberately transparent runner."""
    print(f"[trajectory-runner] {message}", flush=True)


def _load_fund_histories(funds) -> dict[str, pd.DataFrame]:
    """Load and canonically normalize persisted NAV evidence for each Fund."""
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
    """Return completed calendar years from ``start`` to ``due``."""
    years = due.year - start.year
    anniversary = start + pd.DateOffset(years=years)
    if anniversary > due:
        years -= 1
    return years


def _load_purposes(as_of: pd.Timestamp) -> list[Purpose]:
    """Load family Purpose inputs and derive finite horizons from due dates."""
    df = pd.read_csv(PURPOSES_PATH, keep_default_na=False)
    required = {"name", "due", "value", "desired", "monthly_plan"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Purpose input is missing required columns: {sorted(missing)}")

    purposes: list[Purpose] = []
    for row in df.to_dict("records"):
        due_raw = str(row["due"]).strip()
        if due_raw.upper() == "NA" or not due_raw:
            purposes.append(
                Purpose(
                    name=str(row["name"]),
                    current_capital=float(row["value"]),
                )
            )
            continue

        due = pd.Timestamp(due_raw)
        horizon = _floor_years(as_of, due)
        if horizon <= 0:
            raise ValueError(f"Purpose due date is not beyond as-of date: {row['name']}")

        purposes.append(
            Purpose(
                name=str(row["name"]),
                current_capital=float(row["value"]),
                desired_target=float(row["desired"]),
                horizon_years=horizon,
                monthly_contribution=float(row["monthly_plan"]),
            )
        )
    _log(
        "Loaded purposes: "
        + ", ".join(
            f"{purpose.name}={purpose.horizon_years}Y"
            for purpose in purposes
        )
    )
    return purposes


def _composition_key(composition: Composition) -> str:
    members = ",".join(sorted(composition.weights))
    weights = ",".join(
        f"{isin}={composition.weights[isin]:.4f}"
        for isin in sorted(composition.weights)
    )
    return f"{members}|{weights}"


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    _log(f"  wrote {path.relative_to(PROJECT_ROOT)} ({len(rows)} rows)")


def run(as_of: str) -> None:
    """Run the complete experimental reconstruction and persist checkpoints."""
    valuation_date = pd.Timestamp(as_of)
    output = OUTPUT_DIR
    trajectory_output = output / "trajectory_observations"
    output.mkdir(parents=True, exist_ok=True)

    _log(f"START as-of {valuation_date.date()}")

    _log("[1/7] Loading admitted funds")
    funds = load_admissible_funds()
    _log(f"  admitted funds: {len(funds)}")

    _log("[2/7] Loading persisted NAV evidence")
    fund_histories = _load_fund_histories(funds)

    _log("[3/7] Loading Purpose inputs")
    purposes = _load_purposes(valuation_date)

    _log("[4/7] Running TEAM pipeline — this may be computationally heavy")
    teams = run_team_pipeline(funds=funds, fund_histories=fund_histories)
    _log(f"  TEAM survivors: {len(teams)}")
    _write_rows(
        output / "team_survivors.csv",
        [
            {
                "team": "|".join(member.isin for member in team.members),
                "members": len(team.members),
            }
            for team in teams
        ],
    )

    _log("[5/7] Generating Composition fingerprints")
    candidates = list(stream_composition_fingerprints(teams, fund_histories))
    _log(f"  Composition candidates: {len(candidates)}")
    _write_rows(
        output / "composition_candidates.csv",
        [
            {
                "composition": _composition_key(composition),
                "team": "|".join(member.isin for member in composition.team.members),
            }
            for composition, _ in candidates
        ],
    )

    fingerprints = {
        _composition_key(composition): fingerprint
        for composition, fingerprint in candidates
    }

    _log("[6/7] Applying existing MISSION gates")
    global_survivors = global_composition_frontier(candidates)
    _log(f"  global Composition frontier: {len(global_survivors)}")
    global_pairs = [
        (composition, fingerprints[_composition_key(composition)])
        for composition in global_survivors
    ]
    _write_rows(
        output / "global_survivors.csv",
        [{"composition": _composition_key(composition)} for composition in global_survivors],
    )

    for purpose in purposes:
        if purpose.horizon_years is None:
            _log(f"  {purpose.name}: no finite horizon; skipping MISSION trajectory")
            continue

        _log(f"  {purpose.name}: assessing {len(global_pairs)} global survivors")
        achievability_survivors: list[tuple[Composition, CompositionFingerprint]] = []
        assessments: list[dict] = []
        for composition, fingerprint in global_pairs:
            assessment = assess_achievability(purpose, fingerprint)
            assessments.append(
                {
                    "composition": _composition_key(composition),
                    "status": assessment.status.value,
                    "required_annual_return": assessment.required_annual_return,
                    "comparison_horizon_years": assessment.comparison_horizon_years,
                    "observed_upper_return": assessment.observed_upper_return,
                }
            )
            if assessment.status == AchievabilityStatus.WITHIN_OBSERVED_TERRAIN:
                achievability_survivors.append((composition, fingerprint))

        _write_rows(output / f"achievability_{purpose.name}.csv", assessments)
        _log(f"  {purpose.name}: achievability survivors: {len(achievability_survivors)}")

        protected = protection_frontier(achievability_survivors)
        _log(f"  {purpose.name}: protection survivors: {len(protected)}")
        protected_pairs = [
            (composition, fingerprints[_composition_key(composition)])
            for composition in protected
        ]
        _write_rows(
            output / f"mission_survivors_{purpose.name}.csv",
            [{"composition": _composition_key(composition)} for composition in protected],
        )

        _log(f"  {purpose.name}: observing trajectories")
        observations = observe_survivors_for_purpose(
            protected_pairs,
            purpose.horizon_years,
        )
        trajectory_rows: list[dict] = []
        for composition in protected:
            observation = observations[_composition_key(composition)]
            for point in observation.points:
                trajectory_rows.append(
                    {
                        "composition": _composition_key(composition),
                        "horizon_years": observation.horizon_years,
                        "date": point.date.strftime("%Y-%m-%d"),
                        "elapsed_days": point.elapsed_days,
                        "nav": point.nav,
                        "normalized_nav": point.normalized_nav,
                    }
                )
        _write_rows(trajectory_output / f"{purpose.name}.csv", trajectory_rows)

    _write_rows(
        output / "pipeline_summary.csv",
        [
            {"stage": "admissible_funds", "count": len(funds)},
            {"stage": "team_frontier", "count": len(teams)},
            {"stage": "composition_candidates", "count": len(candidates)},
            {"stage": "global_composition_frontier", "count": len(global_survivors)},
        ],
    )
    _log("DONE")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        required=True,
        help="Purpose valuation date, e.g. 2026-08-31",
    )
    args = parser.parse_args()
    run(args.as_of)


if __name__ == "__main__":
    main()
