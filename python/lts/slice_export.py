"""Human-readable export of materialized LTS slices."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from .slice_materialization import MaterializedSlice


def export_materialized_slices_csv(
    slices: tuple[MaterializedSlice, ...] | list[MaterializedSlice],
) -> str:
    """Return a deterministic CSV representation of materialized slices."""
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "investor",
            "folio",
            "isin",
            "slice",
            "source_investor",
            "source_folio",
            "source_isin",
            "source_slice",
            "destination_isin",
            "purpose",
            "disposition",
            "locked",
            "percentage",
            "units",
            "nav",
            "market_value",
            "source_amount",
            "ownership_source",
        ]
    )

    for item in slices:
        writer.writerow(
            [
                item.id.investor,
                item.id.folio,
                item.id.isin,
                item.id.slice,
                item.source_position_id.investor,
                item.source_position_id.folio,
                item.source_position_id.isin,
                item.source_position_id.slice,
                item.destination_isin,
                item.purpose,
                item.disposition.value,
                str(item.locked).lower(),
                format(item.percentage, "f"),
                format(item.units, "f"),
                "" if item.nav is None else format(item.nav, "f"),
                format(item.market_value, "f"),
                format(item.source_amount, "f"),
                item.ownership_source,
            ]
        )

    return output.getvalue()


def write_materialized_slices_csv(
    slices: tuple[MaterializedSlice, ...] | list[MaterializedSlice],
    destination: Path,
) -> None:
    """Write materialized slices to a caller-selected path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(export_materialized_slices_csv(slices), encoding="utf-8")


__all__ = ["export_materialized_slices_csv", "write_materialized_slices_csv"]
