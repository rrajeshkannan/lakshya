"""Persist LPS CURRENT snapshots as durable JSON artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from lps.current import CurrentSnapshot


def _json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return _json_value(asdict(value))
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def persist_current_snapshot(snapshot: CurrentSnapshot, root: Path) -> Path:
    """Write one immutable CURRENT snapshot for the snapshot valuation date."""
    path = Path(root) / snapshot.valuation_as_of_date.isoformat() / f"{snapshot.investor}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_value(snapshot), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


__all__ = ["persist_current_snapshot"]
