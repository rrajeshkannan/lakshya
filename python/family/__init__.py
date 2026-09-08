"""Family-level portfolio architecture validation for Lakshya."""

from . import attribution as _attribution
from .attribution import (
    ATTRIBUTION_SCHEMA_VERSION,
    build_family_attribution,
    run_family_attribution,
)
from . import staging as _staging
from .purpose_staging_adapter import load_intent_rows
from .staging import (
    SCHEMA_VERSION as PURPOSE_STAGING_SCHEMA_VERSION,
    commit_staging,
    initialize_staging,
    run_turn,
)
from lps.purpose_capital import purpose_capital_from_positions


# Family attribution consumes factual Purpose capital from LPS rather than
# treating capital as human Purpose input.
def _load_lps_purpose_capital(path=None):
    if path is None:
        from pathlib import Path
        path = Path(__file__).resolve().parents[2] / "data" / "lps" / "positions.csv"
    return purpose_capital_from_positions(path)


_attribution.load_purpose_capital = _load_lps_purpose_capital

# The dated staging workspace may carry mutable working capital, but its
# source seed must come from intent-only Purpose input plus LPS valuation.
_staging._load_rows = lambda path: load_intent_rows(
    path,
    path.parents[1] / "lps" / "positions.csv",
)

__all__ = [
    "ATTRIBUTION_SCHEMA_VERSION",
    "build_family_attribution",
    "run_family_attribution",
    "PURPOSE_STAGING_SCHEMA_VERSION",
    "commit_staging",
    "initialize_staging",
    "run_turn",
]
