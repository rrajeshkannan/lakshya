"""Versioned annual archival of compact FINAL production summaries."""

from __future__ import annotations

from datetime import date
import hashlib
import json
import os
from pathlib import Path

ARCHIVE_SCHEMA_VERSION = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _write_json_if_same_or_absent(path: Path, payload: dict) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if existing != encoded:
            raise FileExistsError(
                f"Historical review manifest already exists with different content: {path}"
            )
        return
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


def _copy_if_same_or_absent(source: Path, destination: Path) -> str:
    source_hash = _sha256(source)
    if destination.is_file():
        destination_hash = _sha256(destination)
        if destination_hash != source_hash:
            raise FileExistsError(
                f"Historical review record already exists with different content: {destination}"
            )
        return destination_hash
    _atomic_copy(source, destination)
    return source_hash


def archive_final_summaries(
    as_of: str,
    purpose_names: list[str] | None = None,
    *,
    output_dir: Path,
    archive_root: Path,
    final_contract_version: str,
) -> list[Path]:
    """Archive configured FINAL summaries into an immutable dated review record.

    Existing records are idempotent when their content is byte-for-byte
    identical. A conflicting record fails rather than overwriting history.
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

    # Validate every source and its FINAL checkpoint before writing any archive
    # files. This prevents a partially created historical record on bad input.
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
        prepared.append((purpose, source, checkpoint_payload, _sha256(source)))

    review_dir = archive_root / as_of
    manifest_purposes = [
        {
            "purpose": purpose,
            "summary_file": f"{purpose}_summary.csv",
            "summary_sha256": summary_hash,
            "final_contract_version": final_contract_version,
            "mission_sha256": checkpoint_payload.get("mission_sha256"),
            "purpose_horizon_years": checkpoint_payload.get("purpose_horizon_years"),
            "bootstrap_resamples": checkpoint_payload.get("bootstrap_resamples"),
            "bootstrap_seed": checkpoint_payload.get("bootstrap_seed"),
        }
        for purpose, _, checkpoint_payload, summary_hash in prepared
    ]
    manifest = {
        "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
        "as_of": as_of,
        "final_contract_version": final_contract_version,
        "purposes": manifest_purposes,
    }

    # Preflight all existing destinations before changing the archive. This
    # keeps a conflicting historical record from producing a partial update.
    for purpose, source, _, summary_hash in prepared:
        destination = review_dir / f"{purpose}_summary.csv"
        if destination.is_file() and _sha256(destination) != summary_hash:
            raise FileExistsError(
                f"Historical review record already exists with different content: {destination}"
            )
    manifest_path = review_dir / "review_manifest.json"
    if manifest_path.is_file():
        existing_manifest = manifest_path.read_text(encoding="utf-8")
        expected_manifest = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        if existing_manifest != expected_manifest:
            raise FileExistsError(
                f"Historical review manifest already exists with different content: {manifest_path}"
            )

    archived: list[Path] = []
    for purpose, source, _, _ in prepared:
        destination = review_dir / f"{purpose}_summary.csv"
        _copy_if_same_or_absent(source, destination)
        archived.append(destination)
    _write_json_if_same_or_absent(manifest_path, manifest)
    return archived
