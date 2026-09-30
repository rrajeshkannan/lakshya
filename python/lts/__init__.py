"""Lakshya Transition System domain and analytical components."""

from .current_input import CurrentInput, CurrentInputDiagnostics, classify_current_positions
from .formation_intent import build_formation_intent
from .fund_metadata import FundClassification, TransitionFundMetadata, classify_fund, project_fund_metadata
from .lots import HoldingLot, fifo_holding_lots
from .models import FormationIntentRow, TargetFormation, TransitionDisposition
from .physical_transaction_history import transactions_for_holding
from .position_bridge import (
    DEFAULT_SLICE,
    LtsPosition,
    LtsPositionId,
    SliceOwnership,
    bridge_positions,
    build_owned_positions,
    validate_slice_percentages,
)
from .purpose_allocation import validate_purpose_target_allocation


_RUNNER_EXPORTS = {
    "DEFAULT_LTS_ROOT",
    "DEFAULT_POSITIONS_PATH",
    "DEFAULT_PURPOSES_PATH",
    "DEFAULT_PURPOSE_SUMMARIES_PATH",
    "LtsRunResult",
    "persist_lts_artifacts",
    "run_lts_transition",
}


def __getattr__(name: str):
    """Load runner exports lazily so ``python -m lts.runner`` stays warning-free."""
    if name in _RUNNER_EXPORTS:
        from .runner import (
            DEFAULT_LTS_ROOT,
            DEFAULT_POSITIONS_PATH,
            DEFAULT_PURPOSES_PATH,
            DEFAULT_PURPOSE_SUMMARIES_PATH,
            LtsRunResult,
            persist_lts_artifacts,
            run_lts_transition,
        )

        return {
            "DEFAULT_LTS_ROOT": DEFAULT_LTS_ROOT,
            "DEFAULT_POSITIONS_PATH": DEFAULT_POSITIONS_PATH,
            "DEFAULT_PURPOSES_PATH": DEFAULT_PURPOSES_PATH,
            "DEFAULT_PURPOSE_SUMMARIES_PATH": DEFAULT_PURPOSE_SUMMARIES_PATH,
            "LtsRunResult": LtsRunResult,
            "persist_lts_artifacts": persist_lts_artifacts,
            "run_lts_transition": run_lts_transition,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CurrentInput", "CurrentInputDiagnostics", "classify_current_positions",
    "FormationIntentRow", "TargetFormation", "TransitionDisposition",
    "DEFAULT_SLICE", "LtsPosition", "LtsPositionId", "SliceOwnership",
    "bridge_positions", "build_owned_positions", "validate_slice_percentages",
    "build_formation_intent",
    "transactions_for_holding",
    "HoldingLot", "fifo_holding_lots",
    "FundClassification", "TransitionFundMetadata", "classify_fund", "project_fund_metadata",
    "validate_purpose_target_allocation",
    "DEFAULT_LTS_ROOT", "DEFAULT_POSITIONS_PATH", "DEFAULT_PURPOSES_PATH",
    "DEFAULT_PURPOSE_SUMMARIES_PATH", "LtsRunResult", "persist_lts_artifacts",
    "run_lts_transition",
]
