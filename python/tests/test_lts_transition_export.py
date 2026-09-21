from decimal import Decimal

from lts.position_bridge import LtsPositionId
from lts.purpose_transition import (
    TransitionMapping,
    TransitionSourceKind,
    PurposeTransitionPlan,
    PurposeTransitionBalance,
)
from lts.transition_export import (
    export_transition_mapping_csv,
    persist_transition_mapping_csv,
)


def _plan():
    source_id = LtsPositionId("I1", "F1", "AAA", "Slice-1")
    return PurposeTransitionPlan(
        rows=(),
        mappings=(
            TransitionMapping(
                purpose="Edu_A",
                source_position_id=source_id,
                source_isin="AAA",
                source_kind=TransitionSourceKind.LOCKED_REDEMPTION_PROCEEDS,
                destination_isin="BBB",
                amount=Decimal("40.5000"),
                locked=True,
            ),
        ),
        balances=(
            PurposeTransitionBalance(
                purpose="Edu_A",
                current_amount=Decimal("40.5"),
                target_amount=Decimal("40.5"),
                mapped_source_amount=Decimal("40.5"),
                mapped_destination_amount=Decimal("40.5"),
                unallocated_source_amount=Decimal("0"),
                unfunded_target_amount=Decimal("0"),
            ),
        ),
    )


def test_transition_mapping_csv_export_is_deterministic_and_escaped():
    assert export_transition_mapping_csv(_plan()) == (
        "purpose,source_position_id,source_isin,source_kind,destination_isin,amount,locked\n"
        'Edu_A,"LtsPositionId(investor=\'I1\', folio=\'F1\', isin=\'AAA\', slice=\'Slice-1\')",AAA,'
        "LOCKED_REDEMPTION_PROCEEDS,BBB,40.5000,true\n"
    )


def test_persist_transition_mapping_csv_uses_temporal_lts_location(tmp_path):
    destination = persist_transition_mapping_csv(
        _plan(),
        as_of="2026-09-21",
        run_id="run-001",
        root=tmp_path / "data" / "lts",
    )

    assert destination == (
        tmp_path / "data" / "lts" / "transition_mappings" / "2026-09-21_run-001.csv"
    )
    assert destination.read_text(encoding="utf-8").startswith(
        "purpose,source_position_id,source_isin,source_kind"
    )
