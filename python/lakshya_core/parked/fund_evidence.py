from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd

from lakshya_core.parked.evidence_inventory import load_nav_cache


@dataclass(frozen=True)
class MaximumDrawdownEvidence:
    maximum_drawdown: float
    peak_date: date
    trough_date: date
    recovery_date: Optional[date]
    decline_days: int
    recovery_days: Optional[int]
    underwater_days: Optional[int]


@dataclass(frozen=True)
class FundReturnEvidence:
    total_return: float
    annualized_return: float
    first_date: date
    last_date: date
    observations: int


@dataclass(frozen=True)
class FundEvidence:
    isin: str
    returns: FundReturnEvidence
    drawdown: MaximumDrawdownEvidence


def calculate_return_evidence(df: pd.DataFrame) -> FundReturnEvidence:
    """Calculate simple historical return evidence."""

    df = df.sort_values("date").copy()

    first_date = df["date"].iloc[0]
    last_date = df["date"].iloc[-1]

    first_nav = float(df["nav"].iloc[0])
    last_nav = float(df["nav"].iloc[-1])

    total_return = (last_nav / first_nav) - 1

    days = (last_date - first_date).days

    if days <= 0:
        annualized_return = float("nan")
    else:
        years = days / 365.25
        annualized_return = (last_nav / first_nav) ** (1 / years) - 1

    return FundReturnEvidence(
        total_return=total_return,
        annualized_return=annualized_return,
        first_date=first_date.date(),
        last_date=last_date.date(),
        observations=len(df),
    )


def calculate_drawdown_evidence(df: pd.DataFrame) -> MaximumDrawdownEvidence:
    """Calculate maximum drawdown and its recovery characteristics."""

    df = df.sort_values("date").copy()

    running_peak = df["nav"].cummax()
    drawdown = df["nav"] / running_peak - 1

    trough_idx = drawdown.idxmin()

    maximum_drawdown = float(drawdown.loc[trough_idx])

    peak_before_trough = running_peak.loc[trough_idx]
    peak_idx = df.loc[:trough_idx, "nav"].idxmax()

    peak_date = df.loc[peak_idx, "date"]
    trough_date = df.loc[trough_idx, "date"]

    recovery_date = None

    post_trough = df.loc[trough_idx:]

    recovered = post_trough[
        post_trough["nav"] >= peak_before_trough
    ]

    if not recovered.empty:
        recovery_date = recovered.iloc[0]["date"]

    decline_days = (trough_date - peak_date).days

    recovery_days = None
    underwater_days = None

    if recovery_date is not None:
        recovery_days = (recovery_date - trough_date).days
        underwater_days = (recovery_date - peak_date).days

    return MaximumDrawdownEvidence(
        maximum_drawdown=maximum_drawdown,
        peak_date=peak_date.date(),
        trough_date=trough_date.date(),
        recovery_date=(
            recovery_date.date()
            if recovery_date is not None
            else None
        ),
        decline_days=decline_days,
        recovery_days=recovery_days,
        underwater_days=underwater_days,
    )


def calculate_fund_evidence(isin: str) -> FundEvidence:
    """Build the first fund-level Lakshya evidence record."""

    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    cache_path = (
        project_root
        / "data"
        / "cache"
        / f"{isin}_nav.json"
    )

    df = load_nav_cache(cache_path)

    if df.empty:
        raise ValueError(f"No NAV data available for {isin}")

    return FundEvidence(
        isin=isin,
        returns=calculate_return_evidence(df),
        drawdown=calculate_drawdown_evidence(df),
    )
