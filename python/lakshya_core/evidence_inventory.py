from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"


def load_nav_cache(path: Path) -> pd.DataFrame:
    """Load one inherited MFAPI NAV cache into a DataFrame."""

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    data = payload.get("data", [])

    if not data:
        return pd.DataFrame(columns=["date", "nav"])

    df = pd.DataFrame(data)

    df["date"] = pd.to_datetime(
        df["date"],
        format="%d-%m-%Y",
        errors="coerce",
    )

    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    return df


def inspect_nav_cache(path: Path) -> dict:
    """Inspect one inherited NAV cache for structural integrity."""

    df = load_nav_cache(path)

    isin = path.stem.replace("_nav", "")
    meta_path = CACHE_DIR / f"{isin}_meta.json"

    if df.empty:
        return {
            "ISIN": isin,
            "First_NAV": None,
            "Last_NAV": None,
            "Observations": 0,
            "Median_Gap_Days": None,
            "Max_Gap_Days": None,
            "Duplicate_Dates": 0,
            "Duplicate_Records": 0,
            "Invalid_Dates": 0,
            "Invalid_NAV": 0,
            "Metadata_Available": meta_path.exists(),
        }

    invalid_dates = int(df["date"].isna().sum())
    invalid_nav = int(
        df["nav"].isna().sum()
        + (df["nav"] <= 0).sum()
    )

    valid = df.dropna(subset=["date", "nav"]).copy()
    valid = valid[valid["nav"] > 0]
    valid = valid.sort_values("date")

    gaps = valid["date"].diff().dt.days.dropna()

    duplicate_dates = int(valid["date"].duplicated().sum())
    duplicate_records = int(
        valid.duplicated(subset=["date", "nav"]).sum()
    )

    return {
        "ISIN": isin,
        "First_NAV": valid["date"].min().date(),
        "Last_NAV": valid["date"].max().date(),
        "Observations": len(valid),
        "Median_Gap_Days": gaps.median(),
        "Max_Gap_Days": gaps.max(),
        "Duplicate_Dates": duplicate_dates,
        "Duplicate_Records": duplicate_records,
        "Invalid_Dates": invalid_dates,
        "Invalid_NAV": invalid_nav,
        "Metadata_Available": meta_path.exists(),
    }


def build_evidence_inventory() -> pd.DataFrame:
    """Build an integrity inventory for all inherited NAV histories."""

    records = []

    for path in sorted(CACHE_DIR.glob("*_nav.json")):
        records.append(inspect_nav_cache(path))

    return pd.DataFrame(records)


if __name__ == "__main__":
    inventory = build_evidence_inventory()

    print(inventory.to_string(index=False))