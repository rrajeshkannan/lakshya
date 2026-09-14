"""Input-boundary helpers for the resilient Lakshya pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from lakshya_core.nav_history import cutoff_nav_history

from .models import Purpose

Log = Callable[[str], None]


def load_fund_histories(
    funds: Iterable[object],
    *,
    nav_dir: Path,
    as_of: pd.Timestamp,
    log: Log | None = None,
    detail: Log | None = None,
) -> dict[str, pd.DataFrame]:
    """Load one persisted NAV JSON document per fund through ``as_of``.

    This helper owns only the NAV input boundary. It deliberately does not
    know about manifests, checkpoints, workers, or downstream pipeline stages.
    Each fund is expected to expose an ``isin`` attribute, and each JSON file
    is expected to contain an ``observations`` list.
    """
    funds = list(funds)
    histories: dict[str, pd.DataFrame] = {}
    if log is not None:
        log(f"Loading NAV histories for {len(funds)} admitted funds through {as_of.date()}")
    if detail is not None:
        detail(f"NAV_LOAD_START funds={len(funds)} as_of={as_of.date()}")

    for index, fund in enumerate(funds, start=1):
        isin = str(fund.isin)
        path = nav_dir / f"{isin}.json"
        if log is not None:
            log(f"  NAV {index}/{len(funds)}: {isin}")
        if detail is not None:
            detail(
                f"NAV_LOAD_START index={index} total={len(funds)} "
                f"isin={isin} path={path} as_of={as_of.date()}"
            )
        if not path.exists():
            if detail is not None:
                detail(f"NAV_LOAD_FAILED isin={isin} reason=missing_file path={path}")
            raise FileNotFoundError(f"Missing NAV evidence for {isin}: {path}")

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        observations = payload.get("observations")
        if not isinstance(observations, list):
            if detail is not None:
                detail(f"NAV_LOAD_FAILED isin={isin} reason=invalid_observations")
            raise ValueError(f"Invalid NAV evidence observations: {path}")

        histories[isin] = cutoff_nav_history(pd.DataFrame(observations), as_of)
        if detail is not None:
            detail(f"NAV_READY isin={isin} rows={len(histories[isin])} as_of={as_of.date()}")

    if detail is not None:
        detail(f"NAV_LOAD_COMPLETE funds={len(histories)} as_of={as_of.date()}")
    return histories


def load_purposes(
    purposes_path: Path,
    *,
    as_of: pd.Timestamp,
    floor_years: Callable[[pd.Timestamp, pd.Timestamp], int],
    log: Log | None = None,
    detail: Log | None = None,
) -> list[Purpose]:
    """Load and validate purpose inputs without applying purpose selection.

    The caller supplies the date-relative year-flooring rule so this boundary
    does not own orchestration policy or duplicate that calculation.
    """
    df = pd.read_csv(purposes_path, keep_default_na=False)
    required = {"name", "due", "value", "desired", "monthly_plan", "analytical_horizon_years"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Purpose input is missing required columns: {sorted(missing)}")

    purposes: list[Purpose] = []
    for row in df.to_dict("records"):
        name = str(row["name"])
        due_raw = str(row["due"]).strip()
        analytical_raw = str(row["analytical_horizon_years"]).strip()
        analytical_horizon = int(analytical_raw) if analytical_raw else None
        if due_raw.upper() == "NA" or not due_raw:
            if analytical_horizon is None:
                raise ValueError(f"Purpose without a finite due date requires analytical_horizon_years: {name}")
            purposes.append(
                Purpose(
                    name=name,
                    capital=float(row["value"]),
                    horizon_years=analytical_horizon,
                )
            )
            continue

        due = pd.Timestamp(due_raw)
        horizon = floor_years(as_of, due)
        if horizon <= 0:
            raise ValueError(f"Purpose due date is not beyond as-of date: {name}")
        purposes.append(
            Purpose(
                name=name,
                capital=float(row["value"]),
                desired_target=float(row["desired"]),
                horizon_years=horizon,
                monthly_contribution=float(row["monthly_plan"]),
            )
        )

    if log is not None:
        log("Loaded purposes: " + ", ".join(f"{p.name}={p.trajectory_horizon_years}Y" for p in purposes))
    if detail is not None:
        detail(
            "PURPOSES_READY "
            + " ".join(
                f"name={p.name} horizon={p.trajectory_horizon_years}Y achievability={p.has_achievability}"
                for p in purposes
            )
        )
    return purposes
