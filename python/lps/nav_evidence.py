"""
Persistent NAV evidence for the Lakshya Position System.

This module maintains the historical NAV observations acquired by LPS
from an external source.

The store is deliberately separate from the NAV source:

    NAV source
        -> acquires observations

    NAV history gate
        -> validates observations

    NavEvidenceStore
        -> persists and incrementally extends observations

The store never rewrites an existing historical observation.
New observations must be strictly newer than the current latest
observation.
"""

import json
from pathlib import Path

import pandas as pd


class NavEvidenceStore:
    """Persistent JSON store for one Fund's NAV history."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def create(
        self,
        *,
        isin: str,
        scheme_code: int,
        source: str,
        nav: pd.DataFrame,
        retrieved_at: str,
    ) -> None:
        """Create a new NAV evidence artifact."""
        if self.path.exists():
            raise ValueError(
                f"NAV evidence artifact already exists: {self.path}"
            )

        self._validate_nav(nav)

        payload = {
            "artifact_version": 1,
            "isin": isin,
            "scheme_code": int(scheme_code),
            "source": source,
            "retrieved_at": retrieved_at,
            "observations": self._serialize_observations(nav),
        }
        self._write(payload)

    def latest_date(self) -> pd.Timestamp:
        """Return the date of the newest persisted NAV observation."""
        if not self.path.exists():
            raise ValueError(
                f"NAV evidence artifact does not exist: {self.path}"
            )

        payload = self._read()
        observations = payload["observations"]

        if not observations:
            raise ValueError(
                "NAV evidence artifact contains no observations."
            )

        return pd.Timestamp(observations[0]["date"])

    def as_of(self, as_of: pd.Timestamp) -> tuple[pd.Timestamp, float]:
        """
        Return the applicable NAV observation as of a requested date.

        The applicable observation is the latest recorded NAV on or before
        the requested date. Missing calendar days therefore use the most
        recent actual observation rather than manufacturing a NAV.

        Returns:
            A ``(observation_date, nav)`` tuple so callers retain both the
            value used and the factual date on which it was observed.
        """
        if not self.path.exists():
            raise ValueError(
                f"NAV evidence artifact does not exist: {self.path}"
            )

        payload = self._read()
        observations = payload["observations"]

        if not observations:
            raise ValueError(
                "NAV evidence artifact contains no observations."
            )

        requested_date = pd.Timestamp(as_of)

        for observation in observations:
            observation_date = pd.Timestamp(observation["date"])
            if observation_date <= requested_date:
                return observation_date, float(observation["nav"])

        raise ValueError(
            "NAV evidence artifact has no observation on or before "
            f"{requested_date.strftime('%Y-%m-%d')}."
        )

    def update(
        self,
        *,
        nav: pd.DataFrame,
        retrieved_at: str,
        isin: str | None = None,
    ) -> None:
        """Incrementally extend an existing NAV evidence artifact."""
        if not self.path.exists():
            raise ValueError(
                f"NAV evidence artifact does not exist: {self.path}"
            )

        self._validate_nav(nav)
        payload = self._read()

        if isin is not None and isin != payload["isin"]:
            raise ValueError(
                "NAV evidence identity does not match existing artifact."
            )

        existing_observations = payload["observations"]

        if not existing_observations:
            raise ValueError(
                "NAV evidence artifact contains no existing observations."
            )

        latest_existing_date = pd.Timestamp(
            existing_observations[0]["date"]
        )
        incoming_dates = pd.to_datetime(nav["date"])

        if not (incoming_dates > latest_existing_date).all():
            raise ValueError(
                "New NAV observations must be strictly newer than "
                "the existing latest observation."
            )

        new_observations = self._serialize_observations(nav)
        payload["artifact_version"] += 1
        payload["retrieved_at"] = retrieved_at
        payload["observations"] = new_observations + existing_observations
        self._write(payload)

    @staticmethod
    def _validate_nav(nav: pd.DataFrame) -> None:
        required_columns = {"date", "nav"}

        if not required_columns.issubset(nav.columns):
            raise ValueError(
                "NAV evidence is missing required columns: "
                f"{sorted(required_columns - set(nav.columns))}"
            )

        if nav.empty:
            raise ValueError("NAV evidence cannot be empty.")
        if nav["date"].isna().any():
            raise ValueError("NAV evidence contains missing dates.")
        if nav["nav"].isna().any():
            raise ValueError("NAV evidence contains missing NAV values.")
        if (nav["nav"] <= 0).any():
            raise ValueError("NAV values must be strictly positive.")
        if nav["date"].duplicated().any():
            raise ValueError("NAV evidence contains duplicate dates.")

    @staticmethod
    def _serialize_observations(nav: pd.DataFrame) -> list[dict]:
        ordered = nav.sort_values("date", ascending=False)
        return [
            {
                "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
                "nav": float(row["nav"]),
            }
            for _, row in ordered.iterrows()
        ]

    def _read(self) -> dict:
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
