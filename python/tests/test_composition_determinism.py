from pathlib import Path

import pandas as pd

from lakshya_core.models import Fund
from team_analysis.analyze_composition import analyze_composition
from team_analysis.composition import Composition, composition_identity
from team_analysis.composition_fingerprint_store import (
    fingerprint_to_payload,
    load_fingerprint,
    persist_fingerprint,
)
from team_analysis.composition_pipeline import analyze_compositions_parallel
from team_analysis.team import Team


def _fund(isin: str) -> Fund:
    return Fund(name=f"Fund {isin}", isin=isin, category="Test")


def _fixture():
    funds = {_isin: _fund(_isin) for _isin in ("A", "B")}
    dates = pd.date_range("2010-01-01", periods=30, freq="D")
    histories = {
        "A": pd.DataFrame({"date": dates, "nav": [100.0 + i for i in range(30)]}),
        "B": pd.DataFrame({"date": dates, "nav": [100.0 + 2.0 * i for i in range(30)]}),
    }
    compositions = [
        Composition(team=Team(members=(funds["A"],)), weights={"A": 1.0}),
        Composition(
            team=Team(members=(funds["A"], funds["B"])),
            weights={"A": 0.25, "B": 0.75},
        ),
    ]
    return funds, histories, compositions


def _payloads(pairs):
    return {
        composition_identity(composition): fingerprint_to_payload(fingerprint)
        for composition, fingerprint in pairs
    }


def test_serial_and_parallel_computation_are_equivalent():
    _, histories, compositions = _fixture()

    serial = [
        (composition, analyze_composition(
            composition,
            {member.isin: histories[member.isin] for member in composition.team.members},
        ))
        for composition in compositions
    ]
    parallel = list(
        analyze_compositions_parallel(
            compositions,
            histories,
            max_workers=2,
            max_in_flight=2,
        )
    )

    assert _payloads(serial) == _payloads(parallel)


def test_repeated_parallel_computation_is_deterministic():
    _, histories, compositions = _fixture()

    first = list(
        analyze_compositions_parallel(compositions, histories, max_workers=2, max_in_flight=2)
    )
    second = list(
        analyze_compositions_parallel(compositions, histories, max_workers=2, max_in_flight=2)
    )

    assert _payloads(first) == _payloads(second)


def test_persisted_and_reloaded_fingerprint_is_identical(tmp_path: Path):
    _, histories, compositions = _fixture()
    composition = compositions[1]
    fingerprint = analyze_composition(
        composition,
        {member.isin: histories[member.isin] for member in composition.team.members},
    )

    path = persist_fingerprint(fingerprint, tmp_path)
    restored = load_fingerprint(path, composition)

    assert fingerprint_to_payload(restored) == fingerprint_to_payload(fingerprint)
