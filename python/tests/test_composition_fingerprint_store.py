from __future__ import annotations

import json

import pandas as pd
import pytest

from lakshya_core.models import Fund
from team_analysis.analyze_composition import analyze_composition
from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint_store import (
    evidence_path,
    fingerprint_path,
    fingerprint_to_payload,
    has_fingerprint,
    load_fingerprint,
    load_fingerprint_evidence,
    persist_fingerprint,
)
from team_analysis.team import Team


def _fund(isin: str):
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def test_composition_fingerprint_round_trips_without_recalculation(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.50, "B": 0.50})
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [200.0 - i for i in range(30)]}),
    }

    original = analyze_composition(composition, histories)
    path = persist_fingerprint(original, tmp_path)
    restored = load_fingerprint(path, composition)

    assert path == fingerprint_path(tmp_path, composition)
    assert restored.composition == original.composition
    pd.testing.assert_frame_equal(restored.nav, original.nav)
    assert restored.elevation == original.elevation
    assert restored.protection == original.protection


def test_compact_mission_evidence_round_trips_without_nav(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.50, "B": 0.50})
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [200.0 - i for i in range(30)]}),
    }

    original = analyze_composition(composition, histories)
    full_path = persist_fingerprint(original, tmp_path)
    compact_path = evidence_path(tmp_path, composition)

    elevation, protection = load_fingerprint_evidence(full_path, composition)

    assert compact_path.is_file()
    assert elevation == original.elevation
    assert protection == original.protection
    assert compact_path.stat().st_size < full_path.stat().st_size


def test_compact_mission_evidence_migrates_existing_full_fingerprint(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.50, "B": 0.50})
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [200.0 - i for i in range(30)]}),
    }

    original = analyze_composition(composition, histories)
    full_path = fingerprint_path(tmp_path, composition)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    # Simulate a pre-PASS-4 persisted fingerprint with no compact sidecar.
    full_path.write_text(
        json.dumps(fingerprint_to_payload(original), separators=(",", ":")),
        encoding="utf-8",
    )

    elevation, protection = load_fingerprint_evidence(full_path, composition)

    assert elevation == original.elevation
    assert protection == original.protection
    assert evidence_path(tmp_path, composition).is_file()


def test_compact_mission_evidence_rejects_invalid_sidecar(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.50, "B": 0.50})
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [200.0 - i for i in range(30)]}),
    }

    original = analyze_composition(composition, histories)
    full_path = persist_fingerprint(original, tmp_path)
    sidecar = evidence_path(tmp_path, composition)
    sidecar.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "composition_evidence",
                "composition": "wrong",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Composition identity mismatch"):
        load_fingerprint_evidence(full_path, composition)


def test_fingerprint_path_uses_canonical_composition_identity(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"B": 0.70, "A": 0.30})
    equivalent_weight_order = Composition(team=team, weights={"A": 0.30, "B": 0.70})

    assert fingerprint_path(tmp_path, composition) == fingerprint_path(
        tmp_path, equivalent_weight_order
    )
    assert composition_identity(composition) in fingerprint_path(tmp_path, composition).name


def test_corrupt_checkpoint_is_detected_on_load(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.50, "B": 0.50})
    path = fingerprint_path(tmp_path, composition)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")

    assert not has_fingerprint(tmp_path, composition)
    with pytest.raises(json.JSONDecodeError):
        load_fingerprint(path, composition)


def test_checkpoint_with_wrong_identity_is_rejected_on_load(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.50, "B": 0.50})
    path = fingerprint_path(tmp_path, composition)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"schema_version":1,"kind":"composition_fingerprint","composition":"wrong"}',
        encoding="utf-8",
    )

    assert not has_fingerprint(tmp_path, composition)
    with pytest.raises(ValueError, match="Composition identity mismatch"):
        load_fingerprint(path, composition)
