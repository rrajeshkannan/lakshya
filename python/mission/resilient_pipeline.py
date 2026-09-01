
from .achievability_interpretation import AchievabilityStatus, assess_achievability
from .durable_stage_output import (
    is_valid_csv_checkpoint,
    load_csv_checkpoint,
    write_csv_checkpoint,
)
from .models import Purpose
from .survivor_trajectory_experiment import observe_survivors_for_purpose

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
NAV_DIR = DATA_DIR / "nav"
PURPOSES_PATH = DATA_DIR / "purpose" / "purposes.csv"
FINGERPRINT_DIR = DATA_DIR / "fingerprints" / "composition"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_PATH = OUTPUT_DIR / "trajectory_pipeline.log"
MANIFEST_PATH = OUTPUT_DIR / "pipeline_run_manifest.json"

_RUN_MANIFEST: dict | None = None


def _wall_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _console(message: str) -> None:
    print(f"[trajectory-runner] {message}", flush=True)


def _detail(message: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{_wall_timestamp()} | {message}\n")
        handle.flush()


def _log(message: str) -> None:
    _console(message)


def _event(message: str) -> None:
    """Write a forensic event without echoing it to the console."""
    _detail(message)


def _write_manifest() -> None:
    if _RUN_MANIFEST is None:
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(MANIFEST_PATH.suffix + ".tmp")