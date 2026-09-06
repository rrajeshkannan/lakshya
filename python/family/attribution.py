"""Family-level capital concentration and dependency attribution.

This is a post-FINAL observational layer. It does not rank, eliminate,
optimize, or modify any Purpose winner. It attributes the consequences of the
already-selected FINAL Compositions across the family-level Purpose capital.

Contract:
    purposes.csv current ``value`` -> Purpose capital
    dated FINAL summary -> selected Composition
    fund metadata -> fund / AMC identity

The output is intentionally descriptive. A concentration is an observation,
not a violation. No concentration threshold is encoded here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PURPOSES_PATH = DATA_DIR / "purpose" / "purposes.csv"
FUND_METADATA_PATH = DATA_DIR / "fund" / "funds_in_scope_metadata.csv"
REVIEWS_ROOT = DATA_DIR / "reviews"

ATTRIBUTION_SCHEMA_VERSION = 1
FINAL_CONTRACT_VERSION = "1"
MONEY_EPSILON = 1e-6
WEIGHT_EPSILON = 1e-9


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    _atomic_write(path, buffer.getvalue())


def _logger(path: Path) -> logging.Logger:
    logger = logging.getLogger("lakshya.family.attribution")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def parse_composition_identity(identity: str) -> dict[str, float]:
    """Parse canonical Composition identity into ISIN -> weight."""
    try:
        members_raw, weights_raw = identity.split("|", 1)
    except ValueError as exc:
        raise ValueError(f"Invalid Composition identity: {identity!r}") from exc
    members = [value for value in members_raw.split(",") if value]
    weights: dict[str, float] = {}
    for token in weights_raw.split(","):
        try:
            isin, value = token.split("=", 1)
            weights[isin] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Composition weight token: {token!r}") from exc
    if not members or set(members) != set(weights) or len(members) != len(weights):
        raise ValueError(f"Composition members/weights mismatch: {identity!r}")
    if any(weight < -WEIGHT_EPSILON for weight in weights.values()):
        raise ValueError(f"Composition contains negative weight: {identity!r}")
    if abs(sum(weights.values()) - 1.0) > WEIGHT_EPSILON:
        raise ValueError(f"Composition weights do not sum to 1: {identity!r}")
    return {isin: max(0.0, weight) for isin, weight in weights.items()}


def load_purpose_capital(path: Path = PURPOSES_PATH) -> dict[str, float]:
    """Load current Purpose capital from the authoritative Purpose source."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"name", "value"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Purpose source is missing required columns: {path}")
    result: dict[str, float] = {}
    for row in rows:
        name = row["name"].strip()
        if not name or name in result:
            raise ValueError(f"Invalid or duplicate Purpose in {path}: {name!r}")
        try:
            value = float(row["value"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid current capital for Purpose {name!r}") from exc
        if value < 0:
            raise ValueError(f"Negative current capital for Purpose {name!r}")
        result[name] = value
    total = sum(result.values())
    if total <= MONEY_EPSILON:
        raise ValueError("Total Purpose capital must be positive")
    return result


def load_fund_metadata(path: Path = FUND_METADATA_PATH) -> dict[str, dict[str, str]]:
    """Load current fund identity metadata keyed by ISIN."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"isin", "scheme_name", "amc"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Fund metadata is missing required columns: {path}")
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        isin = row["isin"].strip()
        if not isin:
            raise ValueError(f"Blank ISIN in {path}")
        if isin in result:
            raise ValueError(f"Duplicate ISIN in fund metadata: {isin}")
        result[isin] = {
            "scheme_name": row["scheme_name"].strip(),
            "amc": row["amc"].strip(),
        }
        if not result[isin]["scheme_name"] or not result[isin]["amc"]:
            raise ValueError(f"Incomplete metadata for ISIN: {isin}")
    return result


def _read_final_winner(path: Path, expected_purpose: str) -> tuple[str, dict[str, float], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one FINAL summary row: {path}")
    row = rows[0]
    if row.get("purpose") != expected_purpose:
        raise ValueError(f"FINAL Purpose mismatch in {path}")
    if row.get("contract_version") != FINAL_CONTRACT_VERSION:
        raise ValueError(f"FINAL contract mismatch in {path}")
    identity = row.get("primary_winner", "").strip()
    weights = parse_composition_identity(identity)
    return identity, weights, {
        "purpose_horizon_years": row.get("purpose_horizon_years", ""),
        "bootstrap_primary_winner_win_pct": row.get("bootstrap_primary_winner_win_pct", ""),
        "primary_l2_distance": row.get("primary_l2_distance", ""),
    }


def _verify_review_manifest(review_dir: Path, purposes: list[str]) -> dict:
    path = review_dir / "review_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"FINAL review manifest missing: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Invalid FINAL review manifest: {path}") from exc
    if manifest.get("as_of") != review_dir.name:
        raise ValueError("Review manifest date does not match review directory")
    if manifest.get("final_contract_version") != FINAL_CONTRACT_VERSION:
        raise ValueError("Review manifest FINAL contract mismatch")
    entries = {item.get("purpose"): item for item in manifest.get("purposes", [])}
    if set(entries) != set(purposes):
        raise ValueError("Review manifest Purpose set does not match requested Purposes")
    for purpose in purposes:
        summary = review_dir / f"{purpose}_summary.csv"
        if not summary.is_file():
            raise FileNotFoundError(f"Archived FINAL summary missing: {summary}")
        expected_hash = entries[purpose].get("summary_sha256")
        if expected_hash != _sha256(summary):
            raise ValueError(f"Archived FINAL summary hash mismatch: {summary}")
    return manifest


def build_family_attribution(
    purpose_capital: dict[str, float],
    final_winners: dict[str, str],
    fund_metadata: dict[str, dict[str, str]],
) -> dict[str, list[dict]]:
    """Build detailed capital attribution and aggregate dependency views."""
    if set(purpose_capital) != set(final_winners):
        raise ValueError("Purpose capital and FINAL winner sets do not match")
    total_capital = sum(purpose_capital.values())
    if total_capital <= MONEY_EPSILON:
        raise ValueError("Total family Purpose capital must be positive")

    detail: list[dict] = []
    fund_totals: dict[str, float] = defaultdict(float)
    fund_purposes: dict[str, set[str]] = defaultdict(set)
    amc_totals: dict[str, float] = defaultdict(float)
    amc_purposes: dict[str, set[str]] = defaultdict(set)
    purpose_totals: dict[str, float] = defaultdict(float)

    for purpose in sorted(purpose_capital):
        capital = purpose_capital[purpose]
        weights = parse_composition_identity(final_winners[purpose])
        allocated = 0.0
        for isin, weight in sorted(weights.items()):
            if isin not in fund_metadata:
                raise ValueError(f"FINAL winner references unknown fund ISIN: {isin}")
            attributed = capital * weight
            allocated += attributed
            fund_totals[isin] += attributed
            fund_purposes[isin].add(purpose)
            amc = fund_metadata[isin]["amc"]
            amc_totals[amc] += attributed
            amc_purposes[amc].add(purpose)
            purpose_totals[purpose] += attributed
            detail.append({
                "purpose": purpose,
                "purpose_capital": f"{capital:.2f}",
                "purpose_capital_pct": f"{100.0 * capital / total_capital:.6f}",
                "isin": isin,
                "scheme_name": fund_metadata[isin]["scheme_name"],
                "amc": amc,
                "composition_weight_pct": f"{100.0 * weight:.6f}",
                "attributed_capital": f"{attributed:.2f}",
                "attributed_family_pct": f"{100.0 * attributed / total_capital:.6f}",
            })
        if abs(allocated - capital) > MONEY_EPSILON:
            raise AssertionError(f"Purpose allocation does not reconcile: {purpose}")

    fund_rows = []
    for isin in sorted(fund_totals, key=lambda key: (-fund_totals[key], key)):
        fund_rows.append({
            "isin": isin,
            "scheme_name": fund_metadata[isin]["scheme_name"],
            "amc": fund_metadata[isin]["amc"],
            "attributed_capital": f"{fund_totals[isin]:.2f}",
            "family_capital_pct": f"{100.0 * fund_totals[isin] / total_capital:.6f}",
            "purpose_count": len(fund_purposes[isin]),
            "purpose_coverage_pct": f"{100.0 * len(fund_purposes[isin]) / len(purpose_capital):.6f}",
            "purposes": ",".join(sorted(fund_purposes[isin])),
        })

    amc_rows = []
    for amc in sorted(amc_totals, key=lambda key: (-amc_totals[key], key)):
        amc_rows.append({
            "amc": amc,
            "attributed_capital": f"{amc_totals[amc]:.2f}",
            "family_capital_pct": f"{100.0 * amc_totals[amc] / total_capital:.6f}",
            "purpose_count": len(amc_purposes[amc]),
            "purpose_coverage_pct": f"{100.0 * len(amc_purposes[amc]) / len(purpose_capital):.6f}",
            "purposes": ",".join(sorted(amc_purposes[amc])),
        })

    purpose_rows = []
    for purpose in sorted(purpose_capital):
        purpose_rows.append({
            "purpose": purpose,
            "purpose_capital": f"{purpose_capital[purpose]:.2f}",
            "family_capital_pct": f"{100.0 * purpose_capital[purpose] / total_capital:.6f}",
            "attributed_capital_check": f"{purpose_totals[purpose]:.2f}",
            "reconciles": abs(purpose_totals[purpose] - purpose_capital[purpose]) <= MONEY_EPSILON,
            "final_composition": final_winners[purpose],
        })

    return {
        "detail": detail,
        "fund": fund_rows,
        "amc": amc_rows,
        "purpose": purpose_rows,
    }


def write_family_attribution(
    as_of: str,
    rows: dict[str, list[dict]],
    *,
    output_dir: Path,
    input_hashes: dict[str, str],
) -> list[Path]:
    """Persist the family attribution review artifacts under data/reviews."""
    review_dir = output_dir
    files = {
        "detail": ("family_capital_attribution.csv", [
            "purpose", "purpose_capital", "purpose_capital_pct", "isin", "scheme_name",
            "amc", "composition_weight_pct", "attributed_capital", "attributed_family_pct",
        ]),
        "fund": ("family_fund_concentration.csv", [
            "isin", "scheme_name", "amc", "attributed_capital", "family_capital_pct",
            "purpose_count", "purpose_coverage_pct", "purposes",
        ]),
        "amc": ("family_amc_concentration.csv", [
            "amc", "attributed_capital", "family_capital_pct", "purpose_count",
            "purpose_coverage_pct", "purposes",
        ]),
        "purpose": ("family_purpose_dependency.csv", [
            "purpose", "purpose_capital", "family_capital_pct", "attributed_capital_check",
            "reconciles", "final_composition",
        ]),
    }
    paths: list[Path] = []
    for key, (filename, fields) in files.items():
        path = review_dir / filename
        _atomic_csv(path, fields, rows[key])
        paths.append(path)

    manifest = {
        "attribution_schema_version": ATTRIBUTION_SCHEMA_VERSION,
        "as_of": as_of,
        "nature": "descriptive_post_final_attribution",
        "optimization_or_guardrail": False,
        "input_hashes": input_hashes,
        "artifacts": [path.name for path in paths],
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    manifest_path = review_dir / "family_attribution_manifest.json"
    _atomic_write(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    paths.append(manifest_path)
    return paths


def run_family_attribution(
    as_of: str,
    *,
    data_dir: Path = DATA_DIR,
    purposes_path: Path | None = None,
    fund_metadata_path: Path | None = None,
    reviews_root: Path | None = None,
) -> list[Path]:
    """Run the auditable post-FINAL family attribution for one review date."""
    date.fromisoformat(as_of)
    purposes_path = purposes_path or data_dir / "purpose" / "purposes.csv"
    fund_metadata_path = fund_metadata_path or data_dir / "fund" / "funds_in_scope_metadata.csv"
    reviews_root = reviews_root or data_dir / "reviews"
    review_dir = reviews_root / as_of
    log = _logger(review_dir / "family_attribution.log")
    log.info("START as_of=%s", as_of)
    log.info("Loading Purpose capital source=%s", purposes_path)
    purpose_capital = load_purpose_capital(purposes_path)
    log.info("Loaded purposes=%d total_capital=%.2f", len(purpose_capital), sum(purpose_capital.values()))
    log.info("Loading fund metadata source=%s", fund_metadata_path)
    fund_metadata = load_fund_metadata(fund_metadata_path)
    log.info("Loaded fund_metadata=%d", len(fund_metadata))
    manifest = _verify_review_manifest(review_dir, sorted(purpose_capital))
    log.info("Verified FINAL review manifest purposes=%d", len(manifest["purposes"]))

    final_winners: dict[str, str] = {}
    for purpose in sorted(purpose_capital):
        summary = review_dir / f"{purpose}_summary.csv"
        identity, _, _ = _read_final_winner(summary, purpose)
        final_winners[purpose] = identity
        log.info("FINAL winner purpose=%s composition=%s", purpose, identity)

    input_hashes = {
        "purposes_csv_sha256": _sha256(purposes_path),
        "fund_metadata_sha256": _sha256(fund_metadata_path),
        "review_manifest_sha256": _sha256(review_dir / "review_manifest.json"),
    }
    for purpose in sorted(purpose_capital):
        input_hashes[f"{purpose}_summary_sha256"] = _sha256(review_dir / f"{purpose}_summary.csv")

    rows = build_family_attribution(purpose_capital, final_winners, fund_metadata)
    log.info("Built attribution detail_rows=%d funds=%d amcs=%d purposes=%d", len(rows["detail"]), len(rows["fund"]), len(rows["amc"]), len(rows["purpose"]))
    paths = write_family_attribution(as_of, rows, output_dir=review_dir, input_hashes=input_hashes)
    for path in paths:
        log.info("WROTE %s", path)
    log.info("COMPLETE as_of=%s", as_of)
    for handler in log.handlers:
        handler.flush()
        handler.close()
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="FINAL review date, YYYY-MM-DD")
    args = parser.parse_args()
    for path in run_family_attribution(args.as_of):
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
