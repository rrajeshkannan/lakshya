from pathlib import Path

import pandas as pd

from lakshya_core.models import Fund


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FUNDS_ADMISSIBLE_PATH = (
    PROJECT_ROOT
    / "data"
    / "fund"
    / "funds_admissible.csv"
)


def load_admissible_funds(
    path: Path = FUNDS_ADMISSIBLE_PATH,
) -> list[Fund]:
    """
    Load the admissible Fund universe as domain Fund objects.

    At this boundary, a Fund has already earned standing or admission.
    CURRENT/POTENTIAL provenance is deliberately no longer relevant.

    The admissible CSV provides only the identity information required
    by the Fund-stage behavioural engine:

        name
        isin
        category

    Portfolio allocation, goals, metadata, and behavioural calculations
    remain outside this boundary.
    """

    df = pd.read_csv(path)

    required_columns = {
        "scheme_name",
        "isin",
        "category",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Admissible Fund universe is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    funds = [
        Fund(
            name=row["scheme_name"],
            isin=row["isin"],
            category=row["category"],
        )
        for _, row in df.iterrows()
    ]

    return funds
