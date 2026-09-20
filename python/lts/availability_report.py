"""Build reviewer-facing holding availability from Transition Evidence."""

from __future__ import annotations

from datetime import date
from typing import Mapping

from lps.positions import Position

from .evidence import TransitionEvidence
from .holding_availability import HoldingAvailability, summarize_holding_availability
from .holding_constraints import HoldingTaxConstraint, analyze_holding


def build_holding_availability_report(
    evidence: TransitionEvidence,
    as_of: date,
    constraints: Mapping[str, HoldingTaxConstraint],
) -> tuple[HoldingAvailability, ...]:
    """Build availability summaries for all non-zero evidence positions.

    Constraints are supplied explicitly by the caller. This function does not
    infer tax rules from fund names or metadata, and it does not produce or
    execute a transition proposal.
    """
    reports: list[HoldingAvailability] = []

    for projected in evidence.positions:
        if projected.units == 0:
            continue

        try:
            constraint = constraints[projected.id.isin]
        except KeyError as exc:
            raise KeyError(
                f"No holding constraint supplied for ISIN {projected.id.isin}"
            ) from exc

        position = Position(
            id=projected.id,
            units=projected.units,
            nav=projected.nav,
            market_value=projected.market_value,
            purpose=projected.purpose,
        )
        analysis = analyze_holding(
            position=position,
            transactions=evidence.transactions,
            as_of=as_of,
            constraint=constraint,
        )
        reports.append(summarize_holding_availability(analysis))

    return tuple(
        sorted(
            reports,
            key=lambda report: (
                report.holding_id.investor,
                report.holding_id.folio,
                report.holding_id.isin,
            ),
        )
    )


__all__ = ["build_holding_availability_report"]
