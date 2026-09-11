"""Run a Purpose staging simulation turn and preserve its complete history."""
from __future__ import annotations

import argparse
from pathlib import Path

from family.review_surface import refresh_review_surface
from family.staging import initialize_staging, run_turn
from family.staging_history import snapshot_current_staging


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("--as-of", required=True)

    p = sub.add_parser("turn")
    p.add_argument("--as-of", required=True)
    p.add_argument("--input", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "init":
        directory = initialize_staging(args.as_of)
    else:
        directory = run_turn(args.as_of, args.input)

    refresh_review_surface(args.as_of)
    snapshot = snapshot_current_staging(directory)
    print(snapshot)


if __name__ == "__main__":
    main()
