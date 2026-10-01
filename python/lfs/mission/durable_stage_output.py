"""Atomic CSV outputs with mandatory durable completion provenance."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .stage_checkpoint import is_valid_completion_marker, write_completion_marker


def write_csv_checkpoint(
    path: Path,
    rows: list[dict],
    *,
    stage: str,
    as_of: str,
    inputs: dict[str, str] | None = None,
) -> int:
    """Atomically write a CSV and then atomically publish its completion marker."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame = pd.DataFrame(rows)
    frame.to_csv(temporary, index=False)
    temporary.replace(path)
    write_completion_marker(
        path,
        stage=stage,
        as_of=as_of,
        inputs=inputs,
        row_count=len(frame),
    )
    return len(frame)


def is_valid_csv_checkpoint(
    path: Path,
    *,
    stage: str,
    as_of: str,
    inputs: dict[str, str] | None = None,
) -> bool:
    """Return True only when both CSV and its completion marker are valid."""
    return is_valid_completion_marker(
        path,
        stage=stage,
        as_of=as_of,
        inputs=inputs,
    )


def load_csv_checkpoint(
    path: Path,
    *,
    stage: str,
    as_of: str,
    inputs: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Load a CSV only after its durable completion marker validates."""
    if not is_valid_csv_checkpoint(path, stage=stage, as_of=as_of, inputs=inputs):
        raise ValueError(f"Invalid or incomplete stage checkpoint: {path}")
    return pd.read_csv(path, keep_default_na=False)
