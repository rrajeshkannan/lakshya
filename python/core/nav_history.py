"""Compatibility import for the LPS-owned NAV history boundary.

The implementation now lives in ``lps.nav_history``. This module remains
as a temporary compatibility boundary while downstream behavioural consumers
migrate to the LPS factual NAV representation.
"""

from lps.nav_history import cutoff_nav_history, normalize_nav_history

__all__ = ["cutoff_nav_history", "normalize_nav_history"]
