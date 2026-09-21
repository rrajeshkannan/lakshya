"""Lakshya Transition System domain and analytical components."""

from .current_input import CurrentInput, CurrentInputDiagnostics, classify_current_positions
from .evidence import TransitionEvidence, TransitionEvidencePosition, build_transition_evidence
from .formation_intent import build_formation_intent
from .fund_metadata import FundClassification, TransitionFundMetadata, classify_fund, project_fund_metadata
from .models import EconomicReconciliation, FormationIntentRow, PositionReconciliation, TargetFormation
from .position_bridge import LtsPosition, LtsPositionId, bridge_positions, validate_slice_percentages
from .reconciliation import reconcile_economically, reconcile_positions
from .physical_transaction_history import transactions_for_holding
from .holding_history import HoldingHistory, holding_history
from .lots import HoldingLot, fifo_holding_lots
from .redemption import FifoRedemptionAllocation, fifo_redemption_allocations
from .holding_constraints import HoldingConstraintAnalysis, HoldingTaxConstraint, LotTaxAnalysis, analyze_holding
from .constraint_factory import holding_constraint_for_fund
from .holding_availability import HoldingAvailability, LockedLotAvailability, summarize_holding_availability
from .availability_report import build_holding_availability_report
from .treatments import TransitionTreatment, classify_position_treatment
from .purpose_allocation import validate_purpose_target_allocation
from .purpose_transition import (
    PurposeTransitionBalance,
    PurposeTransitionPlan,
    PurposeTransitionRow,
    TransitionDisposition,
    TransitionMapping,
    TransitionSourceKind,
    build_purpose_transition_plan,
)
from .transition_audit import audit_transition_mapping
from .purpose_transition_report import PurposeTransitionReport, build_purpose_transition_report
from .transition_export import (
    DEFAULT_TEMPORAL_ROOT,
    export_transition_mapping_csv,
    persist_transition_mapping_csv,
    write_transition_mapping_csv,
)


_RUNNER_EXPORTS = {
    "DEFAULT_LTS_CANONICAL_ROOT",
    "DEFAULT_LTS_OUTPUT_ROOT",
    "LtsRunResult",
    "persist_lts_run_artifacts",
    "promote_lts_run_artifacts",
    "run_lts_transition",
}


def __getattr__(name: str):
    """Load runner exports lazily so ``python -m lts.runner`` stays warning-free."""
    if name in _RUNNER_EXPORTS:
        from .runner import (
            DEFAULT_LTS_CANONICAL_ROOT,
            DEFAULT_LTS_OUTPUT_ROOT,
            LtsRunResult,
            persist_lts_run_artifacts,
            promote_lts_run_artifacts,
            run_lts_transition,
        )

        return {
            "DEFAULT_LTS_CANONICAL_ROOT": DEFAULT_LTS_CANONICAL_ROOT,
            "DEFAULT_LTS_OUTPUT_ROOT": DEFAULT_LTS_OUTPUT_ROOT,
            "LtsRunResult": LtsRunResult,
            "persist_lts_run_artifacts": persist_lts_run_artifacts,
            "promote_lts_run_artifacts": promote_lts_run_artifacts,
            "run_lts_transition": run_lts_transition,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CurrentInput", "CurrentInputDiagnostics", "classify_current_positions",
    "EconomicReconciliation", "FormationIntentRow", "PositionReconciliation",
    "TransitionEvidence", "TransitionEvidencePosition", "build_transition_evidence",
    "LtsPosition", "LtsPositionId", "bridge_positions", "validate_slice_percentages",
    "TargetFormation", "TransitionTreatment", "classify_position_treatment",
    "build_formation_intent", "reconcile_economically", "reconcile_positions",
    "transactions_for_holding", "HoldingHistory", "holding_history",
    "HoldingLot", "fifo_holding_lots",
    "FifoRedemptionAllocation", "fifo_redemption_allocations",
    "FundClassification", "TransitionFundMetadata", "classify_fund", "project_fund_metadata",
    "HoldingConstraintAnalysis", "HoldingTaxConstraint", "LotTaxAnalysis", "analyze_holding",
    "holding_constraint_for_fund",
    "HoldingAvailability", "LockedLotAvailability", "summarize_holding_availability",
    "build_holding_availability_report",
    "validate_purpose_target_allocation",
    "PurposeTransitionBalance", "PurposeTransitionPlan", "PurposeTransitionRow",
    "TransitionDisposition", "TransitionMapping", "TransitionSourceKind",
    "build_purpose_transition_plan", "audit_transition_mapping",
    "PurposeTransitionReport", "build_purpose_transition_report",
    "DEFAULT_TEMPORAL_ROOT", "export_transition_mapping_csv",
    "persist_transition_mapping_csv", "write_transition_mapping_csv",
    "DEFAULT_LTS_CANONICAL_ROOT", "DEFAULT_LTS_OUTPUT_ROOT",
    "LtsRunResult", "persist_lts_run_artifacts", "promote_lts_run_artifacts", "run_lts_transition",
]
