from __future__ import annotations

import pandas as pd

from lakshya_core.models import Fund
from team_analysis.analyze_composition import analyze_composition
from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint_store import (
    fingerprint_path,
    has_fingerprint,
    load_fingerprint,
    persist_fingerprint,
)
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
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


def test_fingerprint_path_uses_canonical_composition_identity(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"B": 0.70, "A": 0.30})
    equivalent_weight_order = Composition(team=team, weights={"A": 0.30, "B": 0.70})

    assert fingerprint_path(tmp_path, composition) == fingerprint_path(
        tmp_path, equivalent_weight_order
    )
    assert composition_identity(composition) in fingerprint_path(tmp_path, composition).name


def test_corrupt_checkpoint_is_not_considered_complete(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.50, "B": 0.50})
    path = fingerprint_path(tmp_path, composition)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")

    assert not has_fingerprint(tmp_path, composition)


def test_checkpoint_with_wrong_identity_is_not_considered_complete(tmp_path):
    team = Team(members=(_fund("A"), _fund("B")))
    composition = Composition(team=team, weights={"A": 0.50, "B": 0.50})
    path = fingerprint_path(tmp_path, composition)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"schema_version":1,"kind":"composition_fingerprint","composition":"wrong"}',
        encoding="utf-8",
    )

    assert not has_fingerprint(tmp_path, composition)
