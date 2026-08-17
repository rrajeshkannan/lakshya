from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class BenchmarkEvidence:
    index_name: str
    first_date: object
    last_date: object
    observations: int
    median_gap_days: float
    max_gap_days: int
    duplicate_dates: int
    missing_values: int
    invalid_values: int
    invalid_dates: int


def load_benchmark_history(path: Path) -> pd.DataFrame:
    """
    Load the consolidated benchmark TRI history.

    Expected structure:

    Date,
    NIFTY 100,
    NIFTY 500,
    ...
    """

    df = pd.read_csv(path)

    if "Date" not in df.columns:
        raise ValueError("Benchmark file must contain a 'Date' column.")

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%Y-%m-%d",
        errors="coerce",
    )

    return df


def calculate_benchmark_evidence(
    df: pd.DataFrame,
    index_name: str,
) -> BenchmarkEvidence:

    if index_name not in df.columns:
        raise ValueError(
            f"Benchmark index not found: {index_name}"
        )

    dates = df["Date"]
    values = df[index_name]

    invalid_dates = int(dates.isna().sum())

    raw_values = values.astype("string").str.strip()

    missing_mask = raw_values.isna() | raw_values.eq("")

    numeric_values = pd.to_numeric(
        raw_values.where(~missing_mask),
        errors="coerce",
    )

    invalid_mask = (
        ~missing_mask
        & numeric_values.isna()
    )

    missing_values = int(missing_mask.sum())
    invalid_values = int(invalid_mask.sum())

    valid = pd.DataFrame(
        {
            "date": dates,
            "value": numeric_values,
        }
    ).dropna()

    valid = valid.sort_values("date")

    duplicate_dates = int(
        valid["date"].duplicated().sum()
    )

    if valid.empty:
        raise ValueError(
            f"No valid observations for {index_name}"
        )

    gaps = (
        valid["date"]
        .diff()
        .dt.days
        .dropna()
    )

    median_gap_days = (
        float(gaps.median())
        if not gaps.empty
        else 0.0
    )

    max_gap_days = (
        int(gaps.max())
        if not gaps.empty
        else 0
    )

    return BenchmarkEvidence(
        index_name=index_name,
        first_date=valid["date"].min().date(),
        last_date=valid["date"].max().date(),
        observations=len(valid),
        median_gap_days=median_gap_days,
        max_gap_days=max_gap_days,
        duplicate_dates=duplicate_dates,
        missing_values=missing_values,
        invalid_values=invalid_values,
        invalid_dates=invalid_dates,
    )


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    path = (
        project_root
        / "data"
        / "benchmarks_consolidated.csv"
    )

    df = load_benchmark_history(path)

    for index_name in df.columns:
        if index_name == "Date":
            continue

        evidence = calculate_benchmark_evidence(
            df,
            index_name,
        )

        print(evidence)
