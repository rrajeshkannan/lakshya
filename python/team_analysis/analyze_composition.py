"""COMPOSITION-stage analysis for Lakshya."""

from collections.abc import Mapping

import pandas as pd

from .composition import Composition
from .composition_fingerprint import CompositionFingerprint
from .composition_timeline import build_composition_nav


def analyze_composition(
    composition: Composition,
    fund_histories: Mapping[str, pd.DataFrame],
) -> CompositionFingerprint:
    """Build a Composition trajectory and derive its fresh fingerprint."""

    nav = build_composition_nav(composition, fund_histories)
    return CompositionFingerprint(composition, nav)
