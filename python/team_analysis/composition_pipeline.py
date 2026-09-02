"""Streaming and parallel COMPOSITION-stage analytical pipeline primitives."""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator, Mapping
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait

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
    """Yield fresh Composition fingerprints using bounded process parallelism."""
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
    max_in_flight: int | None = None,
) -> Iterator[tuple[Composition, CompositionFingerprint]]:
    """Analyze independent Composition work units with bounded process parallelism."""
    yield from _parallel_results(
        compositions,
        fund_histories,
        max_workers=max_workers,
        max_in_flight=max_in_flight,
        resilient=False,
    )


def analyze_compositions_parallel_resilient(
    compositions: Iterable[Composition],
    fund_histories: Mapping[str, pd.DataFrame],
    *,
    max_workers: int | None = None,
    max_in_flight: int | None = None,
) -> Iterator[tuple[Composition, CompositionFingerprint, Exception | None]]:
    """Analyze Composition work units while isolating individual failures.

    A failed work unit becomes an error result rather than terminating the
    entire experiment. Successful results remain independently checkpointable.
    The source iterable is consumed incrementally and only a bounded number of
    futures can be outstanding at once.
    """
    yield from _parallel_results(
        compositions,
        fund_histories,
        max_workers=max_workers,
        max_in_flight=max_in_flight,
        resilient=True,
    )


def _parallel_results(
    compositions: Iterable[Composition],
    fund_histories: Mapping[str, pd.DataFrame],
    *,
    max_workers: int | None,
    max_in_flight: int | None,
    resilient: bool,
):
    """Shared bounded-process execution engine.

    ``max_in_flight`` defaults to four times the platform's process-worker
    capacity, with a minimum of 16. This keeps the queue bounded while still
    allowing the executor's platform-appropriate default worker count to stay
    busy on larger machines.
    """
    workers = max_workers
    if workers is None:
        probe_workers = None
        detected_workers = os.process_cpu_count() or 1
        window = max(16, detected_workers * 4)
    else:
        if workers < 1:
            raise ValueError("max_workers must be at least 1")
        probe_workers = workers
        window = workers * 4

    if max_in_flight is not None:
        if max_in_flight < 1:
            raise ValueError("max_in_flight must be at least 1")
        window = max_in_flight

    source = iter(compositions)
    pending: dict = {}

    with ProcessPoolExecutor(
        max_workers=probe_workers,
        initializer=_initialize_worker,
        initargs=(dict(fund_histories),),
    ) as executor:
        exhausted = False

        def fill_window() -> None:
            nonlocal exhausted
            while not exhausted and len(pending) < window:
                try:
                    composition = next(source)
                except StopIteration:
                    exhausted = True
                    break
                future = executor.submit(_analyze_composition_worker, composition)
                pending[future] = composition

        fill_window()
        while pending:
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                composition = pending.pop(future)
                if resilient:
                    try:
                        result = future.result()
                    except Exception as exc:
                        yield composition, None, exc
                    else:
                        yield result[0], result[1], None
                else:
                    yield future.result()
            fill_window()
