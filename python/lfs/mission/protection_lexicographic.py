"""Experimental MISSION Protection sequencing.

This is deliberately a sequencing instrument, not a Protection score or
selection rule. The ladder is provisional and exists to test whether the
strongest observed severity distinctions usefully reduce the Composition
candidate space after Elevation qualification.
"""

from __future__ import annotations

from functools import cmp_to_key
from typing import Mapping, Sequence


# Provisional Layer-1 ladder: strongest observed severity distinctions first.
# Lower values are better because every metric describes adverse severity.
PROTECTION_SEVERITY_LADDER = (
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


def _compare(a: Mapping[str, float], b: Mapping[str, float], ladder: Sequence[str]) -> int:
    """Compare two candidates conservatively when evidence is unavailable.

    A missing value is unknown, never zero and never better/worse. Therefore
    a metric can establish an ordering only when both candidates have an
    observed value for that metric. If either side is unavailable, the ladder
    moves on without claiming a distinction from that metric.
    """
    for metric in ladder:
        av = a.get(metric)
        bv = b.get(metric)
        if av is None or bv is None:
            continue
        if av < bv:
            return -1
        if av > bv:
            return 1
    return 0


def protection_lexicographic_order(
    candidates: Sequence[Mapping[str, float]],
    ladder: Sequence[str] = PROTECTION_SEVERITY_LADDER,
) -> list[Mapping[str, float]]:
    """Order candidates from lower to higher observed Protection severity.

    Equal or unresolved candidates remain tied through the entire ladder.
    The function does not eliminate candidates and does not claim that the
    resulting order is a decision rule; it only exposes whether the
    provisional ladder creates useful distinctions.
    """
    return sorted(
        candidates,
        key=cmp_to_key(lambda a, b: _compare(a, b, ladder)),
    )
