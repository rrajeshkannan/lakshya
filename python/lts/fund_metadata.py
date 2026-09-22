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
    """Transition-relevant fund classification."""

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
    """Classify persisted source metadata for compatibility-level tests.

    The production LTS runner does not use this inference path. Production
    transition constraints are sourced from the reviewer-maintained
    ``funds_in_scope.csv`` through ``classify_scope_row``.
    """
    category = (metadata.scheme_category or "").strip().lower()
    if "elss" in category:
        return FundClassification(metadata.isin, "Equity", True, "MFAPI")
    if "equity" in category:
        return FundClassification(metadata.isin, "Equity", False, "MFAPI")
    if "debt" in category:
        return FundClassification(metadata.isin, "Debt", False, "MFAPI")
    return FundClassification(metadata.isin, "Equity", False, "DEFAULT")


__all__ = [
    "FundClassification",
    "TransitionFundMetadata",
    "classify_fund",
    "classify_scope_row",
    "project_fund_metadata",
]
