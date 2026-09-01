from __future__ import annotations

import pandas as pd

from lakshya_core.models import Fund
from team_analysis.composition_pipeline import (
    stream_composition_fingerprints,
    stream_composition_fingerprints_parallel,
    analyze_compositions_parallel_resilient,
)
from team_analysis.composition import composition_identity
from team_analysis.generate_compositions import generate_compositions
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def _inputs():
    team = Team(members=(_fund("A"), _fund("B")))
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [200.0 - i for i in range(30)]}),
    }
    return [team], histories


def test_parallel_composition_pipeline_preserves_complete_grid():
    teams, histories = _inputs()
    results = list(stream_composition_fingerprints_parallel(teams, histories, max_workers=2))

    assert len(results) == 19
    assert all(fingerprint.composition is composition for composition, fingerprint in results)


def test_parallel_results_are_equivalent_to_serial_results():
    teams, histories = _inputs()
    serial = list(stream_composition_fingerprints(teams, histories))
    parallel = list(stream_composition_fingerprints_parallel(teams, histories, max_workers=2))

    serial_by_id = {composition_identity(c): f for c, f in serial}
    parallel_by_id = {composition_identity(c): f for c, f in parallel}

    assert serial_by_id.keys() == parallel_by_id.keys()
    for identity in serial_by_id:
        left = serial_by_id[identity]
        right = parallel_by_id[identity]
        assert right.composition == left.composition
        pd.testing.assert_frame_equal(right.nav, left.nav)
        assert right.elevation == left.elevation
        assert right.protection == left.protection


def test_parallel_result_set_is_deterministic_across_runs():
    teams, histories = _inputs()
    first = list(stream_composition_fingerprints_parallel(teams, histories, max_workers=2))
    second = list(stream_composition_fingerprints_parallel(teams, histories, max_workers=2))

    first_ids = sorted(composition_identity(c) for c, _ in first)
    second_ids = sorted(composition_identity(c) for c, _ in second)
    assert first_ids == second_ids


def test_resilient_parallel_pipeline_isolates_failed_work_units():
    fund_a = _fund("A")
    fund_b = _fund("B")
    singleton = Team(members=(fund_a,))
    twin = Team(members=(fund_a, fund_b))
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
    }
    compositions = [generate_compositions(singleton)[0], generate_compositions(twin)[0]]

    results = list(
        analyze_compositions_parallel_resilient(
            compositions, histories, max_workers=2
        )
    )

    assert len(results) == 2
    successful = [item for item in results if item[2] is None]
    failed = [item for item in results if item[2] is not None]
    assert len(successful) == 1
    assert len(failed) == 1
    assert successful[0][0].team.members[0].isin == "A"
    assert isinstance(failed[0][2], KeyError)
