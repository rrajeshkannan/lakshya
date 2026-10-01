from lps.positions import PositionId
from lts.position_bridge import LtsPositionId


def test_bridge_slice_one_identity_matches_legacy_position_id():
    legacy_id = PositionId("Amma", "13393503", "INF879O01100")
    bridge_id = LtsPositionId("Amma", "13393503", "INF879O01100", "Slice-1")

    assert bridge_id == legacy_id
    assert legacy_id == bridge_id
    assert bridge_id in {legacy_id}


def test_non_primary_slice_does_not_match_legacy_position_id():
    legacy_id = PositionId("Amma", "13393503", "INF879O01100")
    slice_two_id = LtsPositionId("Amma", "13393503", "INF879O01100", "Slice-2")

    assert slice_two_id != legacy_id
    assert slice_two_id not in {legacy_id}
