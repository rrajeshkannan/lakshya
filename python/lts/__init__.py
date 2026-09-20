"""Lakshya Transition System domain and analytical components."""

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

__all__ = [
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
]
