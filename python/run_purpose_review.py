"""Generate the human-facing Purpose review surface for an annual review."""
from __future__ import annotations

import argparse

from family.review_surface import refresh_review_surface


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    print(refresh_review_surface(args.as_of))


if __name__ == "__main__":
    main()
