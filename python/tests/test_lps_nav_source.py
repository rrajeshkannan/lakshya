import pandas as pd
import pytest

from lps.nav_source import MfapiNavSource


class FakeHttpResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_nav_source_fetches_scheme_catalog_through_transport():
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
    def transport(url):
        return FakeHttpResponse(status_code=500, payload={})

    source = MfapiNavSource(transport=transport)

    with pytest.raises(ValueError, match="MFAPI"):
        source.fetch_scheme_catalog()


def test_nav_source_rejects_unsuccessful_nav_response():
    def transport(url):
        return FakeHttpResponse(status_code=503, payload={})

    source = MfapiNavSource(transport=transport)

    with pytest.raises(ValueError, match="MFAPI"):
        source.fetch_nav_history(12345)


def test_nav_source_resolves_isin_to_scheme_code():
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
