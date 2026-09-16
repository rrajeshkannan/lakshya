"""Historical Position snapshot formation owned by LFS.

LFS formation is evaluated at one explicit boundary.  This adapter turns
LPS transaction and NAV evidence into the Position state applicable at that
boundary, while preserving the accepted Purpose attribution already carried
by the established LPS Position state.

The resulting Position collection is intentionally ordinary LPS Position
objects.  Downstream MISSION code therefore consumes derived capital through
its existing Purpose-capital projection instead of learning valuation rules.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

from lps.nav_evidence import NavEvidenceStore
from lps.positions import Position, reconstruct_positions
from lps.transactions import Transaction
from lps.valuation import value_positions


def build_positions_as_of(
    transactions: Sequence[Transaction],
    current_positions: Sequence[Position],
    *,
    formation_as_of: date,
    nav_dir: Path,
) -> list[Position]:
    """Form the factual Position snapshot applicable at ``formation_as_of``.

    Units come only from transactions dated on or before the formation
    boundary.  NAV and market value are observed at the same boundary using
    the latest recorded NAV on or before that date.  Purpose attribution is
    carried from the accepted current Position state because LPS does not yet
    persist effective-dated Purpose attribution history.
    """
    through = [
        transaction
        for transaction in transactions
        if transaction.transaction_date <= formation_as_of
    ]
    positions = reconstruct_positions(list(through))

    purpose_by_id = {
        position.id: position.purpose
        for position in current_positions
        if position.purpose
    }
    attributed = [
        Position(
            id=position.id,
            units=position.units,
            purpose=purpose_by_id.get(position.id),
        )
        for position in positions
    ]

    nav_stores: Mapping[str, NavEvidenceStore] = {
        position.id.isin: NavEvidenceStore(nav_dir / f"{position.id.isin}.json")
        for position in attributed
        if position.units != 0
    }
    return value_positions(attributed, nav_stores, formation_as_of)


__all__ = ["build_positions_as_of"]
