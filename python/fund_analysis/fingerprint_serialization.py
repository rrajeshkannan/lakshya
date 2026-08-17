"""
Serialization of Fund-stage behavioural fingerprints.

The Fund-stage engine works with typed dataclasses.

This module converts that typed evidence into a JSON-safe dictionary
for persistence. It performs no analysis and makes no judgement.
"""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd


def fingerprint_to_dict(fingerprint: Any) -> dict:
    """
    Convert a FundBehaviouralFingerprint dataclass into a JSON-safe
    dictionary.

    Nested dataclasses are recursively converted by dataclasses.asdict().
    Date-like values are represented using ISO date/time strings.
    """

    if not is_dataclass(fingerprint):
        raise TypeError(
            "fingerprint_to_dict() expects a dataclass fingerprint."
        )

    value = asdict(fingerprint)

    return _make_json_safe(value)


def _make_json_safe(value: Any) -> Any:
    """
    Recursively convert values into JSON-compatible representations.
    """

    if isinstance(value, dict):
        return {
            key: _make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _make_json_safe(item)
            for item in value
        ]

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    return value
