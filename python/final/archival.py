"""Persist the compact FINAL summary for all Purposes as one LFS snapshot."""

from __future__ import annotations

import csv
import json
import os
from datetime import date
from pathlib import Path


SUMMARY_FILENAME = "purpose_summaries.csv"


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _atomic_write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _read_checkpoint(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid FINAL checkpoint: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid FINAL checkpoint payload: {path}")
    return payload


def archive_final_summaries(
    as_of: str,
    purpose_names: list[str] | None = None,
    *,
    output_dir: Path,
    archive_root: Path,
    final_contract_version: str,
) -> list[Path]:
    """Update the durable LFS Purpose-summary snapshot in place.

    ``archive_root`` is the LFS data directory. Generated FINAL diagnostics
    remain under ``output``; only the compact one-row-per-Purpose summary is
    persisted under ``data/lfs``. Partial runs update only their selected
    Purpose rows.
    """
    date.fromisoformat(as_of)
    summary_paths = sorted(output_dir.glob("final_*_summary.csv"))
    summaries: dict[str, Path] = {}
    for path in summary_paths:
        purpose = path.name.removeprefix("final_").removesuffix("_summary.csv")
        if purpose:
            summaries[purpose] = path

    if purpose_names is not None:
        requested = set(purpose_names)
        unknown = requested - set(summaries)
        if unknown:
            raise FileNotFoundError(
                "FINAL summary missing for requested Purpose(s): "
                + ", ".join(sorted(unknown))
            )
        summaries = {name: summaries[name] for name in sorted(requested)}
    else:
        summaries = dict(sorted(summaries.items()))

    if not summaries:
        raise FileNotFoundError(f"No FINAL summary files found in {output_dir}")

    existing_path = archive_root / SUMMARY_FILENAME
    existing = {
        row["purpose"]: row
        for row in _read_rows(existing_path)
        if row.get("purpose")
    }

    for purpose, source in summaries.items():
        rows = _read_rows(source)
        if not rows:
            raise FileNotFoundError(f"FINAL summary is empty: {source}")
        if len(rows) != 1:
            raise ValueError(f"FINAL summary must contain exactly one row: {source}")
        row = dict(rows[0])
        if row.get("purpose") != purpose:
            raise ValueError(f"FINAL summary Purpose mismatch: {source}")

        checkpoint = output_dir / f"final_{purpose}_checkpoint.json"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"FINAL checkpoint missing for {purpose}: {checkpoint}")
        checkpoint_payload = _read_checkpoint(checkpoint)
        if checkpoint_payload.get("contract_version") != final_contract_version:
            raise ValueError(
                f"FINAL checkpoint contract mismatch for {purpose}: "
                f"{checkpoint_payload.get('contract_version')!r} != {final_contract_version!r}"
            )
        if checkpoint_payload.get("purpose") != purpose:
            raise ValueError(f"FINAL checkpoint Purpose mismatch: {checkpoint}")

        existing[purpose] = {"as_of": as_of, **row}

    all_fields = ["as_of"]
    for row in existing.values():
        for key in row:
            if key not in all_fields:
                all_fields.append(key)

    rows_out = []
    for purpose in sorted(existing):
        rows_out.append({field: existing[purpose].get(field, "") for field in all_fields})

    _atomic_write(existing_path, all_fields, rows_out)
    return [existing_path]
