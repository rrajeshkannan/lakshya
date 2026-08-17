"""
Fund-stage analysis orchestration.

This module composes existing Fund-stage components.

It does not implement behavioural calculations itself.
"""

import json
from pathlib import Path

import pandas as pd

from fund_analysis.fingerprint_evidence import FingerprintEvidenceStore
from fund_analysis.fingerprint_serialization import fingerprint_to_dict

from lakshya_core.fund_fingerprint import (
    build_fund_behavioural_fingerprint,
)
from lakshya_core.models import Fund


def analyze_fund(
    *,
    fund: Fund,
    nav_evidence_path: Path,
    fingerprint_evidence_path: Path,
    generated_at: str,
):
    """
    Build and persist a Fund behavioural fingerprint from persisted
    NAV evidence.

    The NAV evidence artifact is the analytical input. No source
    acquisition happens here.
    """

    nav_payload = _load_nav_evidence(nav_evidence_path)

    if nav_payload["isin"] != fund.isin:
        raise ValueError(
            "NAV evidence identity does not match Fund identity."
        )

    nav = pd.DataFrame(nav_payload["observations"])

    nav["date"] = pd.to_datetime(nav["date"])
    nav["nav"] = pd.to_numeric(nav["nav"])

    nav = nav.sort_values("date").reset_index(drop=True)

    fingerprint = build_fund_behavioural_fingerprint(
        fund=fund,
        nav=nav,
    )

    evidence = fingerprint_to_dict(fingerprint)

    store = FingerprintEvidenceStore(
        fingerprint_evidence_path
    )

    store.create(
        fingerprint=evidence,
        nav_artifact_version=nav_payload["artifact_version"],
        generated_at=generated_at,
    )

    return fingerprint


def _load_nav_evidence(path: Path) -> dict:
    """
    Load a persisted NAV evidence artifact.
    """

    path = Path(path)

    if not path.exists():
        raise ValueError(
            f"NAV evidence artifact does not exist: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        payload = json.load(f)

    required_fields = {
        "artifact_version",
        "isin",
        "observations",
    }

    missing = required_fields - set(payload)

    if missing:
        raise ValueError(
            "NAV evidence artifact is missing required fields: "
            f"{sorted(missing)}"
        )

    if not payload["observations"]:
        raise ValueError(
            "NAV evidence artifact contains no observations."
        )

    return payload
