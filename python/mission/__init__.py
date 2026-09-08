"""MISSION-stage analysis for Lakshya."""

from .models import Mission, Purpose
from .purpose_loader import load_purposes

# Keep the existing resilient runner as the execution engine while making its
# Purpose boundary consume the authoritative LPS-backed loader.
from . import resilient_pipeline as _resilient_pipeline

_resilient_pipeline._load_purposes = load_purposes

__all__ = ["Mission", "Purpose", "load_purposes"]
