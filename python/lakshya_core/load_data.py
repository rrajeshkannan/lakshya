from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def load_goals() -> pd.DataFrame:
    """Load the existing Lakshya goal definitions."""
    return pd.read_csv(DATA_DIR / "goals.csv")


def load_funds_universe() -> pd.DataFrame:
    """Load the existing fund universe."""
    return pd.read_csv(DATA_DIR / "funds_universe.csv")


def load_current_holdings() -> pd.DataFrame:
    """Load the current portfolio holdings."""
    return pd.read_csv(DATA_DIR / "current_holdings.csv")


def load_goal_tag_mapping() -> pd.DataFrame:
    """Load existing goal-to-fund tagging information."""
    return pd.read_csv(DATA_DIR / "goal_tag_mapping.csv")