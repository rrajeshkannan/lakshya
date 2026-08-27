"""[lakshya] Tests for the TEAM candidate universe."""

from lakshya_core.models import Fund
from team_analysis.candidate_generator import generate_team_candidates


def fund(isin: str) -> Fund:
    return Fund(name=isin, isin=isin)


def signatures(funds):
    return [tuple(member.isin for member in team.members) for team in generate_team_candidates(funds)]


def test_generates_singletons_pairs_and_trios_exactly_once():
    result = signatures([fund("C"), fund("A"), fund("B")])

    assert result == [
        ("A",),
        ("B",),
        ("C",),
        ("A", "B"),
        ("A", "C"),
        ("B", "C"),
        ("A", "B", "C"),
    ]


def test_candidate_count_matches_mathematical_universe():
    funds = [fund(chr(ord("A") + i)) for i in range(5)]
    candidates = list(generate_team_candidates(funds))

    # C(5,1) + C(5,2) + C(5,3) = 5 + 10 + 10 = 25
    assert len(candidates) == 25


def test_member_order_of_input_does_not_create_duplicates():
    forward = signatures([fund("A"), fund("B"), fund("C")])
    reverse = signatures([fund("C"), fund("B"), fund("A")])

    assert forward == reverse


def test_empty_and_small_universes():
    assert signatures([]) == []
    assert signatures([fund("A")]) == [("A",)]
    assert signatures([fund("A"), fund("B")]) == [
        ("A",),
        ("B",),
        ("A", "B"),
    ]


def test_four_funds_do_not_produce_quads():
    result = signatures([fund("A"), fund("B"), fund("C"), fund("D")])

    assert all(len(team) <= 3 for team in result)
    assert ("A", "B", "C", "D") not in result


def test_duplicate_fund_is_rejected():
    funds = [fund("A"), fund("A")]

    try:
        list(generate_team_candidates(funds))
    except ValueError as exc:
        assert "unique ISINs" in str(exc)
    else:
        raise AssertionError("Duplicate Fund should have been rejected")
