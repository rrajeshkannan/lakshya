"""Human-readable exports and persistence for transition mappings."""

from __future__ import annotations

import csv
from decimal import Decimal
from io import StringIO
from pathlib import Path

from .purpose_transition import PurposeTransitionPlan

DEFAULT_TEMPORAL_ROOT = Path("data/lts")


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


def persist_transition_mapping_csv(
    plan: PurposeTransitionPlan,
    *,
    as_of: str,
    run_id: str,
    root: Path = DEFAULT_TEMPORAL_ROOT,
) -> Path:
    """Persist a selected transition mapping as a temporal artifact.

    The default location is ``data/lts/transition_mappings``. The caller must
    provide the run identity and as-of date so the artifact remains attributable
    to a specific analytical run. This writes only the selected CSV; it does
    not imply human acceptance of the broader Historical Snapshot.
    """
    if not as_of.strip() or not run_id.strip():
        raise ValueError("as_of and run_id must be non-blank.")
    if Path(as_of).name != as_of or Path(run_id).name != run_id:
        raise ValueError("as_of and run_id must be single path-safe components.")

    destination = root / "transition_mappings" / f"{as_of}_{run_id}.csv"
    write_transition_mapping_csv(plan, destination)
    return destination


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


__all__ = [
    "DEFAULT_TEMPORAL_ROOT",
    "export_transition_mapping_csv",
    "persist_transition_mapping_csv",
    "write_transition_mapping_csv",
]
