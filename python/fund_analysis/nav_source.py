"""Compatibility import for the LPS-owned NAV source adapter.

The implementation now lives in ``lps.nav_source``. This module remains
as a temporary compatibility boundary while Fund-stage consumers migrate.
"""

from lps.nav_source import (
    DEFAULT_MFAPI_BASE_URL,
    MfapiHttpResponse,
    MfapiNavSource,
    mfapi_http_transport,
)

__all__ = [
    "DEFAULT_MFAPI_BASE_URL",
    "MfapiHttpResponse",
    "MfapiNavSource",
    "mfapi_http_transport",
]
