"""Versioned annual archival of compact FINAL production summaries."""

from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path

from lakshya_core.hashing import sha256_file

ARCHIVE_SCHEMA_VERSION = 2


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with source.open("rb") as src, temporary.open("wb") as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_write_json(path: Path, payload: dict) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _copy_working_record(source: Path, destination: Path) -> str:
    """Replace the same-date working record atomically and return its hash."""
    source_hash = sha256_file(source)
    if destination.is_file() and sha256_file(destination) == source_hash:
        return source_hash
    _atomic_copy(source, destination)
    return source_hash


def _existing_manifest(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid historical review manifest: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid historical review manifest: {path}")
    return payload


def archive_final_summaries(
    as_of: str,
    purpose_names: list[str] | None = None,
    *,
    output_dir: Path,
    archive_root: Path,
    final_contract_version: str,
) -> list[Path]:
    """Update the same-date annual review snapshot in place.

    The dated directory is a working annual snapshot until the resulting
    review state is committed to Git. Repeated runs therefore replace the
    same summary files rather than creating versioned copies. ``working_revision``
    increments when the snapshot content changes and remains stable for an
    identical rerun. Existing purposes not selected by a partial run remain
    in the working manifest.
    """
    try:
        parsed_date = date.fromisoformat(as_of)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid review date: {as_of!r}") from None
    if parsed_date.isoformat() != as_of:
        raise ValueError(f"Invalid review date: {as_of!r}")

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

    # Validate every selected source and its FINAL checkpoint before changing
    # the working snapshot. This prevents a bad partial run from creating a
    # half-valid review state.
    prepared: list[tuple[str, Path, dict, str]] = []
    for purpose, source in summaries.items():
        checkpoint = output_dir / f"final_{purpose}_checkpoint.json"
        if not checkpoint.is_file():
            raise FileNotFoundError(
                f"FINAL checkpoint missing for {purpose}: {checkpoint}"
            )
        try:
            checkpoint_payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError(f"Invalid FINAL checkpoint for {purpose}: {checkpoint}") from exc
        if checkpoint_payload.get("contract_version") != final_contract_version:
            raise ValueError(
                f"FINAL checkpoint contract mismatch for {purpose}: "
                f"expected {final_contract_version!r}, "
                f"got {checkpoint_payload.get('contract_version')!r}"
            )
        prepared.append((purpose, source, checkpoint_payload, sha256_file(source)))

    review_dir = archive_root / as_of
    manifest_path = review_dir / "review_manifest.json"
    existing = _existing_manifest(manifest_path)
    existing_purposes = {
        item["purpose"]: item
        for item in (existing or {}).get("purposes", [])
        if isinstance(item, dict) and item.get("purpose")
    }

    # Build the new selected records while retaining other purposes already in
    # the same annual working snapshot. A partial Purpose run must not erase
    # unrelated Purpose records.
    merged_purposes = dict(existing_purposes)
    for purpose, _, checkpoint_payload, summary_hash in prepared:
        merged_purposes[purpose] = {
            "purpose": purpose,
            "summary_file": f"{purpose}_summary.csv",
            "summary_sha256": summary_hash,
            "final_contract_version": final_contract_version,
            "mission_sha256": checkpoint_payload.get("mission_sha256"),
            "purpose_horizon_years": checkpoint_payload.get("purpose_horizon_years"),
            "bootstrap_resamples": checkpoint_payload.get("bootstrap_resamples"),
            "bootstrap_seed": checkpoint_payload.get("bootstrap_seed"),
        }

    manifest_purposes = [merged_purposes[name] for name in sorted(merged_purposes)]
    base_manifest = {
        "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
        "as_of": as_of,
        "final_contract_version": final_contract_version,
        "purposes": manifest_purposes,
    }

    # Determine whether this invocation actually changes the working snapshot.
    # An identical rerun remains idempotent and does not consume another
    # working revision.
    existing_base = None
    if existing is not None:
        existing_base = dict(existing)
        existing_base.pop("working_revision", None)
    changed = existing_base != base_manifest
    revision = int((existing or {}).get("working_revision", 0)) + (1 if changed else 0)
    manifest = dict(base_manifest)
    manifest["working_revision"] = revision

    archived: list[Path] = []
    for purpose, source, _, _ in prepared:
        destination = review_dir / f"{purpose}_summary.csv"
        _copy_working_record(source, destination)
        archived.append(destination)
    _atomic_write_json(manifest_path, manifest)
    return archived
