# CAS Import POC

Proof of concept for the LPS CAS import boundary.

## Boundary

```text
original CAMS CAS PDF
        ↓
     casparser
        ↓
  hard validation
        ↓
 Lakshya adapter
        ↓
canonical transactions
        ↓
  local LPS ledger
```

The POC deliberately keeps the parser-specific model inside the import boundary. Downstream code consumes only the small Lakshya representations in `models.py`.

## Local input

Put original issuer-delivered CAS PDFs under the repository root:

```text
input/
```

The directory is Git-ignored except for its `.gitkeep`. Never commit the family CAS PDFs or the CAS password.

For the current family fixtures, place for example:

```text
input/Amma_CAS_01012006-07092026.pdf
input/Appanna_CAS_01012006-07092026.pdf
```

The runner also verifies that the supplied PDF is inside `input/`.

## Install / update parser

From the repository root:

```bash
python -m pip install -U casparser
```

The current POC expects the public `casparser` package API:

```python
casparser.read_cas_pdf(path, password)
```

## Run

From repository root:

```bash
python -m cas_import_poc.runner input/Amma_CAS_01012006-07092026.pdf --investor Amma
```

and:

```bash
python -m cas_import_poc.runner input/Appanna_CAS_01012006-07092026.pdf --investor Appanna
```

The password is requested interactively and is never stored by the POC.

A successful run persists the canonical transaction ledger locally at:

```text
data/lps/<Investor>/canonical_transactions.csv
```

`data/lps/` is Git-ignored because it contains family investment state.

## What is validated

The POC checks:

1. parser-level `parse_warnings` are surfaced as a hard validation failure;
2. every scheme's opening + parsed unit movements reproduces the printed closing balance;
3. parser transaction types are translated into Lakshya's shared event vocabulary;
4. every adapted transaction has the Position identity fields `Investor + Folio + ISIN`;
5. no ISIN means a hard failure rather than an inferred identity;
6. persisted canonical transactions can be read back without changing their values.

## Tests

Run the normal Lakshya test suite:

```bash
pytest
```

The CAS import unit tests use small synthetic parser-like objects and do not require the real PDFs.

## POC status

The POC now parses, validates, adapts, persists the canonical transaction ledger, and reconstructs factual Positions. It does **not** yet implement annual checkpoint/re-import reconciliation or produce the final CURRENT artifact. Those follow only when the next concrete requirement is earned.
