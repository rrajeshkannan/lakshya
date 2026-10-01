from datetime import date
from pathlib import Path

from lfs.layout import lfs_manifest_path, purpose_intent_path
from mission.purpose_loader import DATA_DIR, PURPOSES_PATH, load_purposes
from mission.resilient_pipeline import DATA_DIR as PIPELINE_DATA_DIR
from mission.resilient_pipeline import MANIFEST_PATH
from lps.reconciliation import DEFAULT_MANIFEST_PATH
from lts.runner import DEFAULT_LTS_ROOT, DEFAULT_PURPOSES_PATH, DEFAULT_TRANSITION_MANIFEST_PATH


def test_load_purposes_accepts_human_due_date_format(tmp_path: Path):
    purposes = tmp_path / "purposes.csv"
    purposes.write_text(
        "name,due,desired,monthly_plan\n"
        "Edu_B,01-Jan-2031,5500000,40000\n"
        "Kutti,NA,,\n",
        encoding="utf-8",
    )
    positions = tmp_path / "positions.csv"
    positions.write_text(
        "investor,folio,isin,units,nav,market_value,purpose\n"
        "Amma,F1,ISIN1,1,100,2400000,Edu_B\n"
        "Amma,F2,ISIN2,1,100,335000,Kutti\n",
        encoding="utf-8",
    )

    loaded = load_purposes(
        date(2026, 9, 8),
        purposes_path=purposes,
        positions_path=positions,
    )

    edu = next(p for p in loaded if p.name == "Edu_B")
    kutti = next(p for p in loaded if p.name == "Kutti")
    assert edu.due == date(2031, 1, 1)
    assert edu.horizon_years == 4
    assert edu.capital == 2400000
    assert kutti.due is None
    assert kutti.trajectory_horizon_years == 7
    assert kutti.capital == 335000


def test_purpose_intent_prefers_lfs_and_falls_back_to_legacy(tmp_path: Path):
    data = tmp_path / "data"
    legacy = data / "purpose" / "purposes.csv"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("name,due,desired,monthly_plan\n", encoding="utf-8")
    assert purpose_intent_path(data) == legacy

    canonical = data / "lfs" / "purpose.csv"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("name,due,desired,monthly_plan\n", encoding="utf-8")
    assert purpose_intent_path(data) == canonical
    assert PURPOSES_PATH == DATA_DIR / "lfs" / "purpose.csv"
    assert DEFAULT_PURPOSES_PATH == PURPOSES_PATH


def test_stage_manifests_stay_in_separate_directories():
    assert MANIFEST_PATH == lfs_manifest_path(PIPELINE_DATA_DIR)
    assert MANIFEST_PATH == PIPELINE_DATA_DIR / "lfs" / "manifest.json"
    assert DEFAULT_LTS_ROOT / "manifest.json" == PIPELINE_DATA_DIR / "lts" / "manifest.json"
    assert DEFAULT_TRANSITION_MANIFEST_PATH == DEFAULT_MANIFEST_PATH
    assert DEFAULT_MANIFEST_PATH == PIPELINE_DATA_DIR / "lps" / "transition_manifest.json"
    assert len({MANIFEST_PATH, DEFAULT_LTS_ROOT / "manifest.json", DEFAULT_MANIFEST_PATH}) == 3
