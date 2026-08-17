"""
Persistent NAV evidence for the Fund-stage application.

This module maintains the historical NAV observations acquired by
Lakshya from an external source.

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
    """
    Persistent JSON store for one Fund's NAV history.

    An artifact has one immutable identity:

        ISIN
        scheme code
        source

    Observations are persisted newest-first because incremental
    observations naturally prepend to the existing history.
    """

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
        """
        Create a new NAV evidence artifact.

        The target path must not already contain an artifact.
        """

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
        """
        Return the date of the newest persisted NAV observation.
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

        return pd.Timestamp(observations[0]["date"])

    def update(
        self,
        *,
        nav: pd.DataFrame,
        retrieved_at: str,
        isin: str | None = None,
    ) -> None:
        """
        Incrementally extend an existing NAV evidence artifact.

        Every incoming observation must be strictly newer than the
        artifact's current latest observation.

        Existing observations are never replaced.
        """

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
        payload["observations"] = (
            new_observations + existing_observations
        )

        self._write(payload)

    @staticmethod
    def _validate_nav(nav: pd.DataFrame) -> None:
        """
        Require the canonical date/nav representation expected by the store.
        """

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
            raise ValueError(
                "NAV evidence contains duplicate dates."
            )

    @staticmethod
    def _serialize_observations(
        nav: pd.DataFrame,
    ) -> list[dict]:
        """
        Convert canonical NAV observations to the persisted representation.

        Persisted dates use Lakshya's YYYY-MM-DD convention.
        """

        ordered = nav.sort_values(
            "date",
            ascending=False,
        )

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
