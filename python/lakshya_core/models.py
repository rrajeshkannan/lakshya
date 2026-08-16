from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Goal:
    name: str
    purpose: str
    target_corpus: Optional[float] = None
    target_date: Optional[date] = None
    flexibility: str = "unknown"
    consequence_of_shortfall: str = "unknown"
    lifecycle: str = "accumulation"


@dataclass(frozen=True)
class Fund:
    name: str
    isin: str
    category: Optional[str] = None
    benchmark: Optional[str] = None


@dataclass
class Family:
    name: str
    goals: list[Goal] = field(default_factory=list)


@dataclass
class Portfolio:
    name: str
    goal: str
    weights: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceWindow:
    start_date: date
    end_date: date
    observations: int


@dataclass(frozen=True)
class Evidence:
    fund_isin: str
    window: EvidenceWindow
    metric_name: str
    value: float
    source: str