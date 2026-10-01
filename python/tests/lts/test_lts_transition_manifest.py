import json
from datetime import date

from lts.runner import write_transition_manifest


def test_transition_manifest_inherits_lts_manifest_and_playbook_orders(tmp_path):
    lts_manifest = tmp_path / "manifest.json"
    lts_manifest.write_text(
        json.dumps({
            "as_of": "2026-09-06",
            "contract_version": 7,
            "artifacts": {"execution_playbook": "execution_playbook.csv"},
        }),
        encoding="utf-8",
    )
    playbook = tmp_path / "execution_playbook.csv"
    playbook.write_text(
        "source_investor,source_folio,source_isin,units_to_redeem,"
        "pct_of_folio_holding,target_investor,target_folio,target_isin,"
        "target_slice,purpose,execution_instruction\n"
        "Amma,F1,SRC,10.500,100.000000,Appanna,NEW_FOLIO_1,TGT,slice-1,Kutti,"
        "Redeem 10.500 units\n",
        encoding="utf-8",
    )
    destination = tmp_path / "transition_manifest.json"

    write_transition_manifest(
        lts_manifest_path=lts_manifest,
        playbook_path=playbook,
        destination=destination,
    )

    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document["as_of"] == "2026-09-06"
    assert document["manifest_id"] == "MAN-2026-09-06-01"
    assert document["contract_version"] == 7
    assert document["orders"] == [{
        "order_id": "ORD-001",
        "source_investor": "Amma",
        "source_folio": "F1",
        "source_isin": "SRC",
        "units_to_redeem": "10.500",
        "target_investor": "Appanna",
        "target_folio": "NEW_FOLIO_1",
        "target_isin": "TGT",
        "target_slice": "slice-1",
        "purpose": "Kutti",
        "status": "PENDING",
        "settled_at": None,
    }]
    assert date.fromisoformat(document["as_of"]) == date(2026, 9, 6)
