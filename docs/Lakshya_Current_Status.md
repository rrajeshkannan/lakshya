# Lakshya — Current Implementation Status

**Release:** Production v1.0.0
**Valuation as-of:** 2026-09-30
**Recorded:** 2026-10-01
**Status:** The four-runner sweep completes. LTS artifacts are a human review plan, not an execution instruction. `pytest python/tests/` passed 408 tests across `lps`, `lfs`, `lts`, and `core`.

This document is the current implementation-status companion to the design documents. It records what the code does now. It is not a second architecture.

---

## 1. System boundary

Lakshya remains a deliberately separated three-system design, operated through four commands:

```text
LPS — observe Economic CURRENT from authoritative evidence
LFS — form reviewed analytical intent and TARGET inputs
LFS review — Purpose Staging, the human gate after FINAL
LTS — analyze the transition from CURRENT to TARGET
```

```bash
python -m lps.runner --as-of 2026-09-30
python -m lfs.runner --as-of 2026-09-30
python -m lfs.review_runner init --as-of 2026-09-30
python -m lts.runner --as-of 2026-09-30
```

Packages: `python/core/`, `python/lps/` (CAS import is `python/lps/cas_import/`), `python/lfs/` (Purpose Staging is `python/lfs/purpose_staging/`), `python/lts/`. Purpose intent is `data/lfs/purpose.csv`. NAV observations are in `data/nav/`.

LTS does not re-run portfolio formation and does not silently change FINAL decisions.

The states remain distinct:

- **Analytical CURRENT:** what the reviewed Lakshya architecture says should be owned.
- **Economic CURRENT:** what the family actually owns at the selected observation date.
- **TARGET:** what the committed Purpose state and selected FINAL decisions imply should be owned.

## 2. How a review is run

Use one as-of date for LPS valuation, LFS, Purpose Staging, and LTS. The v1.0.0 run used **2026-09-30**.

```bash
python -m lps.cas_import.runner input/<Investor>_CAS_<range>.pdf --investor <Investor> --as-of 2026-09-30
python -m lfs.runner --as-of 2026-09-30
python -m lfs.review_runner init --as-of 2026-09-30
python -m lts.runner --as-of 2026-09-30
python -m lps.runner --as-of 2026-09-30
```

The CAS runner writes `data/lps/positions.csv` at that as-of and keeps Purpose attribution. LFS stamps `data/lfs/purpose_summaries.csv` and `data/lfs/manifest.json`. LTS reads that stamp and refuses a different `--as-of`. It also writes `data/lps/transition_manifest.json`. The date `lps.runner` prints is that manifest as-of.

A normal LFS rerun reuses valid checkpoints under `output/`. Delete `output/*` only for a forced clean rebuild.

## 3. What the 2026-09-30 sweep produced

Portfolio market value is **₹15,233,131.3171967**.

- `data/lps/positions.csv` — 53 holdings, 34 active slices;
- `output/audits/positions_as_of_2026-09-30.csv`;
- `output/goals/<Purpose>/final_<Purpose>_summary.csv`, archived to `data/lfs/purpose_summaries.csv`;
- `data/lts/materialized_transition_slices.csv` — 68 slices;
- `data/lts/cascade_review.csv`;
- `data/lts/execution_playbook.csv` — 49 orders;
- `data/lts/tax_preflight_report.txt`;
- `data/lts/manifest.json`;
- `data/lps/transition_manifest.json` — `MAN-2026-09-30-01`, 49 pending orders, 0 fulfilled.

`python -m lts.runner` writes the slices, the playbook, and the transition manifest. They are part of the artifact contract. The playbook and the manifest agree on source ISIN, target ISIN, and units.

Every FINAL weight is funded. `RETAIN` is only the capital already held in that Purpose and that ISIN. The remainder of the weight is `INVEST` inside the same Purpose.

## 4. Gaps that were open on 2026-09-23

**Valuation.** Positions had been priced at the 8 Sep NAV while availability used the 6 Sep as-of print, which is the 4 Sep NAV. The difference was ₹27,420.2381130. Sharing 2026-09-06 across CAS import, LFS, and LTS closed it. Availability now matches position market value on all 34 holdings.

**Same-day rows.** Folio `11002746` / `INF879O01027` has two purchases on 20 Mar 2023 and two on 5 Jun 2023. The running balance steps up by each purchase, and the bank debits match two ₹30,000 payments and two ₹60,000 payments. They stay in the ledger. A repeated zero-unit IFSC note on another folio does not change units. Do not drop a row because the date, amount, and description match; check the running balance.

**Materialization and selected-fund funding.** Both are in the reconciled artifact set described above.

## 5. Design invariants

The following remain mandatory:

1. An LPS Position is identified by **Investor + Folio + ISIN + Slice**. The physical holding is the first three parts. The opening book is `slice-1`.
2. LTS plans target slices on that same identity. `bridge_positions` reads the LPS book. It does not invent a second ownership percentage.
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
