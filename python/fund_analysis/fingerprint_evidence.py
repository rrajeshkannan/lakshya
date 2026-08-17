"""
Persistent Fund behavioural-fingerprint evidence.

This module persists the output of the Fund-stage behavioural engine.

The fingerprint contains only observed behavioural evidence:

    Elevation
    Protection
    Resilience

It contains no score, ranking, suitability judgement, or recommendation.

Each fingerprint records the NAV evidence artifact version from which
it was generated, preserving analytical lineage.
"""

import json
from pathlib import Path
from typing import Any


class FingerprintEvidenceStore:
    """
    Persistent JSON store for one Fund behavioural fingerprint.

    A fingerprint artifact is created once for a particular analysis
    state. Existing artifacts are never silently overwritten.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    def create(
        self,
        *,
        fingerprint: dict[str, Any],
        nav_artifact_version: int,
        generated_at: str,
    ) -> None:
        """
        Create a persistent Fund fingerprint artifact.

        The target path must not already contain an artifact.
        """

        if self.path.exists():
            raise ValueError(
                f"Fingerprint evidence artifact already exists: {self.path}"
            )

        self._validate_fingerprint(fingerprint)

        payload = {
            "artifact_version": 1,
            "nav_artifact_version": int(nav_artifact_version),
            "generated_at": generated_at,
            "fund": fingerprint["fund"],
            "elevation": fingerprint["elevation"],
            "protection": fingerprint["protection"],
            "resilience": fingerprint["resilience"],
        }

        self._write(payload)

    @staticmethod
    def _validate_fingerprint(
        fingerprint: dict[str, Any],
    ) -> None:
        required_dimensions = {
            "fund",
            "elevation",
            "protection",
            "resilience",
        }

        missing = required_dimensions - set(fingerprint)

        if missing:
            raise ValueError(
                "Fingerprint evidence is missing required dimensions: "
                f"{sorted(missing)}"
            )

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                payload,
                f,
                indent=2,
            )
            f.write("\n")
