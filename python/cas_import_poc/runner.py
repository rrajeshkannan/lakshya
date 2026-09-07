"""Local runner for the Lakshya CAS import proof of concept."""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from .adapter import adapt_cas
from .current_state import derive_current_state
from .ledger import write_ledger
from .positions import reconstruct_positions
from .validation import validate_parse_warnings, validate_scheme_unit_balances

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "input"
LPS_DATA_DIR = PROJECT_ROOT / "data" / "lps"


def _load_casparser():
    try:
        import casparser
    except ImportError as exc:
        raise SystemExit(
            "casparser is not installed. Install/update it with:\n"
            "  python -m pip install -U casparser"
        ) from exc
    return casparser


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
    print(f"Adapted {len(transactions)} canonical transaction(s).")

    ledger_investor = investor or str(data.investor_info.name).strip()
    ledger_path = LPS_DATA_DIR / ledger_investor / "canonical_transactions.csv"
    write_ledger(ledger_path, transactions)
    print(f"Persisted canonical ledger: {ledger_path.relative_to(PROJECT_ROOT)}")

    positions = reconstruct_positions(transactions)
    current_states = derive_current_state(positions)
    active_current_states = [state for state in current_states if state.units != 0]

    print(f"Reconstructed {len(positions)} Position(s).")
    print(f"Derived {len(current_states)} Current State(s).")
    print(f"Active Current State(s): {len(active_current_states)}")

    print(f"Investor: {ledger_investor}")
    print("POC parse + validation + adaptation + ledger persistence + Position reconstruction + Current State derivation: PASS")


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
