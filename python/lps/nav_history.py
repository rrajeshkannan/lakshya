"""
Canonical NAV-history boundary for the Lakshya Position System.

This module sits between external NAV sources and the canonical factual
NAV history consumed by downstream Lakshya systems.

External sources may differ in row ordering, date representation, column
ordering, and data cleanliness. LPS establishes one canonical contract:

    date    -> pandas datetime
    nav     -> numeric, strictly positive
    rows    -> unique dates, chronological order

We normalize what is unambiguous.
We reject what is ambiguous.
We never manufacture historical observations.
"""

import pandas as pd


def normalize_nav_history(nav: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and normalize a raw NAV history into LPS's canonical
    representation.

    Missing calendar days are preserved as-is. A mutual-fund NAV history
    is an observation history, not an artificially completed calendar-day
    time series.

    Raises:
        ValueError: If required columns are missing, dates/NAV values are
            missing or invalid, dates are duplicated, or NAV values are
            not strictly positive.
    """

    required_columns = {"date", "nav"}

    missing_columns = required_columns - set(nav.columns)

    if missing_columns:
        raise ValueError(
            f"NAV history is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    normalized = nav[["date", "nav"]].copy()

    normalized["date"] = pd.to_datetime(
        normalized["date"],
        errors="coerce",
    )

    if normalized["date"].isna().any():
        raise ValueError("NAV history contains invalid or missing dates.")

    normalized["nav"] = pd.to_numeric(
        normalized["nav"],
        errors="coerce",
    )

    if normalized["nav"].isna().any():
        raise ValueError("NAV history contains missing or invalid NAV values.")

    if normalized["date"].duplicated().any():
        raise ValueError("NAV history contains duplicate dates.")

    if (normalized["nav"] <= 0).any():
        raise ValueError("NAV values must be strictly positive.")

    return normalized.sort_values("date").reset_index(drop=True)
