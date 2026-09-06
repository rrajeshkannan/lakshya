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
them:

    rolling_returns.py
        -> RollingReturnEvidence

The Fund Fingerprint then composes the two active Fund Compass dimensions:

    Elevation
    Protection

This separation is intentional.  We don't want multiple competing
definitions of the same evidence object scattered across the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .rolling_returns import RollingReturnEvidence


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

    This remains intentionally lightweight.  Portfolio behaviour belongs
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

    Keeping the window explicit matters because behavioural evidence is
    inherently historical: the same calculation can mean something
    different when based on a short, long, recent, or full-period history.

    This is a supporting domain concept. It does not itself determine
    whether a fund is suitable or preferable.
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

    rolling_3y: RollingReturnEvidence | None
    rolling_5y: RollingReturnEvidence | None
    rolling_7y: RollingReturnEvidence | None
    rolling_10y: RollingReturnEvidence | None


@dataclass(frozen=True)
class ProtectionEvidence:
    """
    Observed adversity terrain measured against the fund's own
    high-water mark.

    This object deliberately contains severity information only.
    Benchmark-relative behaviour is kept outside this intrinsic Fund
    Compass dimension.
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


@dataclass(frozen=True)
class FundFingerprint:
    """
    The Fund-stage behavioural description of a fund.

    The active Fund Compass is:

        Elevation
        Protection

    It intentionally contains no score, rank, suitability judgement or
    recommendation.

    The purpose at this stage is to answer:

        "What kind of teammate is this fund?"

    The question of whether several funds should form a team belongs to
    the later Portfolio stage.
    """

    fund: Fund
    elevation: ElevationEvidence
    protection: ProtectionEvidence
