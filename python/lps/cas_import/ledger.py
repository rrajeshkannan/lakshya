"""Compatibility boundary for the former CAS transaction ledger."""

from lps.transaction_persistence import (
    TRANSACTION_FIELDS,
    read_transactions,
    write_transactions,
)


# Preserve the old CAS-import API while transaction persistence is owned by LPS.
read_ledger = read_transactions
write_ledger = write_transactions

__all__ = [
    "TRANSACTION_FIELDS",
    "read_ledger",
    "write_ledger",
]
