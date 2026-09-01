"""Streaming and parallel COMPOSITION-stage analytical pipeline primitives."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from .analyze_composition import analyze_composition
from .composition import Composition, composition_identity
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
    """Yield fresh Composition fingerprints using process-level parallelism."""
    compositions = (
        composition
        for team in teams
        for composition in generate_compositions(team)
    )
    yield from analyze_compositions_parallel(
        compositions,
        fund_histories,
        max_workers=max_workers,
    )


def analyze_compositions_parallel(
    compositions: Iterable[Composition],
    fund_histories: Mapping[str, pd.DataFrame],
    *,
    max_workers: int | None = None,
) -> Iterator[tuple[Composition, CompositionFingerprint]]:
    """Analyze independent Composition work units in parallel.

    Results are yielded as workers complete.  The caller therefore controls
    persistence and can checkpoint each result immediately.
    """
    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=_initialize_worker,
        initargs=(dict(fund_histories),),
    ) as executor:
        yield from executor.map(_analyze_composition_worker, compositions, chunksize=1)


def analyze_compositions_parallel_resilient(
    compositions: Iterable[Composition],
    fund_histories: Mapping[str, pd.DataFrame],
    *,
    max_workers: int | None = None,
) -> Iterator[tuple[Composition, CompositionFingerprint, Exception | None]]:
    """Analyze Composition work units while isolating individual failures.

    A failed work unit becomes an error result rather than terminating the
    entire experiment.  Successful results remain independently checkpointable.
    """
    from concurrent.futures import as_completed

    composition_list = list(compositions)
    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=_initialize_worker,
        initargs=(dict(fund_histories),),
    ) as executor:
        futures = {
            executor.submit(_analyze_composition_worker, composition): composition
            for composition in composition_list
        }
        for future in as_completed(futures):
            composition = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                yield composition, None, exc
            else:
                yield result[0], result[1], None
