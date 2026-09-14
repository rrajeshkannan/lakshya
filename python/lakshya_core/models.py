"""
Lakshya domain models.

This module contains the small, high-level objects that describe the
architecture of Lakshya.

Important design boundary
-------------------------
The models in this file describe *what evidence belongs together*.
They do not calculate investment metrics and they do not make investment
decisions.

The detailed evidence objects remain owned by the modules that calculate
them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Goal:
    """A family financial goal."""

    name: str
    purpose: str
    target_corpus: Optional[float] = None
    target_date: Optional[date] = None
    flexibility: str = "unknown"
    consequence_of_shortfall: str = "unknown"
    lifecycle: str = "accumulation"


@dataclass(frozen=True)
class Fund:
    """Identity of a mutual fund used by the Fund-stage engine."""

    name: str
    isin: str
    category: Optional[str] = None
    benchmark: Optional[str] = None


@dataclass(frozen=True)
class Family:
    """Family-level identity.

    Portfolio and mission semantics deliberately remain outside the
    Fund-stage implementation for now.
    """

    name: str
    goals: list[Goal] = field(default_factory=list)


@dataclass(frozen=True)
class Portfolio:
    """A portfolio container.

    This remains intentionally lightweight. Portfolio behaviour belongs
    to the next architectural stage and is not implemented here.
    """

    name: str
    goal: str
    weights: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceWindow:
    """
    Describes the historical time window over which evidence is observed.

    An evidence window records the temporal boundary of an observation,
    rather than making any judgement about the quality or behaviour
    observed within that window.
    """

    start_date: date
    end_date: date
    observations: int


@dataclass(frozen=True)
class ElevationEvidence:
    """
    Observed prosperity terrain across investment horizons.

    A horizon is optional because the available NAV history may not be
    long enough to support it.

    None means "not observed / insufficient evidence", not zero.
    """

    rolling_3y: object | None
    rolling_5y: object | None
    rolling_7y: object | None
    rolling_10y: object | None


@dataclass(frozen=True)
class ProtectionEvidence:
    """
    Observed adversity terrain measured against the fund's own
    high-water mark.
    """

    observations: int
    median_severity_pct: float | None
    percentile_75_severity_pct: float | None
    percentile_90_severity_pct: float | None
    percentile_95_severity_pct: float | None
    percentile_99_severity_pct: float | None
    maximum_severity_pct: float | None
    days_at_or_above_threshold: dict[int, int]
    pct_days_at_or_above_threshold: dict[int, float]
