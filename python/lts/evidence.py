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
    """Factual LPS evidence consumed by LTS.

    The projection deliberately contains no TARGET, tax calculation,
    transition treatment, or proposal information.
    """

    positions: tuple[TransitionEvidencePosition, ...]
    transactions: tuple[Transaction, ...]
    fund_metadata: tuple[TransitionFundMetadata, ...]


def build_transition_evidence(
    positions: list[Position],
    transactions: list[Transaction],
    nav_stores: Mapping[str, NavEvidenceStore],
    valuation_as_of_date: date,
) -> TransitionEvidence:
    """Project LPS facts into the frozen Transition Evidence contract.

    Active Positions are valued using the latest persisted NAV on or before
    valuation_as_of_date. The actual NAV observation date is retained
    alongside the NAV so LTS never has to infer it from the requested
    valuation boundary.

    Zero-unit Positions remain represented, but have no valuation observation.
    Transactions are passed through as factual historical evidence and are
    never transformed into LTS actions.
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
            transactions,
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
