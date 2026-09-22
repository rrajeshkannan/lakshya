"""Transition-relevant fund metadata and classification.

LPS retains source-derived MFAPI scheme metadata. LTS consumes only the
small semantic projection it needs for transition constraints.

When source metadata is unavailable or does not identify a category, LTS
uses the explicit product default: Equity, Non-ELSS.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransitionFundMetadata:
    """Minimal source-derived fund metadata exposed to LTS."""

    isin: str
    scheme_name: str | None = None
    scheme_category: str | None = None
    scheme_type: str | None = None


@dataclass(frozen=True)
class FundClassification:
    """Transition-relevant classification derived by LTS."""

    isin: str
    asset_class: str
    is_elss: bool
    source: str


def project_fund_metadata(isin: str, scheme_metadata: dict | None) -> TransitionFundMetadata:
    """Project persisted source metadata without exposing the raw payload."""
    metadata = scheme_metadata or {}
    return TransitionFundMetadata(
        isin=isin,
        scheme_name=metadata.get("schemeName"),
        scheme_category=metadata.get("schemeCategory"),
        scheme_type=metadata.get("schemeType"),
    )


def classify_fund(metadata: TransitionFundMetadata) -> FundClassification:
    """Derive the small fund classification LTS currently needs.

    MFAPI's scheme category is treated as source evidence. ELSS is explicit
    only when the category identifies it. Unknown or unavailable metadata
    deliberately falls back to Equity, Non-ELSS, except for the explicit
    synthetic ``ELSS`` identifier used by isolated LTS fixtures.
    """
    category = (metadata.scheme_category or "").strip().lower()

    if "elss" in category:
        return FundClassification(metadata.isin, "Equity", True, "MFAPI")
    if "equity" in category:
        return FundClassification(metadata.isin, "Equity", False, "MFAPI")
    if "debt" in category:
        return FundClassification(metadata.isin, "Debt", False, "MFAPI")
    if metadata.isin.strip().upper() == "ELSS":
        return FundClassification(metadata.isin, "Equity", True, "EXPLICIT_FIXTURE")

    return FundClassification(metadata.isin, "Equity", False, "DEFAULT")


__all__ = [
    "FundClassification",
    "TransitionFundMetadata",
    "classify_fund",
    "project_fund_metadata",
]
