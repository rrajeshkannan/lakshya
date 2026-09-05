from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from final.compromise_programming import (
    build_purpose_surface,
    distance_from_utopia,
    joint_l2_linf_frontier,
    leave_one_spoke_sensitivity,
    lnorm_sweep,
    score_compromises,
)


METRICS = (
    "minimum",
    "percentile_25",
    "median",
    "percentile_75",
    "maximum",
    "mean",
    "positive_period_pct",
)


def _payload(identity: str, base: float, *, constant_positive_period: bool = False) -> dict:
    elevation = {
        f"rolling_{years}y": {
            metric: (
                base
                if metric == "positive_period_pct" and constant_positive_period
                else base + years + index
            )
            for index, metric in enumerate(METRICS)
        }
        for years in (3, 5, 7, 10)
    }
    protection = {
        "median_severity_pct": base + 1,
        "percentile_75_severity_pct": base + 2,
        "percentile_90_severity_pct": base + 3,
        "percentile_95_severity_pct": base + 4,
        "percentile_99_severity_pct": base + 5,
        "maximum_severity_pct": base + 6,
        "pct_days_at_or_above_threshold": {
            "5": base + 7,
            "10": base + 8,
            "15": base + 9,
            "20": base + 10,
            "25": base + 11,
            "30": base + 12,
        },
    }
    return {
        "schema_version": 1,
        "kind": "composition_fingerprint",
        "composition": identity,
        "members": ["A"],
        "weights": {"A": 1.0},
        "nav": [],
        "elevation": elevation,
        "protection": protection,
    }


def _write_population(
    tmp_path: Path, count: int = 3, *, constant_positive_period: bool = False
) -> list[str]:
    identities = [f"C{i}|isin=1.0" for i in range(count)]
    for index, identity in enumerate(identities):
        payload = _payload(
            identity, float(index), constant_positive_period=constant_positive_period
        )
        (tmp_path / f"{identity}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
    return identities


def test_surface_uses_requested_elevation_horizon_and_all_protection(tmp_path: Path):
    identities = _write_population(tmp_path, constant_positive_period=True)
    signatures, metadata, horizon = build_purpose_surface(identities, 8, tmp_path)

    assert horizon == 7
    assert len(metadata) == 19
    assert len([axis for axis in signatures.columns if axis != "composition"]) == 18
    assert not signatures.empty
    assert not metadata.loc[
        metadata["axis"] == "elevation_7y_positive_period_pct", "included_in_final"
    ].iloc[0]
    assert metadata.loc[
        metadata["axis"] == "elevation_7y_positive_period_pct", "exclusion_reason"
    ].iloc[0] == "zero_variance"


def test_surface_fails_on_incomplete_selected_evidence(tmp_path: Path):
    identities = _write_population(tmp_path)
    payload_path = tmp_path / f"{identities[1]}.json"
    payload = json.loads(payload_path.read_text())
    payload["elevation"]["rolling_7y"]["minimum"] = None
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="incomplete evidence"):
        build_purpose_surface(identities, 8, tmp_path)


def test_distance_from_utopia_and_l2_ordering():
    signatures = pd.DataFrame(
        {
            "composition": ["A", "B", "C"],
            "x": [1.0, 0.8, 0.5],
            "y": [0.0, 0.8, 0.5],
        }
    )
    distances = distance_from_utopia(signatures, ["x", "y"])
    results = score_compromises(distances, ["x", "y"])

    assert np.allclose(distances[["x", "y"]], [[0, 1], [0.2, 0.2], [0.5, 0.5]])
    assert results.iloc[0]["composition"] == "B"
    assert results.iloc[0]["l2_distance"] == pytest.approx(np.sqrt(0.08))


def test_joint_frontier_keeps_total_vs_worst_case_tradeoff():
    results = pd.DataFrame(
        {
            "composition": ["A", "B", "C"],
            "l2_distance": [1.0, 2.0, 3.0],
            "linf_distance": [2.0, 1.0, 3.0],
        }
    )
    frontier = joint_l2_linf_frontier(results)
    assert frontier["composition"].tolist() == ["A", "B"]


def test_lnorm_sweep_and_spoke_sensitivity_are_deterministic():
    distances = pd.DataFrame(
        {
            "composition": ["A", "B", "C"],
            "x": [0.0, 0.2, 0.4],
            "y": [0.8, 0.2, 0.4],
            "z": [0.8, 0.2, 0.4],
        }
    )
    sweep = lnorm_sweep(distances, ["x", "y", "z"], (1.0, 2.0, np.inf))
    assert sweep["p"].tolist() == [1.0, 2.0, np.inf]
    sensitivity = leave_one_spoke_sensitivity(distances, ["x", "y", "z"])
    assert len(sensitivity) == 3
    assert sensitivity["primary_winner"].nunique() == 1


def test_constant_dimension_is_not_a_final_spoke(tmp_path: Path):
    identities = _write_population(
        tmp_path, count=4, constant_positive_period=True
    )
    signatures, metadata, _ = build_purpose_surface(identities, 7, tmp_path)
    assert "elevation_7y_positive_period_pct" not in signatures.columns
    assert metadata.loc[
        metadata["axis"] == "elevation_7y_positive_period_pct", "range"
    ].iloc[0] == pytest.approx(0.0)
