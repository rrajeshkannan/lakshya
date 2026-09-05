from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from mission.radial_neighborhood import build_radial_signatures


def _payload(identity: str, base: float) -> dict:
    metrics = (
        "minimum",
        "percentile_25",
        "median",
        "percentile_75",
        "maximum",
        "mean",
        "positive_period_pct",
    )
    elevation = {
        f"rolling_{years}y": {metric: base + years + index for index, metric in enumerate(metrics)}
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


def test_radial_signatures_have_native_40_dimensions(tmp_path: Path):
    identities = {"A|isin=1.0", "B|isin=1.0"}
    for identity, base in zip(sorted(identities), (10.0, 20.0)):
        (tmp_path / f"{identity}.json").write_text(
            json.dumps(_payload(identity, base)), encoding="utf-8"
        )

    signatures, axes = build_radial_signatures(identities, tmp_path)

    assert len(signatures) == 2
    assert len(axes) == 40
    assert len([column for column in signatures.columns if column != "composition"]) == 40
    assert set(signatures.drop(columns=["composition"]).min()) >= {0.0}
    assert set(signatures.drop(columns=["composition"]).max()) <= {1.0}


def test_protection_direction_is_reversed(tmp_path: Path):
    identities = {"A|isin=1.0", "B|isin=1.0"}
    for identity, base in zip(sorted(identities), (10.0, 20.0)):
        (tmp_path / f"{identity}.json").write_text(
            json.dumps(_payload(identity, base)), encoding="utf-8"
        )

    signatures, _ = build_radial_signatures(identities, tmp_path)
    row_a = signatures.loc[signatures["composition"] == "A|isin=1.0"].iloc[0]
    row_b = signatures.loc[signatures["composition"] == "B|isin=1.0"].iloc[0]

    assert row_a["elevation_3y_mean"] < row_b["elevation_3y_mean"]
    assert row_a["protection_median_severity_pct"] > row_b["protection_median_severity_pct"]


def test_axes_metadata_preserves_gate_order_and_direction(tmp_path: Path):
    identity = "A|isin=1.0"
    (tmp_path / f"{identity}.json").write_text(
        json.dumps(_payload(identity, 10.0)), encoding="utf-8"
    )

    _, axes = build_radial_signatures({identity}, tmp_path)

    assert axes.iloc[0]["axis"] == "elevation_3y_minimum"
    assert axes.iloc[0]["direction"] == "up"
    assert axes.iloc[27]["axis"] == "elevation_10y_positive_period_pct"
    assert axes.iloc[28]["axis"] == "protection_median_severity_pct"
    assert axes.iloc[28]["direction"] == "down"
    assert axes.iloc[39]["axis"] == "protection_pct_days_at_or_above_30"


def test_incomplete_native_evidence_excludes_only_that_axis_from_geometry(tmp_path: Path):
    identities = {"A|isin=1.0", "B|isin=1.0"}
    payload_a = _payload("A|isin=1.0", 10.0)
    payload_b = _payload("B|isin=1.0", 20.0)
    payload_b["elevation"]["rolling_10y"]["minimum"] = None
    for identity, payload in (("A|isin=1.0", payload_a), ("B|isin=1.0", payload_b)):
        (tmp_path / f"{identity}.json").write_text(json.dumps(payload), encoding="utf-8")

    signatures, axes = build_radial_signatures(identities, tmp_path)
    excluded = axes.loc[axes["axis"] == "elevation_10y_minimum"].iloc[0]
    included = axes.loc[axes["axis"] == "elevation_10y_median"].iloc[0]

    assert len(signatures) == 2
    assert "elevation_10y_minimum" not in signatures.columns
    assert len(signatures.columns) == 40  # composition plus 39 complete axes
    assert not excluded["included_in_radial_geometry"]
    assert excluded["observed_count"] == 1
    assert excluded["missing_count"] == 1
    assert excluded["coverage_ratio"] == 0.5
    assert excluded["exclusion_reason"] == "incomplete_native_evidence"
    assert included["included_in_radial_geometry"]
    assert pd.isna(included["exclusion_reason"])
