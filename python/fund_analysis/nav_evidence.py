"""Compatibility import for the LPS-owned NAV evidence store.

The implementation now lives in ``lps.nav_evidence``. This module remains
as a temporary compatibility boundary while Fund-stage consumers migrate.
"""

from lps.nav_evidence import NavEvidenceStore

__all__ = ["NavEvidenceStore"]
