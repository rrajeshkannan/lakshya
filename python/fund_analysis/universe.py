"""
Fund-universe loading for the Fund-stage application layer.

This module translates the declared Fund universe into the domain
objects consumed by the Fund-stage behavioural engine.

It deliberately knows about the universe source file, but knows
nothing about NAV acquisition, portfolio holdings, goals, or
behavioural calculations.
"""

from pathlib import Path

import pandas as pd

from lakshya_core.models import Fund


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FUNDS_UNIVERSE_PATH = PROJECT_ROOT / "data" / "funds_universe.csv"


def load_fund_universe(
    path: Path = FUNDS_UNIVERSE_PATH,
) -> list[Fund]:
    """
    Load the declared Fund universe as domain Fund objects.

    Only funds marked as current holdings in the universe file are
    included in the Fund-stage universe.

    The CSV provides the identity information required by the Fund
    behavioural engine:

        name
        isin
        category

    Portfolio allocation, goals, NAV history, and other metadata
    remain outside this boundary.
    """

    df = pd.read_csv(path)

    required_columns = {
        "name",
        "isin",
        "category",
        "is_current_holding",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Fund universe is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    current = df[df["is_current_holding"] == True].copy()

    funds = [
        Fund(
            name=row["name"],
            isin=row["isin"],
            category=row["category"],
        )
        for _, row in current.iterrows()
    ]

    return funds
