"""[lakshya] Tests for streaming TEAM candidate analysis."""

from lakshya_core.models import Fund
from team_analysis.pipeline import stream_team_fingerprints


def fund(isin: str) -> Fund:
    return Fund(name=isin, isin=isin)


def test_team_pipeline_streams_every_singleton_pair_and_trio():
    seen = []

    def build_fingerprint(team):
        seen.append(team)
        return tuple(member.isin for member in team.members)

    result = list(stream_team_fingerprints(
        [fund("C"), fund("A"), fund("B")],
        build_fingerprint,
    ))

    assert result == [
        ("A",), ("B",), ("C",),
        ("A", "B"), ("A", "C"), ("B", "C"),
        ("A", "B", "C"),
    ]
    assert len(seen) == 7


def test_team_pipeline_is_lazy():
    calls = []

    def build_fingerprint(team):
        calls.append(team)
        return team

    stream = stream_team_fingerprints([fund("A"), fund("B")], build_fingerprint)

    assert calls == []
    next(stream)
    assert len(calls) == 1


def test_team_pipeline_does_not_require_persisting_candidate_universe():
    def funds():
        yield fund("A")
        yield fund("B")
        yield fund("C")

    result = list(stream_team_fingerprints(funds(), lambda team: tuple(m.isin for m in team.members)))

    assert len(result) == 7
