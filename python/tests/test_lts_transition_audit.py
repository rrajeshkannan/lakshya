from dataclasses import replace
from decimal import Decimal

import pytest

from lts.models import FormationIntentRow, TargetFormation
from lts.position_bridge import LtsPosition, LtsPositionId
from lts.purpose_transition import (
    TransitionSourceKind,
    TransitionMapping,
    build_purpose_transition_plan,
)
from lts.transition_audit import audit_transition_mapping


def position(investor, folio, isin, value, purpose="Edu_A"):
    return LtsPosition(
        id=LtsPositionId(investor, folio, isin, "Slice-1"),
        units=Decimal("1"),
        market_value=Decimal(value),
        purpose=purpose,
    )


def formation(*rows):
    return TargetFormation(rows=tuple(rows))


def row(purpose, isin, capital, weight):
    return FormationIntentRow(
        purpose=purpose,
        isin=isin,
        target_capital=Decimal(capital),
        target_weight=Decimal(weight),
    )


def test_valid_transition_mapping_passes_audit():
    positions = [
        position("I1", "F1", "AAA", "60"),
        position("I1", "F2", "CCC", "40"),
    ]
    target = formation(
        row("Edu_A", "AAA", "100", "0.6"),
        row("Edu_A", "BBB", "100", "0.4"),
    )
    plan = build_purpose_transition_plan(positions, target)

    audit_transition_mapping(positions, target, plan)


def test_audit_rejects_incompletely_mapped_source():
    positions = [position("I1", "F1", "CCC", "100")]
    target = formation(row("Edu_A", "AAA", "100", "1"))
    plan = build_purpose_transition_plan(positions, target)
    incomplete = replace(plan, mappings=plan.mappings[:-1])

    with pytest.raises(ValueError, match="Source position is not fully mapped"):
        audit_transition_mapping(positions, target, incomplete)


def test_audit_rejects_unknown_source_position():
    positions = [position("I1", "F1", "AAA", "100")]
    target = formation(row("Edu_A", "AAA", "100", "1"))
    plan = build_purpose_transition_plan(positions, target)
    unknown_id = LtsPositionId("I9", "F9", "ZZZ", "Slice-1")
    unknown_mapping = TransitionMapping(
        purpose="Edu_A",
        source_position_id=unknown_id,
        source_isin="ZZZ",
        source_kind=TransitionSourceKind.REDEMPTION_PROCEEDS,
        destination_isin="AAA",
        amount=Decimal("100"),
    )
    tampered = replace(plan, mappings=(unknown_mapping,))

    with pytest.raises(ValueError, match="unknown source position"):
        audit_transition_mapping(positions, target, tampered)


def test_audit_rejects_purpose_ownership_change():
    positions = [position("I1", "F1", "AAA", "100", purpose="Edu_A")]
    target = formation(row("Edu_A", "AAA", "100", "1"))
    plan = build_purpose_transition_plan(positions, target)
    tampered_mapping = replace(plan.mappings[0], purpose="Retirement")
    tampered = replace(plan, mappings=(tampered_mapping,))

    with pytest.raises(ValueError, match="Purpose ownership"):
        audit_transition_mapping(positions, target, tampered)


def test_audit_rejects_inconsistent_lock_annotation():
    source = position("I1", "F1", "CCC", "100")
    target = formation(row("Edu_A", "AAA", "100", "1"))
    plan = build_purpose_transition_plan([source], target, locked_position_ids={source.id})
    tampered_mapping = replace(plan.mappings[0], locked=False)
    tampered = replace(plan, mappings=(tampered_mapping,))

    with pytest.raises(ValueError, match="Locked redemption source"):
        audit_transition_mapping([source], target, tampered)


def test_audit_rejects_source_isin_mismatch():
    source = position("I1", "F1", "CCC", "100")
    target = formation(row("Edu_A", "AAA", "100", "1"))
    plan = build_purpose_transition_plan([source], target)
    tampered = replace(plan, mappings=(replace(plan.mappings[0], source_isin="WRONG"),))

    with pytest.raises(ValueError, match="source ISIN"):
        audit_transition_mapping([source], target, tampered)


def test_audit_rejects_duplicate_physical_sources():
    source = position("I1", "F1", "CCC", "100")
    target = formation(row("Edu_A", "AAA", "100", "1"))
    plan = build_purpose_transition_plan([source], target)
    with pytest.raises(ValueError, match="Duplicate physical source"):
        audit_transition_mapping([source, source], target, plan)
