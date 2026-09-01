"""Streaming and parallel COMPOSITION-stage analytical pipeline primitives."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from .analyze_composition import analyze_composition
from .composition import Composition
from .composition_fingerprint import CompositionFingerprint
from .generate_compositions import generate_compositions
from .team import Team

_WORKER_HISTORIES: dict[str, pd.DataFrame] | None = None


def stream_composition_fingerprints(
    teams: Iterable[Team],
    fund_histories: Mapping[str, pd.DataFrame],
) -> Iterator[tuple[Composition, CompositionFingerprint]]:
    """Yield Composition identity and fresh fingerprint one candidate at a time.

    The supplied Teams are assumed to have already passed the TEAM-stage gate.
    Composition generation and analysis are derived from those admitted Teams;
    no Team-level behavioural evidence is inherited by a Composition.
    """
    for team in teams:
        for composition in generate_compositions(team):
            histories = {
                member.isin: fund_histories[member.isin]
                for member in team.members
            }
            yield composition, analyze_composition(composition, histories)


def _initialize_worker(histories: Mapping[str, pd.DataFrame]) -> None:
    global _WORKER_HISTORIES
    _WORKER_HISTORIES = dict(histories)


def _analyze_composition_worker(
    composition: Composition,
) -> tuple[Composition, CompositionFingerprint]:
    if _WORKER_HISTORIES is None:
        raise RuntimeError("Composition worker was not initialized with NAV histories.")
    histories = {
        member.isin: _WORKER_HISTORIES[member.isin]
        for member in composition.team.members
    }
    return composition, analyze_composition(composition, histories)


def stream_composition_fingerprints_parallel(
    teams: Iterable[Team],
    fund_histories: Mapping[str, pd.DataFrame],
    *,
    max_workers: int | None = None,
) -> Iterator[tuple[Composition, CompositionFingerprint]]:
    """Yield fresh Composition fingerprints using process-level parallelism.

    ``max_workers=None`` deliberately delegates worker sizing to Python's
    ProcessPoolExecutor.  The caller can override it when an experiment needs
    an explicit resource envelope.

    Results are yielded as workers complete, so callers can persist each
    completed fingerprint immediately instead of accumulating a giant list.
    """
    compositions = (
        composition
        for team in teams
        for composition in generate_compositions(team)
    )
    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=_initialize_worker,
        initargs=(dict(fund_histories),),
    ) as executor:
        yield from executor.map(_analyze_composition_worker, compositions, chunksize=1)
