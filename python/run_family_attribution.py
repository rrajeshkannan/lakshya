"""Run the post-FINAL Family Architecture Validation attribution layer."""

from __future__ import annotations

import argparse

from family.attribution import run_family_attribution


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="FINAL review date, YYYY-MM-DD")
    args = parser.parse_args()
    for path in run_family_attribution(args.as_of):
        print(path)


if __name__ == "__main__":
    main()
