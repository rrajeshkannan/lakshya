"""Run one human-in-the-loop Purpose staging turn or commit the staged review."""
from __future__ import annotations

import argparse
from pathlib import Path

from family.staging import commit_staging, initialize_staging, run_turn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("--as-of", required=True)
    p = sub.add_parser("turn")
    p.add_argument("--as-of", required=True)
    p.add_argument("--input", required=True, type=Path)
    p = sub.add_parser("commit")
    p.add_argument("--as-of", required=True)
    args = parser.parse_args()
    if args.command == "init":
        print(initialize_staging(args.as_of))
    elif args.command == "turn":
        print(run_turn(args.as_of, args.input))
    else:
        print(commit_staging(args.as_of))


if __name__ == "__main__":
    main()
