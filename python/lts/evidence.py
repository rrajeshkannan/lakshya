"""LPS -> LTS Transition Evidence projection.

This module exposes only the factual evidence LTS is currently entitled to
consume. It does not alter LPS Position state or introduce transition
decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from lps.nav_evidence import NavEvidenceStore
from lps.positions import Position, PositionId
from lps.transactions import Transaction
from lts.fund_metadata import TransitionFundMetadata, project_fund_metadata


@dataclass(frozen=True)
class TransitionEvidencePosition:
    """LPS Position projected for LTS with factual NAV observation date."""

    id: PositionId
    units: Decimal
    nav: Decimal | None
    nav_observation_date: date | None
    market_value: Decimal | None
    purpose: str | None


@dataclass(frozen=True)
class TransitionEvidence:
    """Factual LPS evidence consumed by LTS."""

    positions: tuple[TransitionEvidencePosition, ...]
    transactions: tuple[Transaction, ...]
    fund_metadata: tuple[TransitionFundMetadata, ...]


def build_transition_evidence(
    positions: list[Position],
    transactions: list[Transaction],
    nav_stores: Mapping[str, NavEvidenceStore],
    valuation_as_of_date: date,
) -> TransitionEvidence:
    """Project LPS facts using one authoritative ``as_of`` boundary.

    The same valuation boundary controls NAV observation and the historical
    transaction set. Transactions after ``valuation_as_of_date`` are not
    available to lock-in analysis for that run.
    """
    projected: list[TransitionEvidencePosition] = []

    for position in sorted(
        positions,
        key=lambda p: (p.id.investor, p.id.folio, p.id.isin),
    ):
        if position.units == 0:
            projected.append(
                TransitionEvidencePosition(
                    id=position.id,
                    units=position.units,
                    nav=None,
                    nav_observation_date=None,
                    market_value=None,
                    purpose=position.purpose,
                )
            )
            continue

        try:
            store = nav_stores[position.id.isin]
        except KeyError as exc:
            raise KeyError(
                f"No NAV evidence store for ISIN {position.id.isin}"
            ) from exc

        observation_timestamp, nav = store.as_of(valuation_as_of_date)
        nav_decimal = Decimal(str(nav))
        projected.append(
            TransitionEvidencePosition(
                id=position.id,
                units=position.units,
                nav=nav_decimal,
                nav_observation_date=observation_timestamp.date(),
                market_value=position.units * nav_decimal,
                purpose=position.purpose,
            )
        )

    ordered_isins = sorted({position.id.isin for position in positions})
    fund_metadata = tuple(
        project_fund_metadata(isin, nav_stores[isin].scheme_metadata())
        for isin in ordered_isins
        if isin in nav_stores
    )
    ordered_transactions = tuple(
        sorted(
            (
                transaction
                for transaction in transactions
                if transaction.transaction_date <= valuation_as_of_date
            ),
            key=lambda transaction: (
                transaction.transaction_date,
                transaction.investor,
                transaction.folio,
                transaction.isin,
                transaction.event_type,
                transaction.source_description,
            ),
        )
    )

    return TransitionEvidence(
        positions=tuple(projected),
        transactions=ordered_transactions,
        fund_metadata=fund_metadata,
    )


__all__ = [
    "TransitionEvidence",
    "TransitionEvidencePosition",
    "build_transition_evidence",
]
