"""[lakshya] Streaming TEAM analytical pipeline primitives."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from .candidate_generator import generate_team_candidates


def stream_team_fingerprints(
    funds: Iterable[object],
    build_fingerprint: Callable[[object], object],
) -> Iterator[object]:
    """Build Team fingerprints one candidate at a time.

    [lakshya] Candidate Teams are never accumulated merely for the purpose of
    generating fingerprints. The caller decides how the resulting evidence is
    consumed or persisted.
    """
    for team in generate_team_candidates(funds):
        yield build_fingerprint(team)
