"""Transition-relevant fund metadata and classification."""

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
    """Transition-relevant classification supplied by the reviewer scope."""

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


def classify_scope_row(row: dict[str, str]) -> FundClassification:
    """Convert one human-maintained ``funds_in_scope.csv`` row into LTS facts."""
    return FundClassification(
        isin=str(row["isin"]).strip(),
        asset_class=str(row["asset_class"]).strip().lower(),
        is_elss=str(row["is_elss"]).strip().lower() == "yes",
        source="HUMAN_SCOPE",
    )


def classify_fund(metadata: TransitionFundMetadata) -> FundClassification:
    """Retain the source-metadata projection for compatibility only.

    Production LTS classification must use ``classify_scope_row`` and the
    reviewer-maintained fund scope, not external scheme metadata inference.
    """
    category = (metadata.scheme_category or "").strip().lower()
    return FundClassification(
        metadata.isin,
        "Debt" if "debt" in category else "Equity",
        "elss" in category,
        "LEGACY_METADATA",
    )


__all__ = [
    "FundClassification",
    "TransitionFundMetadata",
    "classify_fund",
    "classify_scope_row",
    "project_fund_metadata",
]
