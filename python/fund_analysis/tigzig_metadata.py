from pathlib import Path

import pandas as pd
import requests


TIGZIG_SEARCH_URL = "https://api.tigzig.com/mf/v1/search"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCOPE_FILE = PROJECT_ROOT / "data" / "fund" / "funds_in_scope.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "fund" / "funds_in_scope_metadata.csv"

METADATA_FIELDS = [
    "entry_type",
    "scheme_code",
    "scheme_name",
    "isin",
    "isin2",
    "amc",
    "group",
    "category_sub",
    "category",
    "scheme_type",
    "plan",
    "option",
    "first_date",
    "last_date",
    "is_active",
    "is_stale",
    "txic_code",
]

ALLOWED_ENTRY_TYPES = {"CURRENT", "POTENTIAL"}


def fetch_metadata(isin: str, entry_type: str) -> dict | None:
    response = requests.get(
        TIGZIG_SEARCH_URL,
        params={"isin": isin},
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    results = payload.get("results", [])

    if not results:
        return None

    if len(results) > 1:
        raise RuntimeError(
            f"Expected one result for ISIN {isin}, "
            f"but TigZig returned {len(results)} results."
        )

    result = results[0]

    return {
        "entry_type": entry_type,
        **{
            field: result.get(field)
            for field in METADATA_FIELDS
            if field != "entry_type"
        },
    }


def main() -> None:
    if not SCOPE_FILE.exists():
        raise FileNotFoundError(
            f"Scope file not found: {SCOPE_FILE}"
        )

    scope = pd.read_csv(SCOPE_FILE)

    required_columns = {"entry_type", "isin"}
    missing_columns = required_columns - set(scope.columns)

    if missing_columns:
        raise ValueError(
            "Scope file is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    scope["entry_type"] = (
        scope["entry_type"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    scope["isin"] = (
        scope["isin"]
        .astype(str)
        .str.strip()
    )

    invalid_entry_types = (
        set(scope["entry_type"].dropna())
        - ALLOWED_ENTRY_TYPES
    )

    if invalid_entry_types:
        raise ValueError(
            f"Invalid entry_type values: "
            f"{sorted(invalid_entry_types)}. "
            f"Allowed values: "
            f"{sorted(ALLOWED_ENTRY_TYPES)}"
        )

    duplicate_isins = (
        scope.loc[
            scope["isin"].duplicated(keep=False),
            "isin",
        ]
        .unique()
        .tolist()
    )

    if duplicate_isins:
        raise ValueError(
            "Duplicate ISINs found in scope: "
            f"{duplicate_isins}"
        )

    rows = []
    unresolved = []

    print(f"ISINs in scope: {len(scope)}")

    for index, row in enumerate(
        scope.itertuples(index=False),
        start=1,
    ):
        isin = row.isin
        entry_type = row.entry_type

        print(
            f"[{index}/{len(scope)}] "
            f"Fetching {isin} ({entry_type})..."
        )

        try:
            metadata = fetch_metadata(
                isin,
                entry_type,
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"TigZig request failed for ISIN {isin}: {exc}"
            ) from exc

        if metadata is None:
            unresolved.append(isin)
            print(f"  NOT FOUND: {isin}")
            continue

        rows.append(metadata)

        print(
            f"  OK: {metadata['scheme_name']} "
            f"({metadata['plan']})"
        )

    metadata_df = pd.DataFrame(
        rows,
        columns=METADATA_FIELDS,
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("Metadata fetch complete.")
    print(f"Resolved  : {len(rows)}")
    print(f"Unresolved: {len(unresolved)}")
    print(f"Output    : {OUTPUT_FILE}")

    if unresolved:
        print()
        print("Unresolved ISINs:")
        for isin in unresolved:
            print(f"  - {isin}")


if __name__ == "__main__":
    main()
