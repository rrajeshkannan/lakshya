"""Local runner for the Lakshya CAS import proof of concept."""

from __future__ import annotations

import argparse
import getpass
from datetime import date, datetime
from pathlib import Path

from .adapter import adapt_cas
from .validation import validate_parse_warnings, validate_scheme_unit_balances
from lps.nav_evidence import NavEvidenceStore
from lps.nav_pipeline import run_nav_pipeline
from lps.nav_source import MfapiNavSource, mfapi_http_transport
from lps.position_persistence import read_positions, write_positions
from lps.positions import Position, reconstruct_positions
from lps.transaction_persistence import read_transactions, write_transactions
from lps.transactions import Transaction
from lps.valuation import value_positions

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "input"
LPS_DATA_DIR = PROJECT_ROOT / "data" / "lps"
TRANSACTIONS_PATH = LPS_DATA_DIR / "transactions.csv"
POSITIONS_PATH = LPS_DATA_DIR / "positions.csv"
NAV_DATA_DIR = LPS_DATA_DIR / "nav"


def _load_casparser():
    try:
        import casparser
    except ImportError as exc:
        raise SystemExit(
            "casparser is not installed. Install/update it with:\n"
            "  python -m pip install -U casparser"
        ) from exc
    return casparser


def _replace_investor_transactions(
    existing: list[Transaction], investor: str, incoming: list[Transaction]
) -> list[Transaction]:
    retained = [transaction for transaction in existing if transaction.investor != investor]
    return retained + incoming


def _replace_investor_positions(
    existing: list[Position], investor: str, incoming: list[Position]
) -> list[Position]:
    retained = [position for position in existing if position.id.investor != investor]
    return retained + incoming


def _persist_valued_positions(
    *,
    positions: list[Position],
    valuation_as_of_date: date,
    retrieved_at: str,
) -> list[Position]:
    """Acquire NAV evidence, value Positions, and return the persisted state."""
    active_isins = list(
        dict.fromkeys(
            position.id.isin
            for position in positions
            if position.units != 0
        )
    )

    source = MfapiNavSource(transport=mfapi_http_transport)
    source.scheme_catalog = source.fetch_scheme_catalog()
    nav_results = run_nav_pipeline(
        isins=active_isins,
        nav_source=source,
        data_root=PROJECT_ROOT / "data",
        retrieved_at=retrieved_at,
        progress=print,
    )
    failed = [result for result in nav_results if result["status"] == "failed"]
    if failed:
        raise RuntimeError(
            "NAV acquisition failed: "
            + "; ".join(f"{item['isin']}: {item['error']}" for item in failed)
        )

    nav_stores = {
        isin: NavEvidenceStore(NAV_DATA_DIR / f"{isin}.json")
        for isin in active_isins
    }
    return value_positions(
        positions,
        nav_stores,
        valuation_as_of_date,
    )


def run(
    pdf_path: Path,
    password: str,
    investor: str | None = None,
    valuation_as_of_date: date | None = None,
) -> None:
    casparser = _load_casparser()

    print(f"Reading: {pdf_path.relative_to(PROJECT_ROOT)}")
    data = casparser.read_cas_pdf(str(pdf_path), password)

    print("Validating parser warnings ...")
    validate_parse_warnings(data)

    print("Reconciling scheme unit balances ...")
    results = validate_scheme_unit_balances(data)
    print(f"Validated {len(results)} scheme block(s).")

    transactions = adapt_cas(data, investor_override=investor)
    ledger_investor = investor or str(data.investor_info.name).strip()
    print(f"Adapted {len(transactions)} transaction(s) for {ledger_investor}.")

    existing_transactions = (
        read_transactions(TRANSACTIONS_PATH)
        if TRANSACTIONS_PATH.exists()
        else []
    )
    family_transactions = _replace_investor_transactions(
        existing_transactions,
        ledger_investor,
        transactions,
    )
    write_transactions(TRANSACTIONS_PATH, family_transactions)
    print(f"Persisted Transactions: {TRANSACTIONS_PATH.relative_to(PROJECT_ROOT)}")

    positions = reconstruct_positions(transactions)
    existing_positions = read_positions(POSITIONS_PATH) if POSITIONS_PATH.exists() else []
    family_positions = _replace_investor_positions(
        existing_positions,
        ledger_investor,
        positions,
    )

    if valuation_as_of_date is None:
        valuation_as_of_date = date.today()

    retrieved_at = datetime.now().astimezone().isoformat(timespec="seconds")
    family_positions = _persist_valued_positions(
        positions=family_positions,
        valuation_as_of_date=valuation_as_of_date,
        retrieved_at=retrieved_at,
    )
    write_positions(POSITIONS_PATH, family_positions)

    active_positions = [position for position in positions if position.units != 0]

    print(f"Reconstructed {len(positions)} Position(s) for {ledger_investor}.")
    print(f"Active Position(s): {len(active_positions)}")
    print(f"Persisted Positions: {POSITIONS_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Valuation as of: {valuation_as_of_date.isoformat()}")
    print(
        "LPS parse + validation + adaptation + Transactions persistence + "
        "Position reconstruction + NAV acquisition + valuation + "
        "Positions persistence: PASS"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="CAS PDF path; relative paths are resolved from repo root")
    parser.add_argument("--investor", help="Lakshya investor label, e.g. Amma or Appanna")
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        help="valuation observation date (YYYY-MM-DD); defaults to today",
    )
    args = parser.parse_args()

    pdf_path = args.pdf if args.pdf.is_absolute() else PROJECT_ROOT / args.pdf
    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file():
        raise SystemExit(f"CAS PDF not found: {pdf_path}")
    if not pdf_path.is_relative_to(INPUT_DIR.resolve()):
        raise SystemExit("For safety, CAS input must be stored under the repository input/ directory.")

    password = getpass.getpass("CAS password: ")
    run(
        pdf_path,
        password,
        investor=args.investor,
        valuation_as_of_date=args.as_of,
    )


if __name__ == "__main__":
    main()
