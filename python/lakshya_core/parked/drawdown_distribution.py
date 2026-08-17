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


def calculate_drawdown_distribution(
    nav: pd.Series,
) -> dict:

    nav = nav.dropna().sort_index()

    if nav.empty:
        raise ValueError("NAV series is empty.")

    running_peak = nav.cummax()

    drawdown = (
        nav / running_peak - 1.0
    )

    thresholds = [
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
    ]

    return {
        "observations": int(len(drawdown)),
        "minimum_drawdown_pct": float(
            drawdown.min() * 100
        ),
        "percentile_25_pct": float(
            drawdown.quantile(0.25) * 100
        ),
        "median_drawdown_pct": float(
            drawdown.quantile(0.50) * 100
        ),
        "percentile_75_pct": float(
            drawdown.quantile(0.75) * 100
        ),
        "percentile_90_pct": float(
            drawdown.quantile(0.90) * 100
        ),
        "percentile_95_pct": float(
            drawdown.quantile(0.95) * 100
        ),
        "percentile_99_pct": float(
            drawdown.quantile(0.99) * 100
        ),
        "threshold_pct": {
            f"{int(threshold * 100)}": int(
                (drawdown <= -threshold).sum()
            )
            for threshold in thresholds
        },
        "threshold_pct_observed_pct": {
            f"{int(threshold * 100)}": float(
                (drawdown <= -threshold).mean() * 100
            )
            for threshold in thresholds
        },
    }


if __name__ == "__main__":

    isin = "INF174K01KT2"

    project_root = Path(__file__).resolve().parents[2]

    nav = load_fund_nav(
        isin,
        project_root,
    )

    evidence = calculate_drawdown_distribution(
        nav
    )

    print(evidence)
