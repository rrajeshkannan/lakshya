"""Purpose-facing observation of Composite-NAV trajectory behaviour.

This module is experimental and descriptive only. It does not rank, prune,
or interpret a Composition. It preserves the observed path so a later
MISSION experiment can test whether path behaviour adds information beyond
horizon-level outcome evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TrajectoryPoint:
    """One observed point on a Composite-NAV trajectory."""

    date: pd.Timestamp
    elapsed_days: int
    nav: float
    normalized_nav: float


@dataclass(frozen=True)
class TrajectoryObservation:
    """Observed Composite-NAV path for one requested elapsed-time horizon."""

    horizon_years: int
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    points: tuple[TrajectoryPoint, ...]


def observe_trajectory(nav: pd.DataFrame, years: int) -> TrajectoryObservation:
    """Preserve a trailing Composite-NAV path using the rolling-time convention.

    The starting point is the latest observed NAV on or before the requested
    lookback date, matching the existing rolling-CAGR convention. The full
    observed path between that start and the latest observation is preserved.
    No CAGR, smoothing, scoring, pruning, or path-shape judgement is made.
    """
    if years <= 0:
        raise ValueError("Trajectory horizon must be positive.")

    if set(nav.columns) != {"date", "nav"}:
        raise ValueError("NAV trajectory must contain exactly 'date' and 'nav' columns.")

    data = nav.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)

    if data.empty:
        raise ValueError("NAV trajectory cannot be empty.")
    if data["nav"].isna().any() or (data["nav"] <= 0).any():
        raise ValueError("NAV trajectory must contain positive, non-null NAV values.")

    end_date = data["date"].iloc[-1]
    target_start = end_date - pd.DateOffset(years=years)
    eligible = data.loc[data["date"] <= target_start]

    if eligible.empty:
        raise ValueError(f"Insufficient history for {years}-year trajectory observation.")

    start_date = eligible["date"].iloc[-1]
    window = data.loc[data["date"] >= start_date].copy()
    base_nav = float(window["nav"].iloc[0])

    points = tuple(
        TrajectoryPoint(
            date=row.date,
            elapsed_days=int((row.date - start_date).days),
            nav=float(row.nav),
            normalized_nav=float(row.nav) / base_nav,
        )
        for row in window.itertuples(index=False)
    )

    return TrajectoryObservation(
        horizon_years=years,
        start_date=start_date,
        end_date=window["date"].iloc[-1],
        points=points,
    )
