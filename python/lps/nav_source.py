"""
MFAPI NAV source adapter for the Lakshya Position System.

This module translates MFAPI-specific responses into the small,
source-independent representation consumed by LPS.

It deliberately does not calculate returns, drawdowns, resilience,
make portfolio decisions, or persist evidence artifacts.

Network transport is injected so tests remain deterministic.
"""

from typing import Any, Callable
from urllib.request import Request, urlopen

import pandas as pd


DEFAULT_MFAPI_BASE_URL = "https://api.mfapi.in"


class MfapiHttpResponse:
    def __init__(self, response):
        self.status_code = response.status
        self._response = response

    def json(self):
        import json
        return json.loads(self._response.read().decode("utf-8"))


def mfapi_http_transport(url: str):
    request = Request(
        url,
        headers={
            "User-Agent": "Lakshya/1.0",
            "Accept": "application/json",
        },
    )
    return MfapiHttpResponse(urlopen(request, timeout=30))


class MfapiNavSource:
    """Adapter for MFAPI scheme-catalog and historical-NAV endpoints."""

    def __init__(
        self,
        scheme_catalog: list[dict] | None = None,
        transport: Callable[[str], Any] | None = None,
    ):
        self.scheme_catalog = scheme_catalog or []
        self.transport = transport

    def resolve_scheme_code(self, isin: str) -> int:
        """Resolve a Lakshya Fund ISIN to the MFAPI scheme code."""
        matches = [
            scheme
            for scheme in self.scheme_catalog
            if scheme.get("isinGrowth") == isin
            or scheme.get("isinDivReinvestment") == isin
        ]

        if not matches:
            raise ValueError(
                f"ISIN could not be resolved through MFAPI scheme catalog: {isin}"
            )

        scheme_code = matches[0].get("schemeCode")

        if scheme_code is None:
            raise ValueError(
                f"MFAPI scheme entry has no scheme code for ISIN: {isin}"
            )

        return int(scheme_code)

    def fetch_scheme_catalog(self) -> list[dict]:
        """Fetch the complete MFAPI scheme catalog."""
        response = self._request(f"{DEFAULT_MFAPI_BASE_URL}/mf")
        catalog = response.json()

        if not isinstance(catalog, list):
            raise ValueError("MFAPI scheme catalog response is invalid.")

        return catalog

    def fetch_nav_history(self, scheme_code: int) -> pd.DataFrame:
        """Fetch historical NAV observations for an MFAPI scheme code."""
        response = self._request(f"{DEFAULT_MFAPI_BASE_URL}/mf/{scheme_code}")
        return self.parse_nav_response(response.json())

    def parse_nav_response(self, response: dict) -> pd.DataFrame:
        """Convert an MFAPI NAV response into a date/nav DataFrame."""
        observations = response.get("data")

        if observations is None:
            raise ValueError("MFAPI NAV response does not contain data.")

        nav = pd.DataFrame(observations)
        required_columns = {"date", "nav"}

        if not required_columns.issubset(nav.columns):
            raise ValueError(
                "MFAPI NAV response is missing required fields: "
                f"{sorted(required_columns - set(nav.columns))}"
            )

        nav = nav[["date", "nav"]].copy()
        nav["date"] = pd.to_datetime(
            nav["date"], format="%d-%m-%Y", errors="coerce"
        )
        nav["nav"] = pd.to_numeric(nav["nav"], errors="coerce")
        return nav

    def _request(self, url: str) -> Any:
        """Execute a source request through the injected transport."""
        if self.transport is None:
            raise ValueError("MFAPI transport has not been configured.")

        response = self.transport(url)

        if response.status_code != 200:
            raise ValueError(
                f"MFAPI request failed with status {response.status_code}: {url}"
            )

        return response
