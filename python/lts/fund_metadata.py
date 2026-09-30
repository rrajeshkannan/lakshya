"""Transition-relevant fund metadata and classification."""

from __future__ import annotations

from dataclasses import dataclass

from lps.scheme import scheme_record


@dataclass(frozen=True)
class TransitionFundMetadata:
    """Minimal source-derived fund metadata exposed to LTS."""

    isin: str
    scheme_name: str | None = None
    asset_class: str | None = None
    is_elss: bool = False
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
    metadata = scheme_record(scheme_metadata)
    scheme_name = metadata.get("schemeName") or metadata.get("scheme_name")
    scheme_type = metadata.get("schemeType") or metadata.get("scheme_type")
    asset_class = metadata.get("asset_class")
    return TransitionFundMetadata(
        isin=isin,
        scheme_name=str(scheme_name) if scheme_name else None,
        asset_class=str(asset_class) if asset_class else None,
        is_elss=bool(metadata.get("is_elss", False)),
        scheme_type=str(scheme_type) if scheme_type else None,
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
    asset_class = (metadata.asset_class or "").strip().lower()
    if asset_class == "equity":
        return FundClassification(metadata.isin, "Equity", metadata.is_elss, "MFAPI")
    if asset_class == "debt":
        return FundClassification(metadata.isin, "Debt", False, "MFAPI")
    return FundClassification(metadata.isin, "Equity", False, "DEFAULT")


__all__ = [
    "FundClassification",
    "TransitionFundMetadata",
    "classify_fund",
    "classify_scope_row",
    "project_fund_metadata",
]
