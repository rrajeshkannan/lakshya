"""Human-readable exports for conservation-balanced transition mappings."""

from __future__ import annotations

import csv
from io import StringIO
from decimal import Decimal

from .purpose_transition import PurposeTransitionPlan


def export_transition_mapping_csv(plan: PurposeTransitionPlan) -> str:
    """Return a deterministic CSV representation of every mapping edge.

    The export is analytical evidence only. It does not calculate tax, execute
    transactions, or alter the supplied transition plan.
    """
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "purpose",
            "source_position_id",
            "source_isin",
            "source_kind",
            "destination_isin",
            "amount",
            "locked",
        ]
    )

    for mapping in plan.mappings:
        writer.writerow(
            [
                mapping.purpose,
                str(mapping.source_position_id),
                mapping.source_isin,
                mapping.source_kind.value,
                mapping.destination_isin,
                _decimal_text(mapping.amount),
                str(mapping.locked).lower(),
            ]
        )

    return output.getvalue()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


__all__ = ["export_transition_mapping_csv"]
