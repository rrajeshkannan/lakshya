"""Run bootstrap and input preparation for the resilient pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any

import pandas as pd


@dataclass(frozen=True)
class RunInputs:
    valuation_date: pd.Timestamp
    funds: list[Any]
    histories: Any
    purposes: list[Any]
    funds_by_isin: dict[str, Any]


@dataclass(frozen=True)
class RunInputDeps:
    load_admissible_funds: Callable[[], list[Any]]
    load_fund_histories: Callable[..., Any]
    load_purposes: Callable[..., list[Any]]
    nav_dir: Any
    log: Callable[[str], None]
    detail: Callable[[str], None]


class RunInputStage:
    """Load and validate the runtime inputs needed by resume or full execution."""

    def __init__(self, deps: RunInputDeps):
        self._deps = deps

    def prepare(self, as_of: str, purpose_names: list[str] | None = None) -> RunInputs:
        valuation_date = pd.Timestamp(as_of)
        funds = self._deps.load_admissible_funds()
        histories = self._deps.load_fund_histories(
            funds,
            nav_dir=self._deps.nav_dir,
            as_of=valuation_date,
            log=self._deps.log,
            detail=self._deps.detail,
        )
        purposes = self._deps.load_purposes(valuation_date.date())

        if purpose_names is not None:
            requested = set(purpose_names)
            known = {purpose.name for purpose in purposes}
            unknown = requested - known
            if unknown:
                raise ValueError(
                    f"Unknown Purpose(s): {sorted(unknown)}; "
                    f"available={sorted(known)}"
                )
            purposes = [purpose for purpose in purposes if purpose.name in requested]
            self._deps.log("Selected purposes: " + ", ".join(purpose.name for purpose in purposes))
            self._deps.detail("PURPOSE_SELECTION " + " ".join(purpose.name for purpose in purposes))

        funds_by_isin = {fund.isin: fund for fund in funds}
        self._deps.detail(f"INPUTS_READY funds={len(funds)} purposes={len(purposes)}")

        return RunInputs(
            valuation_date=valuation_date,
            funds=funds,
            histories=histories,
            purposes=purposes,
            funds_by_isin=funds_by_isin,
        )
