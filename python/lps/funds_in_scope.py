"""Reviewer-owned Fund formation scope and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Collection

import pandas as pd

from lakshya_core.models import Fund


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FUNDS_IN_SCOPE_PATH = PROJECT_ROOT / "data" / "lps" / "funds_in_scope.csv"
REQUIRED_COLUMNS = ("isin", "asset_class", "is_elss")
ALLOWED_ASSET_CLASSES = frozenset({"equity", "debt"})
ALLOWED_ELSS_VALUES = frozenset({"yes", "no"})


def load_fund_scope_rows(
    path: Path = FUNDS_IN_SCOPE_PATH,
) -> list[dict[str, str]]:
    """Load and validate the reviewer-maintained fund scope manifest.

    The reviewer supplies all classifications. Lakshya does not infer them
    from MFAPI or any other external source.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    actual_columns = tuple(str(column).strip() for column in df.columns)
    required = set(REQUIRED_COLUMNS)
    actual = set(actual_columns)

    missing = sorted(required - actual)
    unexpected = sorted(actual - required)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing columns: {missing}")
        if unexpected:
            details.append(f"unexpected columns: {unexpected}")
        raise ValueError("Fund scope has an invalid column layout (" + "; ".join(details) + ").")

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in df.to_dict("records"):
        isin = str(row["isin"]).strip()
        asset_class = str(row["asset_class"]).strip().lower()
        is_elss = str(row["is_elss"]).strip().lower()

        if not isin:
            raise ValueError("Fund scope contains an empty ISIN.")
        if isin in seen:
            raise ValueError(f"Fund scope contains duplicate ISIN: {isin}")
        if not asset_class:
            raise ValueError(f"Fund scope has a blank asset_class for ISIN: {isin}")
        if asset_class not in ALLOWED_ASSET_CLASSES:
            raise ValueError(
                f"Fund scope has invalid asset_class for ISIN {isin}: {asset_class!r}"
            )
        if not is_elss:
            raise ValueError(f"Fund scope has a blank is_elss for ISIN: {isin}")
        if is_elss not in ALLOWED_ELSS_VALUES:
            raise ValueError(
                f"Fund scope has invalid is_elss for ISIN {isin}: {is_elss!r}"
            )
        if asset_class == "debt" and is_elss == "yes":
            raise ValueError(f"Debt fund cannot be marked ELSS: {isin}")

        seen.add(isin)
        rows.append(
            {
                "isin": isin,
                "asset_class": asset_class,
                "is_elss": is_elss,
            }
        )

    if not rows:
        raise ValueError(f"Fund scope contains no funds: {path}")

    return rows


def validate_scope_covers_positions(
    scope_isins: Collection[str],
    position_isins: Collection[str],
) -> None:
    """Require every LPS position ISIN to exist in the reviewer scope."""
    scope = {str(isin).strip() for isin in scope_isins if str(isin).strip()}
    positions = {str(isin).strip() for isin in position_isins if str(isin).strip()}
    missing = sorted(positions - scope)
    if missing:
        raise ValueError(
            "Fund scope is missing ISINs present in LPS positions: "
            + ", ".join(missing)
        )


def load_funds_in_scope(
    path: Path = FUNDS_IN_SCOPE_PATH,
) -> list[Fund]:
    """Load Fund identities after validating the complete scope contract."""
    return [Fund(name=row["isin"], isin=row["isin"]) for row in load_fund_scope_rows(path)]
