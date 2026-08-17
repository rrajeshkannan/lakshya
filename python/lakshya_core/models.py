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

    drawdown_episodes.py
        -> DrawdownEpisode

The Fund Behavioural Fingerprint then composes the three Fund Compass
dimensions:

    Elevation
    Protection
    Resilience

This separation is intentional.  We don't want multiple competing
definitions of the same evidence object scattered across the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .drawdown_episodes import DrawdownEpisode
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
    whether a fund is suitable, resilient, or preferable.
    """
    start_date: date
    end_date: date
    observations: int


@dataclass(frozen=True)
class Evidence:
    """
    Describes the availability and quality of observed historical evidence.

    Evidence is deliberately separated from conclusions. It records what
    historical information is available for analysis and provides context
    for interpreting the resulting observations.

    A lack of evidence is not the same as evidence of poor behaviour.
    Similarly, limited history should constrain what Lakshya is allowed
    to conclude rather than being silently converted into a numerical
    value.

    This class belongs to the supporting evidence layer. The Fund
    Behavioural Fingerprint is built from specific behavioural evidence
    such as Elevation, Protection, and Resilience.
    """
    fund_isin: str
    window: EvidenceWindow
    metric_name: str
    value: float
    source: str


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

    Recovery duration, underwater duration and episode journeys belong
    to ResilienceEvidence.  Benchmark-relative behaviour is also kept
    outside this intrinsic Fund Compass dimension.
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
class ResilienceEvidence:
    """
    Observed recovery journeys following drawdown episodes.

    The individual episodes are retained deliberately.  Summary
    statistics provide the 30,000-foot view, while the episode list
    preserves the 3-foot evidence needed to investigate the journey.

    Recovered and ongoing episodes are kept distinct because an ongoing
    episode has no observed recovery duration.
    """

    episode_count: int
    recovered_count: int
    ongoing_count: int
    median_depth_pct: float | None
    worst_depth_pct: float | None
    median_decline_days_recovered: float | None
    median_recovery_days: float | None
    median_underwater_days_recovered: float | None
    median_underwater_days_ongoing: float | None
    episodes: list[DrawdownEpisode]


@dataclass(frozen=True)
class FundBehaviouralFingerprint:
    """
    The Fund-stage behavioural description of a fund.

    This is the Fund Compass:

        Elevation
        Protection
        Resilience

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
    resilience: ResilienceEvidence
