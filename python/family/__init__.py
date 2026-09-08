"""Family-level portfolio architecture validation for Lakshya."""

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
