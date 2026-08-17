from pathlib import Path
import json

import pandas as pd

from lakshya_core.capture import calculate_capture


def load_fund_nav(isin: str, project_root: Path) -> pd.Series:
    path = project_root / "data" / "cache" / f"{isin}_nav.json"

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    data = payload["data"]

    df = pd.DataFrame(data)

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


def load_benchmark(
    benchmark_name: str,
    project_root: Path,
) -> pd.Series:

    path = (
        project_root
        / "data"
        / "benchmarks_consolidated.csv"
    )

    df = pd.read_csv(path)

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%Y-%m-%d",
        errors="raise",
    )

    values = pd.to_numeric(
        df[benchmark_name],
        errors="coerce",
    )

    return pd.Series(
        values.values,
        index=df["Date"],
        name=benchmark_name,
    ).dropna()


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    # fund_isin = "INF174K01KT2"
    # benchmark_name = "NIFTY SMALLCAP 250"
    # benchmark_name = "NIFTY 500"
    fund_isin = "INF109K01BL4"
    # benchmark_name = "NIFTY 100"
    benchmark_name = "NIFTY 500"

    fund_nav = load_fund_nav(
        fund_isin,
        project_root,
    )

    benchmark_nav = load_benchmark(
        benchmark_name,
        project_root,
    )

    evidence = calculate_capture(
        fund_nav,
        benchmark_nav,
    )

    print(evidence)
