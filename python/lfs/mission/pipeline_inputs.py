"""Input-boundary helpers for the resilient Lakshya pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from lakshya_core.nav_history import cutoff_nav_history

Log = Callable[[str], None]


def load_fund_histories(
    funds: Iterable[object],
    *,
    nav_dir: Path,
    as_of: pd.Timestamp,
    log: Log | None = None,
    detail: Log | None = None,
) -> dict[str, pd.DataFrame]:
    """Load one persisted NAV JSON document per fund through ``as_of``.

    This helper owns only the NAV input boundary. It deliberately does not
    know about manifests, checkpoints, workers, or downstream pipeline stages.
    Each fund is expected to expose an ``isin`` attribute, and each JSON file
    is expected to contain an ``observations`` list.
    """
    funds = list(funds)
    histories: dict[str, pd.DataFrame] = {}
    if log is not None:
        log(f"Loading NAV histories for {len(funds)} admitted funds through {as_of.date()}")
    if detail is not None:
        detail(f"NAV_LOAD_START funds={len(funds)} as_of={as_of.date()}")

    for index, fund in enumerate(funds, start=1):
        isin = str(fund.isin)
        path = nav_dir / f"{isin}.json"
        if log is not None:
            log(f"  NAV {index}/{len(funds)}: {isin}")
        if detail is not None:
            detail(
                f"NAV_LOAD_START index={index} total={len(funds)} "
                f"isin={isin} path={path} as_of={as_of.date()}"
            )
        if not path.exists():
            if detail is not None:
                detail(f"NAV_LOAD_FAILED isin={isin} reason=missing_file path={path}")
            raise FileNotFoundError(f"Missing NAV evidence for {isin}: {path}")

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        observations = payload.get("observations")
        if not isinstance(observations, list):
            if detail is not None:
                detail(f"NAV_LOAD_FAILED isin={isin} reason=invalid_observations")
            raise ValueError(f"Invalid NAV evidence observations: {path}")

        histories[isin] = cutoff_nav_history(pd.DataFrame(observations), as_of)
        if detail is not None:
            detail(f"NAV_READY isin={isin} rows={len(histories[isin])} as_of={as_of.date()}")

    if detail is not None:
        detail(f"NAV_LOAD_COMPLETE funds={len(histories)} as_of={as_of.date()}")
    return histories
