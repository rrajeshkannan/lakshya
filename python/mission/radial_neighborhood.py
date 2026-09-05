"""Native Composition radial-geometry experiment.

This is the first step of Radial Neighbourhood Discovery.  It deliberately
returns to the native 40-dimensional Composition gate surface rather than
using pairwise behavioural metrics as coordinates.

The experiment is descriptive only:
- no clustering threshold or requested group count;
- no ranking, scoring, pruning, or anchor selection;
- no change to the MISSION pipeline.

For each native dimension, values are converted to a population-relative
percentile in [0, 1].  Higher is always "farther from the centre" on the
radial representation: upward Elevation dimensions keep their percentile,
while downward Protection dimensions are reversed.  This removes unit and
scale differences while preserving the native direction of desirability.

The resulting table is a radial signature: one row per unique Composition and
one column per native gate dimension.  A later visual/group-discovery step can
consume this representation without redefining the underlying evidence.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from team_analysis.comparator_surface import (
    PROTECTION_METRICS,
    ROLLING_HORIZONS,
    ROLLING_METRICS,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
FINGERPRINT_DIR = PROJECT_ROOT / "data" / "fingerprints" / "composition"


def _dimensions() -> list[tuple[str, str, str, int | None, str]]:
    """Return (axis, family, direction, horizon, metric) in gate order."""
    dimensions: list[tuple[str, str, str, int | None, str]] = []
    for years in ROLLING_HORIZONS:
        for metric in ROLLING_METRICS:
            dimensions.append(
                (f"elevation_{years}y_{metric}", "elevation", "up", years, metric)
            )
    for metric in PROTECTION_METRICS:
        dimensions.append(
            (f"protection_{metric}", "protection", "down", None, metric)
        )
    return dimensions


def _read_survivor_identities(output_dir: Path, purposes: list[str] | None) -> set[str]:
    files = sorted(output_dir.glob("mission_survivors_*.csv"))
    if purposes:
        files = [output_dir / f"mission_survivors_{purpose}.csv" for purpose in sorted(set(purposes))]
    if not files:
        raise ValueError("No MISSION survivor files found")
    missing = [path for path in files if not path.is_file()]
    if missing:
        raise ValueError("Missing MISSION survivor file(s): " + ", ".join(str(path) for path in missing))

    identities: set[str] = set()
    for path in files:
        frame = pd.read_csv(path)
        if "composition" not in frame.columns or frame.empty:
            raise ValueError(f"Invalid or empty MISSION survivor file: {path}")
        identities.update(frame["composition"].astype(str))
    if not identities:
        raise ValueError("No unique Composition identities found")
    return identities


def _load_payload(identity: str, root: Path) -> dict:
    path = root / f"{identity}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Persisted Composition fingerprint missing: {identity}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported fingerprint schema: {path}")
    if payload.get("kind") != "composition_fingerprint":
        raise ValueError(f"Invalid fingerprint kind: {path}")
    if payload.get("composition") != identity:
        raise ValueError(f"Composition identity mismatch: {path}")
    return payload


def _raw_values(payload: dict) -> dict[str, float]:
    values: dict[str, float] = {}
    elevation = payload.get("elevation", {})
    for years in ROLLING_HORIZONS:
        evidence = elevation.get(f"rolling_{years}y")
        for metric in ROLLING_METRICS:
            axis = f"elevation_{years}y_{metric}"
            if evidence is None or metric not in evidence:
                raise ValueError(f"Missing native Elevation value {axis}")
            values[axis] = float(evidence[metric])

    protection = payload.get("protection", {})
    threshold_values = protection.get("pct_days_at_or_above_threshold", {})
    for metric in PROTECTION_METRICS:
        axis = f"protection_{metric}"
        if metric in protection:
            value = protection[metric]
        elif metric.startswith("pct_days_at_or_above_"):
            threshold = metric.removeprefix("pct_days_at_or_above_")
            if threshold not in threshold_values:
                raise ValueError(f"Missing native Protection value {axis}")
            value = threshold_values[threshold]
        else:
            raise ValueError(f"Missing native Protection value {axis}")
        values[axis] = float(value)
    return values


def _population_percentile(series: pd.Series) -> pd.Series:
    """Map a population column to average-tie percentile rank in [0, 1]."""
    count = len(series)
    if count == 1:
        return pd.Series([1.0], index=series.index, dtype=float)
    return (series.rank(method="average", pct=False) - 1.0) / (count - 1.0)


def build_radial_signatures(
    identities: set[str],
    fingerprint_root: Path = FINGERPRINT_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build relative radial signatures and native-axis metadata."""
    dimensions = _dimensions()
    expected_axes = [item[0] for item in dimensions]
    raw_rows = []
    for identity in sorted(identities):
        raw = _raw_values(_load_payload(identity, fingerprint_root))
        raw_rows.append({"composition": identity, **raw})

    raw_frame = pd.DataFrame(raw_rows)
    signatures = raw_frame[["composition"]].copy()
    for axis, _, direction, _, _ in dimensions:
        values = raw_frame[axis]
        relative = _population_percentile(values)
        if direction == "down":
            relative = 1.0 - relative
        signatures[axis] = relative.astype(float)

    if set(signatures.columns) != {"composition", *expected_axes}:
        raise AssertionError("Radial signature axes do not match the native 40-D surface")

    metadata = pd.DataFrame(
        [
            {
                "axis_index": index,
                "axis": axis,
                "family": family,
                "direction": direction,
                "horizon_years": horizon,
                "metric": metric,
                "radial_semantics": "higher_relative_evidence",
            }
            for index, (axis, family, direction, horizon, metric) in enumerate(dimensions, start=1)
        ]
    )
    return signatures, metadata


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(path)


def run(
    purposes: list[str] | None = None,
    output_dir: Path = OUTPUT_DIR,
    fingerprint_root: Path = FINGERPRINT_DIR,
) -> tuple[Path, Path]:
    identities = _read_survivor_identities(output_dir, purposes)
    signatures, metadata = build_radial_signatures(identities, fingerprint_root)

    signature_path = output_dir / "radial_neighborhood_signatures.csv"
    metadata_path = output_dir / "radial_neighborhood_axes.csv"
    _atomic_csv(signature_path, signatures)
    _atomic_csv(metadata_path, metadata)
    return signature_path, metadata_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build native 40-D relative radial signatures for MISSION survivors"
    )
    parser.add_argument("--purposes", nargs="+")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--fingerprint-root", type=Path, default=FINGERPRINT_DIR)
    args = parser.parse_args()
    for path in run(args.purposes, args.output_dir, args.fingerprint_root):
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
