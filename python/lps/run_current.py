"""Build and report LPS CURRENT valuation snapshots for family investors."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from lps.current import CurrentSnapshot, build_current_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"


def build_family_current(
    *,
    investor: str,
    valuation_as_of_date: date,
    data_root: Path = DATA_ROOT,
) -> CurrentSnapshot:
    """Build CURRENT from the investor's persisted LPS ledger and NAV evidence."""
    investor_root = data_root / "lps" / investor
    ledger_path = investor_root / "canonical_transactions.csv"
    nav_root = data_root / "nav"

    if not ledger_path.exists():
        raise FileNotFoundError(f"Canonical ledger not found: {ledger_path}")
    if not nav_root.exists():
        raise FileNotFoundError(f"NAV evidence directory not found: {nav_root}")

    return build_current_snapshot(
        investor=investor,
        ledger_path=ledger_path,
        nav_root=nav_root,
        valuation_as_of_date=valuation_as_of_date,
    )


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date {value!r}; expected YYYY-MM-DD."
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an LPS CURRENT valuation snapshot."
    )
    parser.add_argument("investors", nargs="+", help="Family investor names.")
    parser.add_argument(
        "--as-of",
        required=True,
        type=_parse_date,
        dest="valuation_as_of_date",
        help="Valuation as-of date (YYYY-MM-DD).",
    )
    args = parser.parse_args()

    for investor in args.investors:
        snapshot = build_family_current(
            investor=investor,
            valuation_as_of_date=args.valuation_as_of_date,
        )
        active = len(snapshot.valuations)
        print(f"{investor}: CURRENT as of {snapshot.valuation_as_of_date}")
        print(f"  transactions through: {snapshot.transaction_through_date}")
        print(f"  current states:       {len(snapshot.current_states)}")
        print(f"  active positions:     {active}")
        print(f"  total market value:   {snapshot.total_market_value}")
        print()


if __name__ == "__main__":
    main()
