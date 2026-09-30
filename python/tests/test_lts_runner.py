from datetime import date
from decimal import Decimal

from lts.models import TransitionDisposition
from lts.runner import persist_lts_artifacts, run_lts_transition


PURPOSES = """name,due,desired,monthly_plan
Retirement,2039-04-12,10000000,50000
Edu_A,2027-04-01,4300000,25000
"""

POSITIONS = """investor,folio,isin,units,nav,market_value,purpose
Amma,F1,AAA,10,60,600,Retirement
Appanna,F2,BBB,5,200,1000,Retirement
Amma,F3,CCC,20,100,2000,Edu_A
"""

SUMMARIES = (
    "purpose,primary_winner\n"
    'Retirement,"AAA,BBB|AAA=0.6000,BBB=0.4000"\n'
    "Edu_A,CCC|CCC=1.0000\n"
)


def test_runner_composes_the_cascade(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    purposes.write_text(PURPOSES, encoding="utf-8")
    positions.write_text(POSITIONS, encoding="utf-8")
    summaries.write_text(SUMMARIES, encoding="utf-8")

    result = run_lts_transition(
        purposes_path=purposes,
        positions_path=positions,
        purpose_summaries_path=summaries,
    )

    assert result.lot_locks_applied is False
    assert result.current_input.diagnostics.total_records == 3
    assert result.current_input.diagnostics.active_records == 3
    assert result.current_input.diagnostics.inactive_records == 0
    assert sum(item.market_value for item in result.cascade.slices) == Decimal("3600")
    assert {item.disposition for item in result.cascade.slices} <= {
        TransitionDisposition.RETAIN,
        TransitionDisposition.REDEEM,
    }


def test_runner_excludes_zero_unit_inactive_records(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    purposes.write_text(PURPOSES, encoding="utf-8")
    positions.write_text(
        POSITIONS.replace(
            "Amma,F3,CCC,20,100,2000,Edu_A",
            "Amma,F3,CCC,20,100,2000,Edu_A\nAmma,F4,DDD,0,,,",
        ),
        encoding="utf-8",
    )
    summaries.write_text(SUMMARIES, encoding="utf-8")

    result = run_lts_transition(
        purposes_path=purposes,
        positions_path=positions,
        purpose_summaries_path=summaries,
    )

    assert result.current_input.diagnostics.total_records == 4
    assert result.current_input.diagnostics.active_records == 3
    assert result.current_input.diagnostics.inactive_records == 1
    assert [position.id.isin for position in result.positions] == ["AAA", "BBB", "CCC"]


def test_runner_rejects_unattributed_positions(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    purposes.write_text(PURPOSES, encoding="utf-8")
    positions.write_text(
        POSITIONS.replace("Amma,F3,CCC,20,100,2000,Edu_A", "Amma,F3,CCC,20,100,2000,"),
        encoding="utf-8",
    )
    summaries.write_text(SUMMARIES, encoding="utf-8")

    import pytest

    with pytest.raises(ValueError, match="no Purpose attribution"):
        run_lts_transition(
            purposes_path=purposes,
            positions_path=positions,
            purpose_summaries_path=summaries,
        )


def test_persist_writes_only_active_artifacts(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    purposes.write_text(PURPOSES, encoding="utf-8")
    positions.write_text(POSITIONS, encoding="utf-8")
    summaries.write_text(SUMMARIES, encoding="utf-8")
    result = run_lts_transition(
        purposes_path=purposes,
        positions_path=positions,
        purpose_summaries_path=summaries,
        as_of=date(2026, 9, 6),
    )

    output = tmp_path / "lts"
    written = persist_lts_artifacts(result, as_of="2026-09-06", lts_root=output)
    names = {path.name for path in output.iterdir()}
    assert names == {
        "materialized_transition_slices.csv",
        "cascade_review.csv",
        "execution_playbook.csv",
        "manifest.json",
    }
    assert "tax_preflight_report" not in written
    assert "purpose_reports.csv" not in names
    assert "transition_mappings.csv" not in names
    assert "holding_availability.csv" not in names
    assert "holding_availability_summary.csv" not in names
