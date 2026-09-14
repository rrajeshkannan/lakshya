"""Composition candidate and fingerprint-evidence stage.

The stage owns candidate materialization and durable Composition fingerprint
evidence. Runtime services are supplied through ``CompositionEvidenceDeps``
so the resilient runner remains a coordinator rather than the implementation
owner.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import csv
import time


@dataclass(frozen=True)
class CompositionEvidenceDeps:
    output_dir: Path
    project_root: Path
    fingerprint_dir: Path
    checkpoint_index_path: Path
    input_hash: Callable[[Path], str]
    load_checkpoint_index: Callable[..., dict]
    publish_checkpoint_index: Callable[..., None]
    checkpoint_metadata: Callable[[Path], dict | None]
    has_fingerprint: Callable[..., bool]
    fingerprint_path: Callable[..., Path]
    composition_identity: Callable[..., str]
    generate_compositions: Callable[..., Any]
    analyze_compositions_parallel_resilient: Callable[..., Any]
    persist_fingerprint: Callable[..., Path]
    log: Callable[[str], None]
    detail: Callable[[str], None]
    manifest_update: Callable[..., None]


class CompositionEvidenceStage:
    def __init__(self, deps: CompositionEvidenceDeps):
        self.d = deps

    def write_candidates(self, teams) -> int:
        path = self.d.output_dir / "composition_candidates.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        count = 0
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=("composition", "team"))
            writer.writeheader()
            for team in teams:
                for composition in self.d.generate_compositions(team):
                    writer.writerow(
                        {
                            "composition": self.d.composition_identity(composition),
                            "team": "|".join(member.isin for member in composition.team.members),
                        }
                    )
                    count += 1
        temporary.replace(path)
        self.d.log(f"  wrote {path.relative_to(self.d.project_root)} ({count} rows)")
        self.d.detail(f"COMPOSITION_CANDIDATES_WRITTEN path={path.relative_to(self.d.project_root)} rows={count}")
        return count


    def candidate_compositions(self, teams):
        for team in teams:
            yield from self.d.generate_compositions(team)



    def scan_checkpoints(self, teams) -> tuple[int, int, list[Composition], dict[str, dict[str, int]], str]:
        """Scan Composition checkpoints using the durable index as a narrow cache.

        The index can accelerate only metadata matches. Every miss, stale entry,
        malformed entry, or changed file falls back to authoritative validation via
        self.d.has_fingerprint(). The returned entries are published only after all missing
        Composition work has successfully persisted.
        """
        candidates_sha256 = self.d.input_hash(self.d.output_dir / "composition_candidates.csv")
        indexed_entries = self.d.load_checkpoint_index(self.d.checkpoint_index_path, candidates_sha256)
        index_reusable = bool(indexed_entries)
        total = existing = 0
        missing_compositions: list[Composition] = []
        valid_entries: dict[str, dict[str, int]] = {}
        indexed_hits = authoritative_checks = 0

        for composition in candidate_compositions(teams):
            total += 1
            identity = self.d.composition_identity(composition)
            path = self.d.fingerprint_path(self.d.fingerprint_dir, composition)
            metadata = self.d.checkpoint_metadata(path)
            indexed_metadata = indexed_entries.get(identity) if index_reusable else None
            if metadata is not None and indexed_metadata == metadata:
                existing += 1
                indexed_hits += 1
                valid_entries[identity] = metadata
                continue
            authoritative_checks += 1
            if self.d.has_fingerprint(self.d.fingerprint_dir, composition):
                existing += 1
                refreshed = self.d.checkpoint_metadata(path)
                if refreshed is not None:
                    valid_entries[identity] = refreshed
            else:
                missing_compositions.append(composition)

        self.d.detail(
            f"FINGERPRINT_CHECKPOINT_SCAN total={total} existing={existing} missing={len(missing_compositions)} "
            f"indexed_hits={indexed_hits} authoritative_checks={authoritative_checks} index_reusable={index_reusable}"
        )
        return total, existing, missing_compositions, valid_entries, candidates_sha256


    def persist_evidence(self, teams, fund_histories, *, max_workers: int | None) -> int:
        """Compute only missing fingerprints and persist each result immediately."""
        total, existing, missing_compositions, checkpoint_entries, candidates_sha256 = scan_checkpoints(teams)
        missing = len(missing_compositions)
        self.d.log(f"  fingerprint checkpoint scan: total={total} existing={existing} missing={missing}")
        self.d.manifest_update("composition_evidence", "running", total=total, existing=existing, missing=missing)
        if missing == 0:
            self.d.log("  all Composition fingerprints already persisted; no recomputation required")
            self.d.publish_checkpoint_index(self.d.checkpoint_index_path, candidates_sha256, checkpoint_entries)
            self.d.detail(f"FINGERPRINT_STAGE_SKIPPED reason=all_checkpoints_present index_entries={len(checkpoint_entries)}")
            self.d.manifest_update("composition_evidence", "complete", total=total, newly_computed=0, reused=existing)
            return total

        started = time.perf_counter()
        completed = failed = 0
        for composition, fingerprint, error in self.d.analyze_compositions_parallel_resilient(
            missing_compositions, fund_histories, max_workers=max_workers
        ):
            identity = self.d.composition_identity(composition)
            if error is not None:
                failed += 1
                self.d.detail(f"FINGERPRINT_FAILED composition={identity} error={error!r}")
                continue
            destination = self.d.persist_fingerprint(fingerprint, self.d.fingerprint_dir)
            metadata = self.d.checkpoint_metadata(destination)
            if metadata is None:
                failed += 1
                self.d.detail(f"FINGERPRINT_FAILED composition={identity} error=checkpoint_missing_after_persist")
                continue
            checkpoint_entries[identity] = metadata
            completed += 1
            self.d.detail(f"FINGERPRINT_PERSISTED index={completed}/{missing} composition={identity} path={destination.relative_to(self.d.project_root)}")
            processed = completed + failed
            if processed % 1000 == 0 or processed == missing:
                elapsed = time.perf_counter() - started
                rate = processed / elapsed if elapsed else 0.0
                eta = (missing - processed) / rate if rate else 0.0
                self.d.log(f"  Composition evidence: {processed}/{missing} missing work units | persisted={completed} failed={failed} | rate={rate:.1f}/s | ETA~{eta:.0f}s")
                self.d.detail(f"FINGERPRINT_PROGRESS processed={processed} total_missing={missing} persisted={completed} failed={failed} rate={rate:.3f} eta_seconds={eta:.1f}")
                self.d.manifest_update("composition_evidence", "running", total=total, existing=existing, missing=missing, processed=processed, persisted=completed, failed=failed)
        if failed:
            self.d.detail(f"FINGERPRINT_STAGE_FAILED failed={failed} total_missing={missing}")
            self.d.manifest_update("composition_evidence", "failed", total=total, newly_computed=completed, failed=failed)
            raise RuntimeError(f"Composition evidence stage completed with {failed} failed work units")
        elapsed = time.perf_counter() - started
        self.d.publish_checkpoint_index(self.d.checkpoint_index_path, candidates_sha256, checkpoint_entries)
        self.d.log(f"  Composition evidence complete: {total} persisted | newly computed={completed} | elapsed={elapsed:.1f}s")
        self.d.detail(f"FINGERPRINT_STAGE_COMPLETE total={total} newly_computed={completed} elapsed_seconds={elapsed:.3f} index_entries={len(checkpoint_entries)}")
        self.d.manifest_update("composition_evidence", "complete", total=total, reused=existing, newly_computed=completed, elapsed_seconds=round(elapsed, 3))
        return total

