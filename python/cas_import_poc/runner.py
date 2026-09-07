"""Local runner for the Lakshya CAS import proof of concept."""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from .adapter import adapt_cas
from .ledger import read_ledger, write_ledger
from .validation import validate_parse_warnings, validate_scheme_unit_balances
from lps.position_persistence import read_positions, write_positions
from lps.positions import Position, reconstruct_positions

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "input"
LPS_DATA_DIR = PROJECT_ROOT / "data" / "lps"
TRANSACTIONS_PATH = LPS_DATA_DIR / "transactions.csv"
POSITIONS_PATH = LPS_DATA_DIR / "positions.csv"


def _load_casparser():
    try:
        import casparser
    except ImportError as exc:
        raise SystemExit(
            "casparser is not installed. Install/update it with:\n"
            "  python -m pip install -U casparser"
        ) from exc
    return casparser


def _replace_investor_transactions(existing, investor: str, incoming):
    retained = [transaction for transaction in existing if transaction.investor != investor]
    return retained + incoming


def _replace_investor_positions(existing: list[Position], investor: str, incoming: list[Position]) -> list[Position]:
    retained = [position for position in existing if position.id.investor != investor]
    return retained + incoming


def run(pdf_path: Path, password: str, investor: str | None = None) -> None:
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

    existing_transactions = read_ledger(TRANSACTIONS_PATH) if TRANSACTIONS_PATH.exists() else []
    family_transactions = _replace_investor_transactions(
        existing_transactions,
        ledger_investor,
        transactions,
    )
    write_ledger(TRANSACTIONS_PATH, family_transactions)
    print(f"Persisted Transactions: {TRANSACTIONS_PATH.relative_to(PROJECT_ROOT)}")

    positions = reconstruct_positions(transactions)
    existing_positions = read_positions(POSITIONS_PATH) if POSITIONS_PATH.exists() else []
    family_positions = _replace_investor_positions(
        existing_positions,
        ledger_investor,
        positions,
    )
    write_positions(POSITIONS_PATH, family_positions)

    active_positions = [position for position in positions if position.units != 0]

    print(f"Reconstructed {len(positions)} Position(s) for {ledger_investor}.")
    print(f"Active Position(s): {len(active_positions)}")
    print(f"Persisted Positions: {POSITIONS_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Investor: {ledger_investor}")
    print("LPS parse + validation + adaptation + Transactions persistence + Position reconstruction + Positions persistence: PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="CAS PDF path; relative paths are resolved from repo root")
    parser.add_argument("--investor", help="Lakshya investor label, e.g. Amma or Appanna")
    args = parser.parse_args()

    pdf_path = args.pdf if args.pdf.is_absolute() else PROJECT_ROOT / args.pdf
    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file():
        raise SystemExit(f"CAS PDF not found: {pdf_path}")
    if not pdf_path.is_relative_to(INPUT_DIR.resolve()):
        raise SystemExit("For safety, CAS input must be stored under the repository input/ directory.")

    password = getpass.getpass("CAS password: ")
    run(pdf_path, password, investor=args.investor)


if __name__ == "__main__":
    main()
