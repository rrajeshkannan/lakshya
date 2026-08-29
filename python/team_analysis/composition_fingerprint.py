"""COMPOSITION-stage behavioural fingerprint.

A Composition earns fresh behavioural evidence from its weighted NAV
trajectory. It does not transform or inherit Team-level evidence.
"""

from __future__ import annotations

import pandas as pd

from lakshya_core.drawdown_severity import calculate_protection
from lakshya_core.elevation import calculate_elevation

from .composition import Composition


class CompositionFingerprint:
    """Behavioural evidence derived from a Composition NAV trajectory."""

    def __init__(self, composition: Composition, nav: pd.DataFrame) -> None:
        self.composition = composition
        self.elevation = calculate_elevation(nav)
        self.protection = calculate_protection(nav)
