"""Production FINAL-stage compromise-programming analysis for Lakshya.

The FINAL stage orders already-qualified MISSION Compositions without adding
subjective Purpose weights.

For each Purpose it:

1. chooses the longest supported analytical Elevation horizon not beyond the
   Purpose horizon;
2. compares the seven Elevation dimensions at that horizon plus all twelve
   native Protection dimensions;
3. converts each dimension to a population-relative desirability coordinate;
4. removes only zero-variance dimensions from that comparison population;
5. defines the Utopia Point as the best observed value on every remaining
   spoke;
6. expresses every Composition as distance from Utopia;
7. uses unweighted L2 as the primary compromise ordering;
8. retains L-infinity as a worst-spoke diagnostic and joint diagnostic
   frontier, never as an arbitrary elimination threshold;
9. measures ordering robustness with an Lp sweep, leave-one-spoke
   sensitivity, and deterministic population bootstrap.

No Purpose score, subjective family weights, arbitrary kill threshold,
clustering, or region model is introduced here.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from team_analysis.comparator_surface import PROTECTION_METRICS, ROLLING_METRICS

from .observation_horizon import nearest_supported_horizon

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
FINGERPRINT_DIR = DATA_DIR / "fingerprints" / "composition"
OUTPUT_DIR = PROJECT_ROOT / "output"

FINAL_CONTRACT_VERSION = "1"
DEFAULT_BOOTSTRAP_RESAMPLES = 5000
DEFAULT_BOOTSTRAP_SEED = 20260906
DEFAULT_LP_VALUES = tuple(round(1.0 + 0.25 * i, 2) for i in range(37))


@dataclass(frozen=True)
class FinalAnalysis:
    purpose: str
    purpose_horizon_years: float
    nominal_elevation_horizon_years: int
    population_size: int
    axes: tuple[str, ...]
    signatures: pd.DataFrame
    distances: pd.DataFrame
    results: pd.DataFrame
    lnorm_sweep: pd.DataFrame
    leave_one_spoke: pd.DataFrame
    bootstrap: pd.DataFrame
    joint_frontier: pd.DataFrame
    axis_metadata: pd.DataFrame


def _load_payload(identity: str, fingerprint_root: Path) -> dict:
    path = fingerprint_root / f"{identity}.json"
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


def _finite(value: object) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _raw_axis_values(payload: dict, horizon_years: int) -> dict[str, float | None]:
    elevation = payload.get("elevation", {})
    evidence = elevation.get(f"rolling_{horizon_years}y")
    values: dict[str, float | None] = {}
    for metric in ROLLING_METRICS:
        axis = f"elevation_{horizon_years}y_{metric}"
        values[axis] = _finite(
            evidence.get(metric) if isinstance(evidence, dict) else None
        )

    protection = payload.get("protection", {})
    thresholds = protection.get("pct_days_at_or_above_threshold", {})
    for metric in PROTECTION_METRICS:
        axis = f"protection_{metric}"
        if metric in protection:
            value = protection[metric]
        elif metric.startswith("pct_days_at_or_above_"):
            threshold = metric.removeprefix("pct_days_at_or_above_")
            value = thresholds.get(threshold)
        else:
            value = None
        values[axis] = _finite(value)
    return values


def _average_tie_percentile(values: pd.Series) -> pd.Series:
    count = len(values)
    if count == 1:
        return pd.Series([1.0], index=values.index, dtype=float)
    return (values.rank(method="average", pct=False) - 1.0) / (count - 1.0)


def _axis_direction(axis: str) -> str:
    return "down" if axis.startswith("protection_") else "up"


def _selected_axes(horizon_years: int) -> list[str]:
    return [
        *[f"elevation_{horizon_years}y_{metric}" for metric in ROLLING_METRICS],
        *[f"protection_{metric}" for metric in PROTECTION_METRICS],
    ]


def build_purpose_surface(
    identities: list[str] | tuple[str, ...] | set[str],
    purpose_horizon_years: float,
    fingerprint_root: Path = FINGERPRINT_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Build the production Purpose surface and deterministic spoke metadata."""
    identities = sorted(set(str(identity) for identity in identities))
    if not identities:
        raise ValueError("FINAL requires at least one MISSION survivor")
    if purpose_horizon_years <= 0:
        raise ValueError("Purpose horizon must be positive")

    horizon = nearest_supported_horizon(purpose_horizon_years)
    if horizon is None:
        raise ValueError(
            f"Purpose horizon {purpose_horizon_years}Y has no supported analytical horizon"
        )

    selected = _selected_axes(horizon)
    raw_rows = []
    for identity in identities:
        raw_rows.append(
            {
                "composition": identity,
                **_raw_axis_values(_load_payload(identity, fingerprint_root), horizon),
            }
        )
    raw = pd.DataFrame(raw_rows).set_index("composition")

    incomplete = [axis for axis in selected if raw[axis].isna().any()]
    if incomplete:
        raise ValueError(
            "FINAL surface has incomplete evidence on selected axes: "
            + ", ".join(incomplete)
        )

    varying_axes = [
        axis
        for axis in selected
        if not np.isclose(raw[axis].max(), raw[axis].min(), rtol=0.0, atol=1e-12)
    ]
    if not varying_axes:
        raise ValueError("FINAL surface has no varying dimensions")

    signatures = pd.DataFrame(index=raw.index)
    metadata_rows = []
    for index, axis in enumerate(selected, start=1):
        direction = _axis_direction(axis)
        observed_min = float(raw[axis].min())
        observed_max = float(raw[axis].max())
        varying = axis in varying_axes
        if varying:
            relative = _average_tie_percentile(raw[axis])
            if direction == "down":
                relative = 1.0 - relative
            signatures[axis] = relative.astype(float)
        metadata_rows.append(
            {
                "axis_index": index,
                "axis": axis,
                "family": "protection" if direction == "down" else "elevation",
                "direction": direction,
                "horizon_years": horizon if direction == "up" else "",
                "observed_min": observed_min,
                "observed_max": observed_max,
                "range": observed_max - observed_min,
                "included_in_final": varying,
                "exclusion_reason": "zero_variance" if not varying else "",
            }
        )

    signatures = signatures.reset_index()
    metadata = pd.DataFrame(metadata_rows)
    return signatures, metadata, horizon


def distance_from_utopia(
    signatures: pd.DataFrame, axes: list[str] | tuple[str, ...]
) -> pd.DataFrame:
    """Return per-spoke regret from the attainable Utopia Point (coordinate 1)."""
    if not axes:
        raise ValueError("At least one varying axis is required")
    distances = signatures[["composition"]].copy()
    for axis in axes:
        values = signatures[axis].astype(float)
        if ((values < 0.0) | (values > 1.0)).any():
            raise ValueError(f"Radial coordinate outside [0,1]: {axis}")
        distances[axis] = 1.0 - values
    return distances


def _l_norm(distance_matrix: np.ndarray, p: float) -> np.ndarray:
    if p <= 0:
        raise ValueError("Lp order must be positive")
    if np.isinf(p):
        return np.max(distance_matrix, axis=1)
    return np.sum(distance_matrix**p, axis=1) ** (1.0 / p)


def _rank_ascending(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).rank(method="min", ascending=True).astype(int).to_numpy()


def score_compromises(
    distances: pd.DataFrame, axes: list[str] | tuple[str, ...]
) -> pd.DataFrame:
    """Score candidates with primary L2 and diagnostic L-infinity measures."""
    matrix = distances[list(axes)].to_numpy(dtype=float)
    l2 = _l_norm(matrix, 2.0)
    linf = _l_norm(matrix, np.inf)
    result = distances[["composition"]].copy()
    result["l2_distance"] = l2
    result["linf_distance"] = linf
    result["l2_rank"] = _rank_ascending(l2)
    result["linf_rank"] = _rank_ascending(linf)
    worst_index = np.argmax(matrix, axis=1)
    result["worst_spoke"] = [axes[index] for index in worst_index]
    result["worst_spoke_distance"] = matrix[np.arange(len(matrix)), worst_index]
    result["winner"] = result["l2_rank"] == 1
    return result.sort_values(
        ["l2_distance", "linf_distance", "composition"],
        kind="mergesort",
    ).reset_index(drop=True)


def joint_l2_linf_frontier(results: pd.DataFrame) -> pd.DataFrame:
    """Return the non-dominated set when minimizing L2 and L-infinity."""
    values = results[["l2_distance", "linf_distance"]].to_numpy(float)
    keep = np.ones(len(values), dtype=bool)
    for i in range(len(values)):
        dominated = (
            (values[:, 0] <= values[i, 0])
            & (values[:, 1] <= values[i, 1])
            & ((values[:, 0] < values[i, 0]) | (values[:, 1] < values[i, 1]))
        )
        dominated[i] = False
        if dominated.any():
            keep[i] = False
    return results.loc[keep].sort_values(
        ["l2_distance", "linf_distance", "composition"],
        kind="mergesort",
    ).reset_index(drop=True)


def lnorm_sweep(
    distances: pd.DataFrame,
    axes: list[str] | tuple[str, ...],
    p_values: tuple[float, ...] = DEFAULT_LP_VALUES,
) -> pd.DataFrame:
    """Measure which Composition wins as the compromise norm changes."""
    matrix = distances[list(axes)].to_numpy(dtype=float)
    rows = []
    for p in p_values:
        values = _l_norm(matrix, p)
        minimum = float(values.min())
        winner_indices = np.flatnonzero(
            np.isclose(values, minimum, rtol=0.0, atol=1e-12)
        )
        order = np.argsort(values, kind="mergesort")
        winner_index = int(winner_indices[0])
        rows.append(
            {
                "p": p,
                "winner": distances.iloc[winner_index]["composition"],
                "winning_distance": float(values[winner_index]),
                "winner_rank": int(np.flatnonzero(order == winner_index)[0] + 1),
                "winner_count_at_minimum": len(winner_indices),
            }
        )
    return pd.DataFrame(rows)


def leave_one_spoke_sensitivity(
    distances: pd.DataFrame, axes: list[str] | tuple[str, ...]
) -> pd.DataFrame:
    """Re-run primary L2 after removing each varying spoke once."""
    if len(axes) < 2:
        raise ValueError("Leave-one-spoke sensitivity requires at least two axes")
    full_l2 = _l_norm(distances[list(axes)].to_numpy(float), 2.0)
    primary_index = int(np.argmin(full_l2))
    primary_winner = distances.iloc[primary_index]["composition"]
    rows = []
    for removed in axes:
        remaining = [axis for axis in axes if axis != removed]
        values = distances[remaining].to_numpy(float)
        l2 = _l_norm(values, 2.0)
        order = np.argsort(l2, kind="mergesort")
        winner_index = int(order[0])
        primary_position = int(np.flatnonzero(order == primary_index)[0] + 1)
        rows.append(
            {
                "removed_spoke": removed,
                "winner": distances.iloc[winner_index]["composition"],
                "winner_l2_distance": float(l2[winner_index]),
                "primary_winner": primary_winner,
                "primary_winner_rank": primary_position,
            }
        )
    return pd.DataFrame(rows)


def _bootstrap_percentile_coordinate(
    population_values: np.ndarray, sampled_values: np.ndarray
) -> np.ndarray:
    """Evaluate the same average-tie percentile convention under one resample."""
    n = len(population_values)
    order = np.argsort(sampled_values, kind="mergesort")
    sorted_values = sampled_values[order]
    left = np.searchsorted(sorted_values, population_values, side="left")
    right = np.searchsorted(sorted_values, population_values, side="right")
    if np.all(sampled_values == sampled_values[0]):
        return (population_values >= sampled_values[0]).astype(float)
    return np.clip(((left + right) / 2.0) / max(n - 1, 1), 0.0, 1.0)


def bootstrap_robustness(
    signatures: pd.DataFrame,
    axes: list[str] | tuple[str, ...],
    *,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> pd.DataFrame:
    """Rebuild empirical coordinates and L2 ordering for each population resample.

    The original Composition population is resampled with replacement. The
    population-relative coordinate system is rebuilt for every resample and
    the original candidate set is scored in that coordinate system. This is
    a stability test for the analytical ordering, not a forecast of returns.
    """
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    matrix = signatures[list(axes)].to_numpy(dtype=float)
    n = len(matrix)
    rng = np.random.default_rng(seed)
    wins = np.zeros(n, dtype=int)
    rank_sum = np.zeros(n, dtype=float)
    rank_values = np.empty((resamples, n), dtype=np.int16)

    for iteration in range(resamples):
        sample_indices = rng.integers(0, n, size=n)
        sampled = matrix[sample_indices]
        radial = np.empty_like(matrix)
        for column in range(matrix.shape[1]):
            radial[:, column] = _bootstrap_percentile_coordinate(
                matrix[:, column], sampled[:, column]
            )
        regrets = 1.0 - radial
        l2 = _l_norm(regrets, 2.0)
        order = np.argsort(l2, kind="mergesort")
        ranks = np.empty(n, dtype=np.int16)
        ranks[order] = np.arange(1, n + 1, dtype=np.int16)
        rank_values[iteration] = ranks
        wins[order[0]] += 1
        rank_sum += ranks

    compositions = signatures["composition"].tolist()
    rows = []
    for index, composition in enumerate(compositions):
        rows.append(
            {
                "composition": composition,
                "bootstrap_wins": int(wins[index]),
                "bootstrap_win_pct": float(wins[index] / resamples),
                "bootstrap_median_rank": float(np.median(rank_values[:, index])),
                "bootstrap_mean_rank": float(rank_sum[index] / resamples),
                "bootstrap_p05_rank": float(np.percentile(rank_values[:, index], 5)),
                "bootstrap_p95_rank": float(np.percentile(rank_values[:, index], 95)),
                "resamples": resamples,
                "seed": seed,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["bootstrap_win_pct", "bootstrap_mean_rank", "composition"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def analyze_purpose(
    purpose: str,
    identities: list[str],
    purpose_horizon_years: float,
    *,
    fingerprint_root: Path = FINGERPRINT_DIR,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> FinalAnalysis:
    """Run the complete production FINAL algorithm for one Purpose."""
    signatures, axis_metadata, horizon = build_purpose_surface(
        identities, purpose_horizon_years, fingerprint_root
    )
    axes = tuple(axis_metadata.loc[axis_metadata["included_in_final"], "axis"].tolist())
    distances = distance_from_utopia(signatures, axes)
    results = score_compromises(distances, axes)
    sweep = lnorm_sweep(distances, axes)
    sensitivity = leave_one_spoke_sensitivity(distances, axes)
    bootstrap = bootstrap_robustness(
        signatures,
        axes,
        resamples=bootstrap_resamples,
        seed=bootstrap_seed,
    )
    frontier = joint_l2_linf_frontier(results)
    return FinalAnalysis(
        purpose=purpose,
        purpose_horizon_years=purpose_horizon_years,
        nominal_elevation_horizon_years=horizon,
        population_size=len(identities),
        axes=axes,
        signatures=signatures,
        distances=distances,
        results=results,
        lnorm_sweep=sweep,
        leave_one_spoke=sensitivity,
        bootstrap=bootstrap,
        joint_frontier=frontier,
        axis_metadata=axis_metadata,
    )


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(path)


def write_analysis(analysis: FinalAnalysis, output_dir: Path = OUTPUT_DIR) -> dict[str, Path]:
    """Persist the complete FINAL evidence bundle atomically."""
    prefix = output_dir / f"final_{analysis.purpose}"
    paths = {
        "axes": prefix.with_name(prefix.name + "_axes.csv"),
        "signatures": prefix.with_name(prefix.name + "_signatures.csv"),
        "distances": prefix.with_name(prefix.name + "_distances.csv"),
        "results": prefix.with_name(prefix.name + "_results.csv"),
        "lnorm": prefix.with_name(prefix.name + "_lnorm_sweep.csv"),
        "sensitivity": prefix.with_name(prefix.name + "_leave_one_spoke.csv"),
        "bootstrap": prefix.with_name(prefix.name + "_bootstrap.csv"),
        "frontier": prefix.with_name(prefix.name + "_joint_l2_linf_frontier.csv"),
    }
    _atomic_csv(paths["axes"], analysis.axis_metadata)
    _atomic_csv(paths["signatures"], analysis.signatures)
    _atomic_csv(paths["distances"], analysis.distances)
    _atomic_csv(paths["results"], analysis.results)
    _atomic_csv(paths["lnorm"], analysis.lnorm_sweep)
    _atomic_csv(paths["sensitivity"], analysis.leave_one_spoke)
    _atomic_csv(paths["bootstrap"], analysis.bootstrap)
    _atomic_csv(paths["frontier"], analysis.joint_frontier)

    winner = analysis.results.iloc[0]
    bootstrap_winner = analysis.bootstrap.loc[
        analysis.bootstrap["composition"] == winner["composition"]
    ].iloc[0]
    summary = pd.DataFrame(
        [
            {
                "purpose": analysis.purpose,
                "purpose_horizon_years": analysis.purpose_horizon_years,
                "nominal_elevation_horizon_years": analysis.nominal_elevation_horizon_years,
                "population_size": analysis.population_size,
                "informative_spoke_count": len(analysis.axes),
                "primary_winner": winner["composition"],
                "primary_l2_distance": winner["l2_distance"],
                "primary_linf_distance": winner["linf_distance"],
                "primary_worst_spoke": winner["worst_spoke"],
                "joint_frontier_size": len(analysis.joint_frontier),
                "bootstrap_resamples": int(bootstrap_winner["resamples"]),
                "bootstrap_seed": int(bootstrap_winner["seed"]),
                "bootstrap_primary_winner_win_pct": float(bootstrap_winner["bootstrap_win_pct"]),
                "contract_version": FINAL_CONTRACT_VERSION,
            }
        ]
    )
    paths["summary"] = prefix.with_name(prefix.name + "_summary.csv")
    _atomic_csv(paths["summary"], summary)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--horizon-years", required=True, type=float)
    parser.add_argument("--identities-file", required=True, type=Path)
    parser.add_argument("--fingerprint-root", type=Path, default=FINGERPRINT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=DEFAULT_BOOTSTRAP_RESAMPLES)
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    args = parser.parse_args()

    identities = pd.read_csv(args.identities_file)["composition"].astype(str).tolist()
    analysis = analyze_purpose(
        args.purpose,
        identities,
        args.horizon_years,
        fingerprint_root=args.fingerprint_root,
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
    )
    for path in write_analysis(analysis, args.output_dir).values():
        print(path)


if __name__ == "__main__":
    main()
