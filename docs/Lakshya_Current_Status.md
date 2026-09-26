# Lakshya — Current Implementation Status

**As of:** 2026-09-26
**Branch:** `main`
**Status:** The 2026-09-06 clean run reconciles. LTS artifacts are a human review plan, not an execution instruction.

This document is the current implementation-status companion to the design documents. It records what the code does now. It is not a second architecture.

---

## 1. System boundary

Lakshya remains a deliberately separated three-system design:

```text
LPS — observe Economic CURRENT from authoritative evidence
LFS — form reviewed analytical intent and TARGET inputs
LTS — analyze the transition from CURRENT to TARGET
```

LTS does not re-run portfolio formation and does not silently change FINAL decisions.

The states remain distinct:

- **Analytical CURRENT:** what the reviewed Lakshya architecture says should be owned.
- **Economic CURRENT:** what the family actually owns at the selected observation date.
- **TARGET:** what the committed Purpose state and selected FINAL decisions imply should be owned.

## 2. How a review is run

Use one as-of date for all three systems. The validated run used **2026-09-06**.

```bash
python -m cas_import_poc.runner input/<Investor>_CAS_<range>.pdf --investor <Investor> --as-of 2026-09-06
python python/run_production.py --as-of 2026-09-06
python -m lts.runner
```

The CAS runner writes `data/lps/positions.csv` at that as-of and keeps Purpose attribution. LFS stamps `data/lfs/purpose_summaries.csv`. LTS reads that stamp and refuses a different `--as-of`.

A normal LFS rerun reuses valid checkpoints under `output/`. Delete `output/*` only for a forced clean rebuild.

## 3. What the 2026-09-06 run reconciled

Portfolio market value is **₹15,233,131.3171967** in every economic artifact:

- `data/lps/positions.csv` for the 34 active positions;
- `output/positions_as_of_2026-09-06.csv`;
- `data/lts/holding_availability_summary.csv`;
- `data/lts/purpose_reports.csv`;
- `data/lts/transition_mappings.csv`;
- `data/lts/materialized_transition_slices.csv`;
- `data/lts/manifest.json`.

The run also has 696 lots (602 available, 94 locked), 46 mappings, 46 slices, and six balanced Purpose reports. FINAL winners in `output/final_<Purpose>_summary.csv` match `data/lfs/purpose_summaries.csv`.

`python -m lts.runner` writes the materialized slices. They are part of the artifact contract.

Every FINAL weight is funded. `RETAIN` is only the capital already held in that Purpose and that ISIN. The remainder of the weight is `INVEST` inside the same Purpose.

## 4. Gaps that were open on 2026-09-23

**Valuation.** Positions had been priced at the 8 Sep NAV while availability used the 6 Sep as-of print, which is the 4 Sep NAV. The difference was ₹27,420.2381130. Sharing 2026-09-06 across CAS import, LFS, and LTS closed it. Availability now matches position market value on all 34 holdings.

**Same-day rows.** Folio `11002746` / `INF879O01027` has two purchases on 20 Mar 2023 and two on 5 Jun 2023. The running balance steps up by each purchase, and the bank debits match two ₹30,000 payments and two ₹60,000 payments. They stay in the ledger. A repeated zero-unit IFSC note on another folio does not change units. Do not drop a row because the date, amount, and description match; check the running balance.

**Materialization and selected-fund funding.** Both are in the reconciled artifact set described above.

## 5. Design invariants

The following remain mandatory:

1. An LPS Position is identified by **Investor + Folio + ISIN**.
2. LTS uses **Investor + Folio + ISIN + Slice**. The bridge currently projects each LPS Position to `Slice-1` at 100%. LPS does not store slices yet.
3. Ownership and Purpose mapping stay explicit. One virtual LTS Position maps to one Purpose. Slice percentages on one physical holding sum to 100%.
4. `transaction_through_date` and `valuation_as_of_date` are separate facts.
5. Source evidence stays separate from analytical interpretation and transition decisions.
6. Locked holdings are explicit. They are not treated as freely redeemable.
7. Unknown source facts stay unknown. The system does not invent tax basis, transaction costs, or execution constraints.
8. Materialization is a review artifact, not permission to execute transactions.
9. LTS is constrained transition analysis, not a second portfolio optimizer.

## 6. Reviewer's rule

Use the LTS files to review the transition. Do not treat them as orders to place. The human still executes outside Lakshya, and a later source import is what changes LPS.

For the operating steps, see `docs/Lakshya_HowTo.md`. For the contracts, see `docs/Lakshya_Architecture.md` and `docs/Lakshya_Pipeline_Sequence.md`.
