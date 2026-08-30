import pandas as pd

from team_analysis.composition_fingerprint import CompositionFingerprint
from team_analysis.composition import Composition
from team_analysis.team import Team
from lakshya_core.models import Fund


def test_fingerprint_exposes_the_same_raw_nav_used_for_derived_evidence():
    a = Fund(name="Fund A", isin="A", category="Test")
    composition = Composition(team=Team(members=(a,)), weights={"A": 1.0})
    nav = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2021-01-01"]),
            "nav": [100.0, 110.0],
        }
    )

    fingerprint = CompositionFingerprint(composition, nav)

    pd.testing.assert_frame_equal(fingerprint.nav, nav)
    assert fingerprint.nav is not nav
