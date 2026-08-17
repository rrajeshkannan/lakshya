from pathlib import Path
import json

import pandas as pd


def load_fund_nav(isin: str, project_root: Path) -> pd.Series:
    path = (
        project_root
        / "data"
        / "cache"
        / f"{isin}_nav.json"
    )

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    df = pd.DataFrame(payload["data"])

    df["date"] = pd.to_datetime(
        df["date"],
        format="%d-%m-%Y",
        errors="raise",
    )

    df["nav"] = pd.to_numeric(
        df["nav"],
        errors="raise",
    )

    df = df.sort_values("date")

    return pd.Series(
        df["nav"].values,
        index=df["date"],
        name=isin,
    )


def calculate_drawdown_severity(
    nav: pd.Series,
) -> dict:

    nav = nav.dropna().sort_index()

    if nav.empty:
        raise ValueError("NAV series is empty.")

    running_peak = nav.cummax()

    drawdown = (
        nav / running_peak - 1.0
    )

    severity = -drawdown

    thresholds = [
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
    ]

    return {
        "observations": int(len(severity)),

        "median_severity_pct": float(
            severity.quantile(0.50) * 100
        ),

        "percentile_75_severity_pct": float(
            severity.quantile(0.75) * 100
        ),

        "percentile_90_severity_pct": float(
            severity.quantile(0.90) * 100
        ),

        "percentile_95_severity_pct": float(
            severity.quantile(0.95) * 100
        ),

        "percentile_99_severity_pct": float(
            severity.quantile(0.99) * 100
        ),

        "maximum_severity_pct": float(
            severity.max() * 100
        ),

        "days_at_or_above_threshold": {
            f"{int(threshold * 100)}": int(
                (severity >= threshold).sum()
            )
            for threshold in thresholds
        },

        "pct_days_at_or_above_threshold": {
            f"{int(threshold * 100)}": float(
                (severity >= threshold).mean() * 100
            )
            for threshold in thresholds
        },
    }


if __name__ == "__main__":

    # isin = "INF174K01KT2"
    # isin = "INF109K01BL4"
    isin = "INF179K01608"

    project_root = Path(__file__).resolve().parents[2]

    nav = load_fund_nav(
        isin,
        project_root,
    )

    evidence = calculate_drawdown_severity(nav)

    print(evidence)
