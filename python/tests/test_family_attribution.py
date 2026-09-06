from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from family.attribution import (
    ATTRIBUTION_SCHEMA_VERSION,
    build_family_attribution,
    load_fund_metadata,
    load_purpose_capital,
    parse_composition_identity,
    run_family_attribution,
)

A = "A"
B = "B"
C = "C"
A65_B30_C05 = "A,B,C|A=0.6500,B=0.3000,C=0.0500"
A85_B05_C10 = "A,B,C|A=0.8500,B=0.0500,C=0.1000"


def test_parse_composition_identity_requires_valid_complete_weights():
    assert parse_composition_identity(A65_B30_C05) == {A: 0.65, B: 0.30, C: 0.05}
    with pytest.raises(ValueError):
        parse_composition_identity("A,B|A=0.5")
    with pytest.raises(ValueError):
        parse_composition_identity("A,B|A=0.8,B=0.3")
    with pytest.raises(ValueError):
        parse_composition_identity("A,B|A=-0.1,B=1.1")


def test_build_attribution_reconciles_purpose_capital_and_family_capital():
    purposes = {"Edu": 1_000_000.0, "Retirement": 3_000_000.0}
    winners = {"Edu": A65_B30_C05, "Retirement": A85_B05_C10}
    metadata = {
        A: {"scheme_name": "Fund A", "amc": "AMC 1"},
        B: {"scheme_name": "Fund B", "amc": "AMC 1"},
        C: {"scheme_name": "Fund C", "amc": "AMC 2"},
    }

    rows = build_family_attribution(purposes, winners, metadata)

    assert len(rows["detail"]) == 6
    fund = {row["isin"]: row for row in rows["fund"]}
    assert float(fund[A]["attributed_capital"]) == pytest.approx(3_200_000.0)
    assert float(fund[A]["family_capital_pct"]) == pytest.approx(80.0)
    assert fund[A]["purpose_count"] == 2
    assert fund[A]["purposes"] == "Edu,Retirement"

    amc = {row["amc"]: row for row in rows["amc"]}
    assert float(amc["AMC 1"]["attributed_capital"]) == pytest.approx(3_400_000.0)
    assert float(amc["AMC 1"]["family_capital_pct"]) == pytest.approx(85.0)

    purpose = {row["purpose"]: row for row in rows["purpose"]}
    assert all(row["reconciles"] is True for row in purpose.values())


def test_build_attribution_requires_matching_purpose_sets():
    metadata = {A: {"scheme_name": "Fund A", "amc": "AMC"}}
    with pytest.raises(ValueError):
        build_family_attribution({"Edu": 100.0}, {}, metadata)


def test_build_attribution_rejects_unknown_fund():
    with pytest.raises(ValueError, match="unknown fund ISIN"):
        build_family_attribution(
            {"Edu": 100.0}, {"Edu": "Z|Z=1.0000"}, {A: {"scheme_name": "A", "amc": "AMC"}}
        )


def test_loaders_validate_authoritative_source_shapes(tmp_path: Path):
    purpose = tmp_path / "purposes.csv"
    purpose.write_text("name,value\nEdu,100\nRetirement,300\n", encoding="utf-8")
    assert load_purpose_capital(purpose) == {"Edu": 100.0, "Retirement": 300.0}

    metadata = tmp_path / "funds.csv"
    metadata.write_text(
        "isin,scheme_name,amc\nA,Fund A,AMC 1\nB,Fund B,AMC 2\n", encoding="utf-8"
    )
    assert load_fund_metadata(metadata)[A]["amc"] == "AMC 1"


def _write_review_fixture(root: Path) -> None:
    review = root / "2026-09-06"
    review.mkdir(parents=True)
    summaries = {
        "Edu": A65_B30_C05,
        "Retirement": A85_B05_C10,
    }
    manifest_items = []
    import hashlib

    for purpose, identity in summaries.items():
        text = (
            "purpose,purpose_horizon_years,primary_winner,contract_version\n"
            f"{purpose},7,\"{identity}\",1\n"
        )
        path = review / f"{purpose}_summary.csv"
        path.write_text(text, encoding="utf-8")
        digest = hashlib.sha256(text.encode()).hexdigest()
        manifest_items.append({
            "purpose": purpose,
            "summary_sha256": digest,
        })
    (review / "review_manifest.json").write_text(
        json.dumps({
            "archive_schema_version": 1,
            "as_of": "2026-09-06",
            "final_contract_version": "1",
            "purposes": manifest_items,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_run_family_attribution_persists_all_artifacts_and_log(tmp_path: Path):
    data = tmp_path / "data"
    purposes = data / "purpose" / "purposes.csv"
    funds = data / "fund" / "funds_in_scope_metadata.csv"
    purposes.parent.mkdir(parents=True)
    funds.parent.mkdir(parents=True)
    purposes.write_text("name,value\nEdu,1000000\nRetirement,3000000\n", encoding="utf-8")
    funds.write_text(
        "isin,scheme_name,amc\nA,Fund A,AMC 1\nB,Fund B,AMC 1\nC,Fund C,AMC 2\n",
        encoding="utf-8",
    )
    _write_review_fixture(data / "reviews")

    paths = run_family_attribution(
        "2026-09-06",
        data_dir=data,
    )

    names = {path.name for path in paths}
    assert names == {
        "family_capital_attribution.csv",
        "family_fund_concentration.csv",
        "family_amc_concentration.csv",
        "family_purpose_dependency.csv",
        "family_attribution_manifest.json",
    }
    review = data / "reviews" / "2026-09-06"
    assert (review / "family_attribution.log").is_file()
    assert "COMPLETE" in (review / "family_attribution.log").read_text(encoding="utf-8")

    with (review / "family_fund_concentration.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["isin"] == A
    assert float(rows[0]["family_capital_pct"]) == pytest.approx(80.0)

    manifest = json.loads((review / "family_attribution_manifest.json").read_text(encoding="utf-8"))
    assert manifest["attribution_schema_version"] == ATTRIBUTION_SCHEMA_VERSION
    assert manifest["optimization_or_guardrail"] is False


def test_run_family_attribution_rejects_tampered_archived_summary(tmp_path: Path):
    data = tmp_path / "data"
    purposes = data / "purpose" / "purposes.csv"
    funds = data / "fund" / "funds_in_scope_metadata.csv"
    purposes.parent.mkdir(parents=True)
    funds.parent.mkdir(parents=True)
    purposes.write_text("name,value\nEdu,100\n", encoding="utf-8")
    funds.write_text("isin,scheme_name,amc\nA,Fund A,AMC\n", encoding="utf-8")
    review = data / "reviews" / "2026-09-06"
    review.mkdir(parents=True)
    summary = review / "Edu_summary.csv"
    summary.write_text(
        "purpose,purpose_horizon_years,primary_winner,contract_version\nEdu,7,\"A|A=1.0000\",1\n",
        encoding="utf-8",
    )
    (review / "review_manifest.json").write_text(
        json.dumps({
            "archive_schema_version": 1,
            "as_of": "2026-09-06",
            "final_contract_version": "1",
            "purposes": [{"purpose": "Edu", "summary_sha256": "wrong"}],
        }),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        run_family_attribution("2026-09-06", data_dir=data)
