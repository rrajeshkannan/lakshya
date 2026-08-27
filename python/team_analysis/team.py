"""TEAM domain identity."""

from __future__ import annotations

from dataclasses import dataclass

from lakshya_core.models import Fund


@dataclass(frozen=True)
class Team:
    """An ordered-independent collective of one to three Funds.

    Team identity contains membership only. Behavioural evidence is
    calculated separately from the collective NAV trajectory.
    """

    members: tuple[Fund, ...]

    def __post_init__(self) -> None:
        if not 1 <= len(self.members) <= 3:
            raise ValueError("A Team must contain between 1 and 3 Funds.")

        isins = [fund.isin for fund in self.members]
        if len(isins) != len(set(isins)):
            raise ValueError("A Team cannot contain the same Fund more than once.")

        canonical = tuple(sorted(self.members, key=lambda fund: fund.isin))
        if self.members != canonical:
            raise ValueError("Team members must be in canonical ISIN order.")

    @property
    def cardinality(self) -> int:
        return len(self.members)

    @property
    def is_singleton(self) -> bool:
        return self.cardinality == 1

    @property
    def is_pair(self) -> bool:
        return self.cardinality == 2

    @property
    def is_trio(self) -> bool:
        return self.cardinality == 3
