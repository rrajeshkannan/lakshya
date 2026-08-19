from datetime import date, datetime
from pathlib import Path
import argparse

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "fund"
    / "funds_in_scope_metadata.csv"
)

DEFAULT_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "fund"
    / "funds_admissible.csv"
)

ALLOWED_ENTRY_TYPES = {"CURRENT", "POTENTIAL"}

EXCLUDED_CATEGORIES = {
    "Debt",
    "Multicap",
    "Focused",
    "ETF",
    "Thematic",
    "ELSS",
}

MINIMUM_FUND_AGE_YEARS = 8


def calculate_age_years(
    first_date: pd.Timestamp,
    review_date: date,
) -> float:
    days = (
        pd.Timestamp(review_date)
        - first_date
    ).days

    return days / 365.2425


def evaluate_potential_fund(
    row: pd.Series,
    review_date: date,
) -> str:
    category = str(row["category"]).strip()
    category_sub = str(row["category_sub"]).strip()
    plan = str(row["plan"]).strip()
    option = str(row["option"]).strip()
    scheme_type = str(row["scheme_type"]).strip()

    is_active = bool(row["is_active"])

    first_date = pd.to_datetime(
        row["first_date"],
        errors="coerce",
    )

    category_text = f"{category} {category_sub}".lower()

    for excluded in EXCLUDED_CATEGORIES:
        if excluded.lower() in category_text:
            return "REJECT"

    if not is_active:
        return "REJECT"

    if "open ended" not in scheme_type.lower():
        return "REJECT"

    if option.lower() != "growth":
        return "REJECT"

    if plan.lower() != "direct":
        return "REJECT"

    if pd.isna(first_date):
        return "REJECT"

    age_years = calculate_age_years(
        first_date,
        review_date,
    )

    if age_years < MINIMUM_FUND_AGE_YEARS:
        return "WAITLIST"

    return "ADMIT"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Lakshya Fund Admission."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_FILE,
        help="Input funds metadata CSV.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help="Output admissible Funds CSV.",
    )

    parser.add_argument(
        "--review-date",
        type=str,
        default=None,
        help="Review date in YYYY-MM-DD format.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_file = args.input
    output_file = args.output

    if args.review_date:
        try:
            review_date = datetime.strptime(
                args.review_date,
                "%Y-%m-%d",
            ).date()
        except ValueError as exc:
            raise ValueError(
                "review-date must be in YYYY-MM-DD format."
            ) from exc
    else:
        review_date = date.today()

    if not input_file.is_absolute():
        input_file = PROJECT_ROOT / input_file

    if not output_file.is_absolute():
        output_file = PROJECT_ROOT / output_file

    if not input_file.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {input_file}"
        )

    df = pd.read_csv(input_file)

    required_columns = {
        "entry_type",
        "isin",
        "scheme_name",
        "category",
        "category_sub",
        "scheme_type",
        "plan",
        "option",
        "first_date",
        "is_active",
    }

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Metadata file is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    df["entry_type"] = (
        df["entry_type"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    invalid_entry_types = (
        set(df["entry_type"].dropna())
        - ALLOWED_ENTRY_TYPES
    )

    if invalid_entry_types:
        raise ValueError(
            "Invalid entry_type values: "
            f"{sorted(invalid_entry_types)}. "
            f"Allowed values: "
            f"{sorted(ALLOWED_ENTRY_TYPES)}"
        )

    admitted_rows = []

    print(f"Review date: {review_date}")
    print(f"Funds in metadata: {len(df)}")
    print()

    for _, row in df.iterrows():
        isin = row["isin"]
        entry_type = row["entry_type"]
        scheme_name = row["scheme_name"]

        if entry_type == "CURRENT":
            decision = "STANDING"
        else:
            decision = evaluate_potential_fund(
                row,
                review_date,
            )

        print(
            f"{isin} | "
            f"{entry_type:<10} | "
            f"{decision:<9} | "
            f"{scheme_name}"
        )

        if decision in {"STANDING", "ADMIT"}:
            admitted_rows.append(row)

    admissible_df = pd.DataFrame(admitted_rows)

    # CURRENT/POTENTIAL is deliberately not propagated.
    # Once a Fund reaches this artifact, it simply belongs
    # to the behavioural universe.
    if not admissible_df.empty:
        admissible_df = admissible_df.drop(
            columns=["entry_type"],
            errors="ignore",
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    admissible_df.to_csv(
        output_file,
        index=False,
    )

    print()
    print("Fund Admission complete.")
    print(
        f"Behavioural universe: "
        f"{len(admissible_df)} Funds"
    )
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
