"""Compatibility import for the human-reviewed Fund scope loader.

The formation boundary is now ``funds_in_scope.csv``. This module remains
only as a thin compatibility name for the production runner while callers
migrate to ``fund_analysis.funds_in_scope``.
"""

from fund_analysis.funds_in_scope import FUNDS_IN_SCOPE_PATH, load_funds_in_scope


# Temporary compatibility alias. No automated admissibility policy lives here.
FUNDS_ADMISSIBLE_PATH = FUNDS_IN_SCOPE_PATH


def load_admissible_funds(path=FUNDS_IN_SCOPE_PATH):
    return load_funds_in_scope(path)
