"""Human-in-the-loop Purpose Staging review gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from lfs.purpose_staging.staging import commit_staging, initialize_staging, run_turn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--as-of", required=True)
    turn = sub.add_parser("turn")
    turn.add_argument("--as-of", required=True)
    turn.add_argument("--input", required=True, type=Path)
    commit = sub.add_parser("commit")
    commit.add_argument("--as-of", required=True)
    args = parser.parse_args()
    if args.command == "init":
        print(initialize_staging(args.as_of))
    elif args.command == "turn":
        print(run_turn(args.as_of, args.input))
    else:
        print(commit_staging(args.as_of))


if __name__ == "__main__":
    main()
