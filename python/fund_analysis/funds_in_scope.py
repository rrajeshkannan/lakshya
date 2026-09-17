"""Human-reviewed Fund formation scope."""

from pathlib import Path

import pandas as pd

from lakshya_core.models import Fund


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FUNDS_IN_SCOPE_PATH = PROJECT_ROOT / "data" / "lps" / "funds_in_scope.csv"


def load_funds_in_scope(
    path: Path = FUNDS_IN_SCOPE_PATH,
) -> list[Fund]:
    """Load the Fund universe admitted by the human reviewer.

    This boundary deliberately performs no policy screening. The reviewer
    controls which Funds are in scope; Lakshya subsequently applies its
    behavioural FUND gate to that universe.

    Only Fund identity is required by the downstream analytical engine.
    """
    df = pd.read_csv(path, keep_default_na=False)
    required_columns = {"entry_type", "isin"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            "Fund scope is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    funds: list[Fund] = []
    seen: set[str] = set()
    for row in df.to_dict("records"):
        isin = str(row["isin"]).strip()
        if not isin:
            raise ValueError("Fund scope contains an empty ISIN.")
        if isin in seen:
            raise ValueError(f"Fund scope contains duplicate ISIN: {isin}")
        seen.add(isin)
        funds.append(Fund(name=isin, isin=isin))

    return funds
