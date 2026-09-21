"""Human-readable exports and persistence for transition mappings."""

from __future__ import annotations

import csv
from decimal import Decimal
from io import StringIO
from pathlib import Path

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


def write_transition_mapping_csv(
    plan: PurposeTransitionPlan,
    destination: Path,
) -> None:
    """Write a selected transition mapping export to a caller-chosen path.

    The caller decides whether the destination belongs to temporary run output
    or to a deliberately retained temporal artifact under ``data/lts``.
    Parent directories are created when needed.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(export_transition_mapping_csv(plan), encoding="utf-8")


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


__all__ = ["export_transition_mapping_csv", "write_transition_mapping_csv"]
