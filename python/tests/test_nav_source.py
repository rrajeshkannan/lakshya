import pandas as pd
import pytest

from fund_analysis.nav_source import MfapiNavSource


class FakeHttpResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_nav_source_fetches_scheme_catalog_through_transport():
    # The source adapter obtains the MFAPI scheme catalog through
    # an injected transport. Tests must not depend on live internet access.
    responses = {
        "https://api.mfapi.in/mf": FakeHttpResponse(
            status_code=200,
            payload=[
                {
                    "schemeCode": 12345,
                    "schemeName": "Test Fund - Growth",
                    "isinGrowth": "TEST123",
                }
            ],
        )
    }

    def transport(url):
        return responses[url]

    source = MfapiNavSource(transport=transport)

    catalog = source.fetch_scheme_catalog()

    assert len(catalog) == 1
    assert catalog[0]["schemeCode"] == 12345


def test_nav_source_fetches_nav_history_through_transport():
    # Once the scheme code is known, MFAPI history is retrieved from
    # the scheme-specific endpoint.
    responses = {
        "https://api.mfapi.in/mf/12345": FakeHttpResponse(
            status_code=200,
            payload={
                "data": [
                    {"date": "17-08-2026", "nav": "123.45"},
                    {"date": "14-08-2026", "nav": "122.80"},
                ]
            },
        )
    }

    def transport(url):
        return responses[url]

    source = MfapiNavSource(transport=transport)

    nav = source.fetch_nav_history(12345)

    assert list(nav.columns) == ["date", "nav"]
    assert len(nav) == 2
    assert nav["nav"].iloc[0] == 123.45


def test_nav_source_rejects_unsuccessful_catalog_response():
    # A failed source response must never be mistaken for an empty
    # or valid Fund universe.
    def transport(url):
        return FakeHttpResponse(
            status_code=500,
            payload={},
        )

    source = MfapiNavSource(transport=transport)

    with pytest.raises(ValueError, match="MFAPI"):
        source.fetch_scheme_catalog()


def test_nav_source_rejects_unsuccessful_nav_response():
    # A failed historical NAV response must be surfaced rather than
    # converted into incomplete evidence.
    def transport(url):
        return FakeHttpResponse(
            status_code=503,
            payload={},
        )

    source = MfapiNavSource(transport=transport)

    with pytest.raises(ValueError, match="MFAPI"):
        source.fetch_nav_history(12345)


def test_nav_source_resolves_isin_to_scheme_code():
    # MFAPI identifies historical NAV endpoints by scheme code,
    # while Lakshya identifies funds by ISIN.
    source = MfapiNavSource(
        scheme_catalog=[
            {
                "schemeCode": 12345,
                "schemeName": "Test Fund - Growth",
                "isinGrowth": "TEST123",
            }
        ]
    )

    assert source.resolve_scheme_code("TEST123") == 12345


def test_nav_source_rejects_unknown_isin():
    # An unresolved ISIN is an identity problem, not a missing NAV.
    source = MfapiNavSource(
        scheme_catalog=[
            {
                "schemeCode": 12345,
                "schemeName": "Test Fund - Growth",
                "isinGrowth": "TEST123",
            }
        ]
    )

    with pytest.raises(ValueError, match="ISIN"):
        source.resolve_scheme_code("UNKNOWN")


def test_nav_source_parses_nav_history():
    # Source-specific NAV responses are converted into the canonical
    # date/nav representation expected by Lakshya.
    source = MfapiNavSource(scheme_catalog=[])

    response = {
        "data": [
            {"date": "17-08-2026", "nav": "123.45"},
            {"date": "14-08-2026", "nav": "122.80"},
        ]
    }

    nav = source.parse_nav_response(response)

    assert list(nav.columns) == ["date", "nav"]
    assert nav["date"].iloc[0] == pd.Timestamp("2026-08-17")
    assert nav["nav"].iloc[0] == 123.45


def test_nav_source_does_not_calculate_behavioural_evidence():
    # The source adapter retrieves observations only.
    # Elevation, Protection and Resilience remain Fund-engine concerns.
    source = MfapiNavSource(scheme_catalog=[])

    response = {
        "data": [
            {"date": "17-08-2026", "nav": "123.45"},
        ]
    }

    nav = source.parse_nav_response(response)

    assert "return" not in nav.columns
    assert "drawdown" not in nav.columns
    assert "recovery" not in nav.columns
