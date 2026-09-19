from decimal import Decimal

import pytest

from lts.formation_intent import build_formation_intent
from lts.models import FormationIntentRow


PURPOSES = """name,due,desired,monthly_plan
Retirement,2039-04-12,10000000,50000
Edu_A,2027-04-01,4300000,25000
"""

POSITIONS = """investor,folio,isin,units,nav,market_value,purpose
Amma,F1,AAA,10,60,600,Retirement
Appanna,F2,BBB,5,200,1000,Retirement
Amma,F3,CCC,20,100,2000,Edu_A
"""


def write_files(tmp_path):
    purposes = tmp_path / "purposes.csv"
    positions = tmp_path / "positions.csv"
    summaries = tmp_path / "purpose_summaries.csv"
    purposes.write_text(PURPOSES, encoding="utf-8")
    positions.write_text(POSITIONS, encoding="utf-8")
    summaries.write_text(
        'purpose,primary_winner\n'
        'Retirement,"AAA,BBB|AAA=0.6000,BBB=0.4000"\n'
        'Edu_A,CCC|CCC=1.0000\n',
        encoding="utf-8",
    )
    return purposes, positions, summaries


def test_build_formation_intent_uses_lps_capital_and_final_weights(tmp_path):
    purposes, positions, summaries = write_files(tmp_path)

    formation = build_formation_intent(
        purposes_path=purposes,
        positions_path=positions,
        purpose_summaries_path=summaries,
    )

    assert formation.rows == (
        FormationIntentRow("Edu_A", "CCC", Decimal("2000"), Decimal("1.0000")),
        FormationIntentRow("Retirement", "AAA", Decimal("1600"), Decimal("0.6000")),
        FormationIntentRow("Retirement", "BBB", Decimal("1600"), Decimal("0.4000")),
    )


def test_formation_intent_preserves_purpose_level_mapping(tmp_path):
    purposes, positions, summaries = write_files(tmp_path)
    summaries.write_text(
        'purpose,primary_winner\n'
        'Retirement,"AAA,BBB|AAA=0.6000,BBB=0.4000"\n'
        'Edu_A,"AAA,BBB|AAA=0.6000,BBB=0.4000"\n',
        encoding="utf-8",
    )

    formation = build_formation_intent(
        purposes_path=purposes,
        positions_path=positions,
        purpose_summaries_path=summaries,
    )

    assert [row.purpose for row in formation.rows] == [
        "Edu_A", "Edu_A", "Retirement", "Retirement"
    ]
    assert [row.isin for row in formation.rows] == ["AAA", "BBB", "AAA", "BBB"]


def test_missing_purpose_capital_is_not_invented(tmp_path):
    purposes, positions, summaries = write_files(tmp_path)
    purposes.write_text(
        "name,due,desired,monthly_plan\n"
        "Retirement,2039-04-12,10000000,50000\n"
        "Edu_A,2027-04-01,4300000,25000\n"
        "Home,2030-01-01,1000000,10000\n",
        encoding="utf-8",
    )
    summaries.write_text(
        'purpose,primary_winner\n'
        'Retirement,"AAA,BBB|AAA=0.6000,BBB=0.4000"\n'
        'Edu_A,CCC|CCC=1.0000\n'
        'Home,CCC|CCC=1.0000\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="no valued Position capital"):
        build_formation_intent(
            purposes_path=purposes,
            positions_path=positions,
            purpose_summaries_path=summaries,
        )


def test_purpose_and_final_must_match(tmp_path):
    purposes, positions, summaries = write_files(tmp_path)
    summaries.write_text(
        'purpose,primary_winner\n'
        'Retirement,"AAA,BBB|AAA=0.6000,BBB=0.4000"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Purpose/FINAL mismatch"):
        build_formation_intent(
            purposes_path=purposes,
            positions_path=positions,
            purpose_summaries_path=summaries,
        )


def test_invalid_composition_identity_is_rejected(tmp_path):
    purposes, positions, summaries = write_files(tmp_path)
    summaries.write_text(
        'purpose,primary_winner\n'
        'Retirement,invalid\n'
        'Edu_A,CCC|CCC=1.0000\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid Composition identity"):
        build_formation_intent(
            purposes_path=purposes,
            positions_path=positions,
            purpose_summaries_path=summaries,
        )
