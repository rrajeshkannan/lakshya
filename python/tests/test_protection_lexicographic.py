from __future__ import annotations

from mission.protection_lexicographic import (
    PROTECTION_SEVERITY_LADDER,
    protection_lexicographic_order,
)


def _candidate(name: str, **values: float):
    return {"name": name, **values}


def test_strongest_severity_distinction_gets_priority():
    a = _candidate(
        "A",
        protection_maximum_severity_pct=20,
        protection_percentile_99_severity_pct=18,
    )
    b = _candidate(
        "B",
        protection_maximum_severity_pct=25,
        protection_percentile_99_severity_pct=10,
    )

    ordered = protection_lexicographic_order([b, a])

    assert [candidate["name"] for candidate in ordered] == ["A", "B"]


def test_next_ladder_level_is_used_only_when_stronger_level_ties():
    a = _candidate(
        "A",
        protection_maximum_severity_pct=20,
        protection_percentile_99_severity_pct=10,
    )
    b = _candidate(
        "B",
        protection_maximum_severity_pct=20,
        protection_percentile_99_severity_pct=15,
    )

    ordered = protection_lexicographic_order([b, a])

    assert [candidate["name"] for candidate in ordered] == ["A", "B"]


def test_complete_tie_remains_a_tie_and_input_order_is_preserved():
    a = _candidate("A", protection_maximum_severity_pct=20)
    b = _candidate("B", protection_maximum_severity_pct=20)

    ordered = protection_lexicographic_order([b, a], ladder=("protection_maximum_severity_pct",))

    assert [candidate["name"] for candidate in ordered] == ["B", "A"]


def test_provisional_ladder_covers_current_protection_severity_surface():
    assert PROTECTION_SEVERITY_LADDER == (
        "protection_maximum_severity_pct",
        "protection_percentile_99_severity_pct",
        "protection_percentile_95_severity_pct",
        "protection_percentile_90_severity_pct",
        "protection_percentile_75_severity_pct",
        "protection_median_severity_pct",
        "protection_pct_days_at_or_above_30",
        "protection_pct_days_at_or_above_25",
        "protection_pct_days_at_or_above_20",
        "protection_pct_days_at_or_above_15",
        "protection_pct_days_at_or_above_10",
        "protection_pct_days_at_or_above_5",
    )
