from datetime import date
import json

from lakshya_core.models import (
    Goal,
    Fund,
    ElevationEvidence,
    ProtectionEvidence,
    ResilienceEvidence,
    FundBehaviouralFingerprint,
)
from fund_analysis.fingerprint_serialization import fingerprint_to_dict


def test_goal_can_be_created():
    goal = Goal(
        name="Retirement",
        purpose="Lifetime financial independence",
        target_corpus=8_50_00_000,
        target_date=date(2039, 4, 30),
        flexibility="low",
        consequence_of_shortfall="high",
        lifecycle="accumulation",
    )

    assert goal.name == "Retirement"
    assert goal.target_corpus == 8_50_00_000


def test_fund_behavioural_fingerprint_can_be_serialized_to_evidence_dict():
    fund = Fund(
        name="Test Fund",
        isin="TEST123",
        category="Flexi Cap",
    )

    fingerprint = FundBehaviouralFingerprint(
        fund=fund,
        elevation=ElevationEvidence(
            rolling_3y=None,
            rolling_5y=None,
            rolling_7y=None,
            rolling_10y=None,
        ),
        protection=ProtectionEvidence(
            observations=4,
            median_severity_pct=10.0,
            percentile_75_severity_pct=12.5,
            percentile_90_severity_pct=15.0,
            percentile_95_severity_pct=17.5,
            percentile_99_severity_pct=19.0,
            maximum_severity_pct=20.0,
            days_at_or_above_threshold={},
            pct_days_at_or_above_threshold={},
        ),
        resilience=ResilienceEvidence(
            episode_count=2,
            recovered_count=1,
            ongoing_count=1,
            median_depth_pct=20.0,
            worst_depth_pct=30.0,
            median_decline_days_recovered=30.0,
            median_recovery_days=60.0,
            median_underwater_days_recovered=90.0,
            median_underwater_days_ongoing=120.0,
            episodes=[],
        ),
    )

    evidence = fingerprint_to_dict(fingerprint)

    assert evidence["fund"]["name"] == "Test Fund"
    assert evidence["fund"]["isin"] == "TEST123"
    assert evidence["fund"]["category"] == "Flexi Cap"

    assert "elevation" in evidence
    assert "protection" in evidence
    assert "resilience" in evidence

    assert evidence["protection"]["median_severity_pct"] == 10.0
    assert evidence["resilience"]["episode_count"] == 2


def test_fund_behavioural_fingerprint_serialization_is_json_safe():
    fund = Fund(
        name="Test Fund",
        isin="TEST123",
        category="Flexi Cap",
    )

    fingerprint = FundBehaviouralFingerprint(
        fund=fund,
        elevation=ElevationEvidence(
            rolling_3y=None,
            rolling_5y=None,
            rolling_7y=None,
            rolling_10y=None,
        ),
        protection=ProtectionEvidence(
            observations=0,
            median_severity_pct=0.0,
            percentile_75_severity_pct=0.0,
            percentile_90_severity_pct=0.0,
            percentile_95_severity_pct=0.0,
            percentile_99_severity_pct=0.0,
            maximum_severity_pct=0.0,
            days_at_or_above_threshold={},
            pct_days_at_or_above_threshold={},
        ),
        resilience=ResilienceEvidence(
            episode_count=0,
            recovered_count=0,
            ongoing_count=0,
            median_depth_pct=0.0,
            worst_depth_pct=0.0,
            median_decline_days_recovered=0.0,
            median_recovery_days=0.0,
            median_underwater_days_recovered=0.0,
            median_underwater_days_ongoing=0.0,
            episodes=[],
        ),
    )

    evidence = fingerprint_to_dict(fingerprint)

    json.dumps(evidence)
