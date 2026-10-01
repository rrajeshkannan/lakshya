"""COMPOSITION-stage behavioural fingerprint.

A Composition earns fresh behavioural evidence from its weighted NAV
trajectory. It does not transform or inherit Team-level evidence.
"""

from __future__ import annotations

import pandas as pd

from lakshya_core.drawdown_severity import calculate_protection
from lakshya_core.elevation import calculate_elevation
from lakshya_core.models import ElevationEvidence, ProtectionEvidence

from .composition import Composition


class CompositionFingerprint:
    """Behavioural evidence derived from a Composition NAV trajectory."""

    def __init__(self, composition: Composition, nav: pd.DataFrame) -> None:
        self.composition = composition
        self.nav = nav.copy()
        self.elevation = calculate_elevation(self.nav)
        self.protection = calculate_protection(self.nav)

    @classmethod
    def from_persisted(
        cls,
        composition: Composition,
        nav: pd.DataFrame,
        elevation: ElevationEvidence,
        protection: ProtectionEvidence,
    ) -> "CompositionFingerprint":
        """Rehydrate complete evidence without recalculating any metric.

        This is intentionally separate from ``__init__``: normal construction
        means "compute fresh evidence", while rehydration means "trust the
        validated persisted evidence".  Keeping those paths explicit prevents
        a resume operation from accidentally repeating expensive analysis.
        """
        fingerprint = cls.__new__(cls)
        fingerprint.composition = composition
        fingerprint.nav = nav.copy()
        fingerprint.elevation = elevation
        fingerprint.protection = protection
        return fingerprint
