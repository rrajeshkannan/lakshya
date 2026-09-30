"""Reconcile the LPS transition manifest against later CAMS redemptions."""

from __future__ import annotations

from pathlib import Path

from .reconciliation import (
    DEFAULT_MANIFEST_PATH,
    DEFAULT_POSITIONS_PATH,
    DEFAULT_TRANSACTIONS_PATH,
    PROJECT_ROOT,
    reconcile,
)


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def main() -> None:
    result = reconcile()
    if not result.manifest_present:
        print(f"No transition manifest at {_relative(DEFAULT_MANIFEST_PATH)}. Reconciliation skipped.")
        return
    print(f"transition_manifest: {_relative(DEFAULT_MANIFEST_PATH)}")
    print(f"positions: {_relative(DEFAULT_POSITIONS_PATH)}")
    print(f"transactions: {_relative(DEFAULT_TRANSACTIONS_PATH)}")
    print(f"manifest_id: {result.manifest_id}")
    print(f"as_of: {result.as_of}")
    print(f"Orders: {result.order_count}")
    print(f"Fulfilled this run: {result.fulfilled_this_run}")
    print(f"Fulfilled: {result.fulfilled}")
    print(f"Pending: {result.pending}")
    print(f"Positions updated: {'yes' if result.positions_changed else 'no'}")


if __name__ == "__main__":
    main()


__all__ = ["main"]
