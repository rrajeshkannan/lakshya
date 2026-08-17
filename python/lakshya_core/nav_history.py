"""
Canonical NAV-history boundary for the Lakshya engine.

This module deliberately sits between external NAV sources and the
behavioural-analysis engine.

External sources may differ in:
    - row ordering
    - date representation
    - column ordering
    - data cleanliness

The Fund-stage engine should not have to care about those differences.

This module establishes one canonical contract:

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
    Validate and normalize a raw NAV history into Lakshya's
    canonical analytical representation.

    Canonical representation:

        date    : datetime-like
        nav     : numeric and strictly positive

    The returned DataFrame is sorted chronologically by date.

    Missing calendar days are preserved as-is. A mutual-fund NAV
    history is an observation history, not an artificially completed
    calendar-day time series.

    Raises:
        ValueError:
            If required columns are missing, dates/NAV values are
            missing or invalid, dates are duplicated, or NAV values
            are not strictly positive.
    """

    required_columns = {"date", "nav"}

    missing_columns = required_columns - set(nav.columns)

    if missing_columns:
        raise ValueError(
            f"NAV history is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    normalized = nav[["date", "nav"]].copy()

    # Convert source dates into pandas datetime values so every
    # downstream calculation works with one internal date type.
    normalized["date"] = pd.to_datetime(
        normalized["date"],
        errors="coerce",
    )

    if normalized["date"].isna().any():
        raise ValueError("NAV history contains invalid or missing dates.")

    # Convert NAV values to numeric rather than allowing strings or
    # other source-specific representations into the analytical engine.
    normalized["nav"] = pd.to_numeric(
        normalized["nav"],
        errors="coerce",
    )

    if normalized["nav"].isna().any():
        raise ValueError("NAV history contains missing or invalid NAV values.")

    # Two different observations for the same date are ambiguous.
    # We deliberately refuse to choose one silently.
    if normalized["date"].duplicated().any():
        raise ValueError("NAV history contains duplicate dates.")

    # NAV represents a positive fund value. Zero or negative values
    # are invalid source observations for this analytical pipeline.
    if (normalized["nav"] <= 0).any():
        raise ValueError("NAV values must be strictly positive.")

    # The analytical engine consumes chronological observations.
    # Sorting here gives every downstream calculation one deterministic
    # ordering regardless of how the source delivered the data.
    normalized = normalized.sort_values("date").reset_index(drop=True)

    return normalized
