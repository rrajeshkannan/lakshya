"""Production FINAL-stage analysis."""

from .archival import ARCHIVE_SCHEMA_VERSION, archive_final_summaries
from .compromise_programming import (
    FINAL_CONTRACT_VERSION,
    DEFAULT_BOOTSTRAP_RESAMPLES,
    DEFAULT_BOOTSTRAP_SEED,
    FinalAnalysis,
    analyze_purpose,
    build_purpose_surface,
    distance_from_utopia,
    joint_l2_linf_frontier,
    leave_one_spoke_sensitivity,
    lnorm_sweep,
    score_compromises,
    write_analysis,
)

__all__ = [
    "ARCHIVE_SCHEMA_VERSION",
    "archive_final_summaries",
    "FINAL_CONTRACT_VERSION",
    "DEFAULT_BOOTSTRAP_RESAMPLES",
    "DEFAULT_BOOTSTRAP_SEED",
    "FinalAnalysis",
    "analyze_purpose",
    "build_purpose_surface",
    "distance_from_utopia",
    "joint_l2_linf_frontier",
    "leave_one_spoke_sensitivity",
    "lnorm_sweep",
    "score_compromises",
    "write_analysis",
]
