from dataclasses import dataclass

import pandas as pd

from lakshya_core.downside import calculate_downside_deviation
from lakshya_core.fund_evidence import calculate_fund_evidence


@dataclass(frozen=True)
class RatioEvidence:
    full_period_cagr: float
    risk_free_rate: float
    sortino: float
    calmar: float


def calculate_ratio_evidence(
    df: pd.DataFrame,
    risk_free_rate: float = 0.065,
) -> RatioEvidence:
    """
    Reproduce the inherited toolkit's Sortino and Calmar conventions.

    risk_free_rate is supplied explicitly rather than treated as a
    Lakshya philosophical assumption.
    """

    df = df.sort_values("date").copy()

    fund_evidence = calculate_fund_evidence_from_df(df)

    cagr = fund_evidence.annualized_return

    downside = calculate_downside_deviation(df)

    if downside.downside_rms_annualized == 0:
        sortino = float("nan")
    else:
        sortino = (
            cagr - risk_free_rate
        ) / downside.downside_rms_annualized

    if fund_evidence.drawdown.maximum_drawdown == 0:
        calmar = float("nan")
    else:
        calmar = (
            cagr
            / abs(fund_evidence.drawdown.maximum_drawdown)
        )

    return RatioEvidence(
        full_period_cagr=cagr,
        risk_free_rate=risk_free_rate,
        sortino=sortino,
        calmar=calmar,
    )


def calculate_fund_evidence_from_df(df: pd.DataFrame):
    """Calculate the existing fund evidence directly from a DataFrame."""

    from lakshya_core.fund_evidence import (
        calculate_return_evidence,
        calculate_drawdown_evidence,
    )

    return type(
        "FundEvidenceFromDataFrame",
        (),
        {
            "annualized_return": calculate_return_evidence(
                df
            ).annualized_return,
            "drawdown": calculate_drawdown_evidence(df),
        },
    )()


if __name__ == "__main__":
    from pathlib import Path
    from lakshya_core.evidence_inventory import load_nav_cache

    project_root = Path(__file__).resolve().parents[2]

    path = (
        project_root
        / "data"
        / "cache"
        / "INF174K01KT2_nav.json"
    )

    df = load_nav_cache(path)

    evidence = calculate_ratio_evidence(df)

    print(evidence)
