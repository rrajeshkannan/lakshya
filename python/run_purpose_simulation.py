"""Run Purpose staging simulations and preserve complete turn history."""
from __future__ import annotations

import argparse
from pathlib import Path

from family.review_surface import refresh_review_surface
from family.staging import initialize_staging, run_turn
from family.staging_history import snapshot_current_staging, write_turn_template

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def _directory(as_of: str) -> Path:
    return DATA_DIR / "reviews" / as_of / "purpose_staging"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("--as-of", required=True)

    p = sub.add_parser("snapshot")
    p.add_argument("--as-of", required=True)

    p = sub.add_parser("template")
    p.add_argument("--as-of", required=True)

    p = sub.add_parser("turn")
    p.add_argument("--as-of", required=True)
    p.add_argument("--input", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "init":
        directory = initialize_staging(args.as_of)
        refresh_review_surface(args.as_of)
        print(snapshot_current_staging(directory))
        return

    directory = _directory(args.as_of)
    if args.command == "snapshot":
        refresh_review_surface(args.as_of)
        print(snapshot_current_staging(directory))
        return

    if args.command == "template":
        print(write_turn_template(directory))
        return

    directory = run_turn(args.as_of, args.input)
    refresh_review_surface(args.as_of)
    print(snapshot_current_staging(directory, turn_input=args.input))


if __name__ == "__main__":
    main()
