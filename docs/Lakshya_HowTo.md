# Lakshya — How To Run

This is the practical operating guide for a Lakshya annual review. `docs/Lakshya_Architecture.md` defines the contracts; `docs/Lakshya_Pipeline_Sequence.md` defines execution and persistence boundaries.

**Release:** Production v1.0.0, valuation as-of 2026-09-30

The three-system mental model is:

```text
LPS — observe actual capital
LFS — form the reviewed architecture
LTS — transition CURRENT → TARGET
```

Follow the annual review in order. Do not skip a manual checkpoint.

```bash
python -m lps.cas_import.runner input/<Investor>_CAS_<range>.pdf --investor <Investor> --as-of 2026-09-30
python -m lps.runner --as-of 2026-09-30
python -m lfs.runner --as-of 2026-09-30
python -m lfs.review_runner init --as-of 2026-09-30
python -m lts.runner --as-of 2026-09-30
```

Import the statement first. `lps.runner` then fetches NAV, prices the book, and reconciles settlements. Confirm with `pytest python/tests/`.

---

# 1. Before you start

Run commands from the repository root:

```bash
cd /path/to/lakshya
python -m pip install -e ".[test]"
```

Do not edit generated files under `output/` by hand. `data/lfs/purpose.csv` is the human intent file. `data/lfs/purpose_summaries.csv` and `data/lfs/manifest.json` are written by LFS.

## 1A. LPS — annual source acquisition and factual evidence

For the mutual-fund holdings boundary, use the family's authoritative account statement / CAS evidence.

For the 2027 annual review, the operational source-acquisition step is to obtain the family statement from the current authoritative source (MyCAMS, under the family's present operating procedure) on or around the agreed annual observation date, then preserve the original source unchanged before ingestion.

The source boundary is operational, not architectural: the LPS contract remains source-independent and consumes authoritative evidence rather than a provider-specific domain object.

Policy:

- request the statement comfortably before the earliest family mutual-fund investment;
- include all folios, including zero-balance folios;
- retain the original unmodified source PDFs;
- enter the password interactively and never store it;
- stop and ask the human when parsing produces warnings or ambiguity;
- import the full history at every annual review; and
- review validation before accepting the resulting CURRENT.

The LPS factual collections are family-wide:

```text
data/lps/transactions.csv
data/lps/positions.csv
```

Each record retains investor identity. A Position is identified by `Investor + Folio + ISIN + Slice`. The physical holding is the first three parts. The opening book is `slice-1`.

Run one import per investor from the repository root. The investor name is the filename prefix before `_CAS`, for example `Amma` and `Appanna`. The runner replaces that investor's transactions, reconstructs unit balances, and keeps existing Purpose attribution. It does not fetch NAV or write market value. Do not empty `positions.csv` before import. The password is entered at the prompt and is not stored. `--as-of` is recorded on the import; pricing is the next command.

```bash
python -m lps.cas_import.runner input/<Investor>_CAS_<range>.pdf --investor <Investor> --as-of YYYY-MM-DD
```

The LPS data model has **Transactions and Positions**. Do not introduce a `CurrentState` object or a Portfolio dimension merely to make a view convenient.

## 1B. LPS — valuation semantics

Keep these dates separate:

```text
transaction_through_date
valuation_as_of_date
```

NAV evidence is sparse. Store actual recorded observations only. For a NAV read as of a date, use the latest recorded observation on or before that date.

Do not manufacture holiday/weekend NAVs or interpolate calendar days.

After the statement import, price the family book before LFS:

```bash
python -m lps.runner --as-of YYYY-MM-DD
```

That command asks `lps.nav_engine` to cache mfapi.in history under `data/nav/` for each active holding through the date, asks `lps.valuator` to set market value to units times that NAV, then reconciles `data/lps/transition_manifest.json`. A fund whose newest stored print is already on or after the date is not fetched again. When `data/lps/settlement_mapping.csv` has rows, those orders are marked settled from the folio, units, amount, and date you entered. The steps are in section 11C.

## 1C. Review Fund scope

Review the current formation scope used by LFS. Where the formation-evidence contract is being migrated, the reviewer-selected potential fund universe is the source for additional funds not represented by Positions.

The admission categories are:

- `CURRENT` — already held / currently in family scope;
- `POTENTIAL` — possible new entry.

The 8-year lived-history rule applies to POTENTIAL/new-entry Funds. CURRENT Funds may be younger and remain valid. These categories are admission concepts, not hidden quality rankings or Purpose priorities.

Scheme Name and AMC remain useful factual identity/reference information. Do not add generic Fund attributes such as category or benchmark unless a downstream contract genuinely consumes them.

## 1D. Review Purpose inputs

Review:

```text
data/lfs/purpose.csv
```

Purpose values, targets, SIPs and dates are human-controlled inputs. LFS does not infer or invent them.

---

# 2. Run LFS-Main production

Use:

```bash
python -m lfs.runner --as-of YYYY-MM-DD
```

Example:

```bash
python -m lfs.runner --as-of 2026-09-30
```

Optional selected Purposes:

```bash
python -m lfs.runner --as-of YYYY-MM-DD --purposes Retirement Edu_B
```

The LFS-Main analytical chain is:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

Do not treat TARGET as part of this production run. TARGET is derived after the reviewed Purpose state has passed Purpose Staging and the annual persistence boundary.

A normal annual review does not require deleting `output/`; valid checkpoints are reused automatically.

A deliberate clean rebuild, when genuinely required, is:

```bash
rm -rf output/*
python -m lfs.runner --as-of YYYY-MM-DD
```

---

# 3. MANUAL CHECKPOINT — inspect FINAL

For every Purpose being reviewed, inspect:

```text
output/goals/<Purpose>/final_<Purpose>_summary.csv
```

Confirm:

- the expected file exists;
- production completed successfully;
- a FINAL winner exists; and
- the result is complete and sensible.

If anything is missing or unexpected, stop. Do not edit generated output to make the review continue.

The FINAL result is an analytical decision. It is **not** evidence of the family's actual holdings.

---

# 4. Purpose Staging

Purpose Staging is the deliberate human reconciliation turn after FINAL. It is a separate stage from LFS-Main production and is not another optimization layer.

Initialize:

```bash
python -m lfs.review_runner init --as-of YYYY-MM-DD
```

Example:

```bash
python -m lfs.review_runner init --as-of 2026-09-30
```

Workspace:

```text
output/purpose_staging/YYYY-MM-DD/
```

Structured state:

```text
purposes_staged.csv
reconciliation_ledger.csv
achievability_latest.csv
staging_state.json
```

The authoritative `data/lfs/purpose.csv` is not changed by INIT. `staging.log` is a forensic log.

Purpose Staging does not alter FUND, TEAM, COMPOSITION, MISSION, FINAL, or the selected FINAL Composition.

---

# 5. MANUAL CHECKPOINT — decide the staging turn

The reviewer controls the permitted staging levers:

- `value` — current capital;
- `monthly_plan` — monthly contribution;
- `capital_acquire_pct`; and
- `sip_acquire_pct`.

`desired` and `due` remain fixed context for the staging turn. `analytical_horizon_years` is derived and is not a human Purpose field.

Use the current staging header:

```text
purpose,value,monthly_plan,capital_acquire_pct,sip_acquire_pct
```

Blank fields mean unchanged.

Example:

```text
purpose,value,monthly_plan,capital_acquire_pct,sip_acquire_pct
Home_Loan,600000,10000,,
Retirement,,,,60
```

Do not create money or SIP by directly increasing `value` or `monthly_plan`. Release from another Purpose first, then acquire from the common pool.

---

# 6. Run a staging turn

```bash
python -m lfs.review_runner turn --as-of YYYY-MM-DD --input path/to/turn.csv
```

The turn:

1. applies the requested staged changes;
2. releases reductions into the capital/SIP pools;
3. applies acquisition percentages to the pool available at the start of the acquisition phase;
4. records the movement in the cumulative ledger;
5. recalculates Achievability; and
6. pauses for review.

Acquisition percentages are not applied sequentially to a shrinking pool. Any unallocated pool remains available for the next turn.

Changing `desired` or the horizon is outside the staging lever set; such a change must be made deliberately in the authoritative Purpose inputs before the relevant analytical review is rerun. It does not create a capital release.

---

# 7. MANUAL CHECKPOINT — inspect every turn

After every turn, inspect:

```text
output/purpose_staging/YYYY-MM-DD/purposes_staged.csv
output/purpose_staging/YYYY-MM-DD/reconciliation_ledger.csv
output/purpose_staging/YYYY-MM-DD/achievability_latest.csv
output/purpose_staging/YYYY-MM-DD/staging_state.json
```

Check:

- staged Purpose values and dates;
- `pool_capital`;
- `pool_monthly_sip`;
- every release/acquisition in the ledger; and
- Achievability status for finite-target Purposes.

Possible Achievability statuses are:

```text
NOT_APPLICABLE
INSUFFICIENT_EVIDENCE
WITHIN_OBSERVED_TERRAIN
BEYOND_OBSERVED_TERRAIN
```

Repeat as necessary:

```text
review → turn → inspect → review → turn → inspect → …
```

There is no automatic Purpose-priority decision.

---

# 8. Commit Purpose Staging

Commit only when:

- the reviewer is satisfied;
- `pool_capital = 0`; and
- `pool_monthly_sip = 0`.

Run:

```bash
python -m lfs.review_runner commit --as-of YYYY-MM-DD
```

Before promotion, the authoritative Purpose file is backed up as:

```text
purposes_before_commit.csv
```

The staged file is then promoted to:

```text
data/lfs/purpose.csv
```

A non-zero pool blocks the commit. This prevents an incomplete redistribution from silently becoming authoritative.

---

# 9. MANUAL CHECKPOINT — after Purpose commit

Confirm:

- staging state is `COMMITTED`;
- `data/lfs/purpose.csv` contains the intended state; and
- `purposes_before_commit.csv` exists in the staging workspace.

---

# 10. Persist the annual Historical Snapshot

The annual snapshot is a **human-controlled Git persistence boundary**. It is not an automatic snapshot engine and not a transaction ledger.

Review intended changes:

```bash
git status --short
git diff
```

Commit only intended annual-review state. Do not blindly use `git add .` when unrelated working-tree changes exist.

Typical deliberate persistence:

```bash
git add data/
git status --short
git commit -m "Archive Lakshya annual review YYYY-MM-DD"
git status --short
```

Do not archive generated runtime material such as:

- `data/cache/`;
- `output/fingerprints/composition/`;
- `staging.log`;
- runtime contents under `output/`.

The durable annual state is reviewed authoritative input plus structured review evidence under `data/`.

---

# 11. CURRENT → TARGET

**Stop the annual-review workflow here before beginning transition analysis.** The CURRENT → TARGET stage is deliberately separate from LFS-Main and Purpose Staging.

The authoritative annual sequence is:

```text
FINAL
  ↓
Purpose Staging
  ↓
Historical Snapshot
  ↓
CURRENT
  ↓
TARGET
```

The three states must remain distinct:

```text
ANALYTICAL CURRENT
= what the reviewed Lakshya architecture says

ECONOMIC CURRENT
= what the family actually owns at the chosen observation date

TARGET
= what the committed Purpose state + selected FINAL decisions imply should be owned
```

LPS supplies Economic CURRENT. LFS supplies the reviewed formation intent used to derive TARGET. LTS analyzes the path between them.

## 11A. Run LTS

LTS has a production command. Run it after LPS and LFS have shared the same as-of. The date is read from `data/lfs/purpose_summaries.csv`.

```bash
python -m lts.runner --as-of YYYY-MM-DD
```

It writes:

```text
data/lts/materialized_transition_slices.csv
data/lts/cascade_review.csv
data/lts/execution_playbook.csv
data/lts/tax_preflight_report.txt
data/lts/manifest.json
data/lps/transition_manifest.json
```

The plan uses the market values already stored on `data/lps/positions.csv`. Availability reprices those units from the NAV files as of the LFS date. If those dates differ, the two totals will not match. Revalue with `python -m lps.runner --as-of` at the LFS date, then run LTS again.

The artifacts are a human review plan. They do not place transactions.

Source evidence still limits what LTS may conclude. Inspect what the statement genuinely provides for:

- holding/scheme identity;
- units;
- current value;
- observation date;
- account/folio representation;
- acquisition or transaction information;
- cost information and its granularity;
- source-authoritative versus presentation fields; and
- facts the source does not provide.

Do not infer actual holdings from:

```text
funds_in_scope.csv
FINAL summaries
Purpose data
```

Do not manufacture cost basis, acquisition dates, tax lots, exit costs, account semantics, or transaction constraints.

## 11B. What the LTS run does

```text
data/lps/positions.csv + transactions + NAV
        ↓
Economic CURRENT at the shared as-of
        ↓
data/lfs/purpose_summaries.csv weights × Purpose capital
        ↓
RETAIN / REDEEM / REDEEM_LOCKED / INVEST
        ↓
materialized slices for human review
```

`RETAIN` keeps capital already in the same Purpose and the same ISIN. The rest of a FINAL weight is funded by `INVEST` inside that Purpose. Locked ELSS lots stay explicit.

ELSS lock-in is already classified. Acquisition-date tax consequences, STCG/LTCG labels, exit loads, transaction costs, liquidity, minimum transaction constraints, and SIP/STP/SWP sequencing stay unused until the source evidence supports them.

LTS must not become a second portfolio optimizer and cannot execute transactions automatically.

## 11C. Purpose-dedicated folios and settlement

A reinvestment does not join whatever folio the investor already holds in that fund. `RETAIN` stays on the current physical folio. A new purchase reuses a folio only when that folio is already dedicated to the same investor, purpose, and ISIN. Otherwise the order names a placeholder:

```text
NEW_FOLIO_<INVESTOR>_<PURPOSE>_<ISIN_SUFFIX>
```

`NEW_FOLIO_Amma_Edu_B_O01027` is Amma's Edu_B purchase of the fund whose ISIN ends in `O01027`. Marriage, Retirement, and the other purposes in that same fund get their own placeholders.

Indian mutual-fund redemptions apply FIFO inside one folio of one scheme. Lots in another folio are a separate queue. If Edu_B and Retirement purchases share one folio, a later redemption of either goal consumes the oldest units in that folio, including units bought for the other goal. One folio per purpose keeps each goal's acquisition sequence intact.

The playbook is a review plan. You place the trades at the AMC. The AMC then assigns the real folio number, units, and amount. Record each completed order in `data/lps/settlement_mapping.csv`. The file is already in the repository with this header and no rows:

```text
order_id,actual_folio,actual_units,actual_amount,settled_date
```

`order_id` is the id in `data/lps/transition_manifest.json`, such as `ORD-001`. `actual_folio` is the folio number the AMC opened. `actual_units` and `actual_amount` are what was allotted. `settled_date` is `YYYY-MM-DD`.

Then run:

```bash
python -m lps.runner --as-of YYYY-MM-DD
```

Each mapped order changes from `PENDING` to `SETTLED`. `settled_at` becomes `settled_date`. The placeholder `target_folio` becomes `actual_folio`. The order stores `settled_units` and `settled_amount`. The match is the order id. Leave a row out until that trade has actually settled. CAS import remains the path that writes the raw transaction ledger.

---

# 12. Errors and recovery

If a command fails:

1. stop;
2. read the error carefully;
3. do not edit generated files to work around it;
4. do not continue to the next checkpoint;
5. repair the input/checkpoint problem or ask for help.

Do not casually delete or overwrite the durable review files:

```text
data/lfs/purpose_summaries.csv
data/lfs/purpose.csv
data/lps/positions.csv
data/lps/transactions.csv
data/lps/settlement_mapping.csv
```

Common issues:

### `Purpose source is missing required intent columns`

Check:

```text
data/lfs/purpose.csv
```

Required columns:

```text
name,due,desired,monthly_plan
```

Capital comes from LPS positions. Horizon is derived from `due`.

### `Unknown Purpose(s)`

Check the spelling against `data/lfs/purpose.csv`.

### `Staging state missing; initialize first`

Run:

```bash
python -m lfs.review_runner init --as-of YYYY-MM-DD
```

### `Acquisition percentages cannot exceed 100%`

Correct the turn CSV so total capital and SIP acquisition percentages are each within 100%.

### `Required MISSION checkpoint is missing`

Stop and repair/rerun the relevant production checkpoint before attempting FINAL.

### `MISSION checkpoint is empty`

Do not manufacture a winner. Inspect and rerun the relevant production stage.

### Commit says the pool is non-zero

Return to staging turns and deliberately reconcile the remaining pool.

### LPS source evidence is ambiguous

Stop. Do not guess. Preserve the original source, inspect the ambiguity, and resolve it with the human before accepting the factual state.

---

# 13. One-page annual checklist

```text
LPS — FACTUAL OBSERVATION
[ ] Obtain authoritative full-history account statement / CAS / source evidence
[ ] For the 2027 review, acquire it from the current authoritative source on/around the agreed annual observation date
[ ] Preserve original evidence; enter password interactively
[ ] Validate source import; stop on ambiguity
[ ] Reconcile family-wide data/lps/transactions.csv
[ ] Reconstruct / validate data/lps/positions.csv
[ ] Price the book at valuation_as_of_date
    python -m lps.runner --as-of YYYY-MM-DD
[ ] Confirm transaction_through_date and valuation_as_of_date separately
[ ] Review Purpose mapping; one Position → one Purpose
[ ] Accept Economic CURRENT only after human review

LFS-MAIN — FORMATION
[ ] Review formation scope and Purpose inputs
[ ] Run production
    python -m lfs.runner --as-of YYYY-MM-DD
[ ] CHECKPOINT: inspect output/goals/<Purpose>/final_<Purpose>_summary.csv
[ ] Confirm FINAL results

PURPOSE STAGING
[ ] Initialize Purpose Staging
    python -m lfs.review_runner init --as-of YYYY-MM-DD
[ ] CHECKPOINT: decide staging turn
[ ] Run staging turn
    python -m lfs.review_runner turn --as-of YYYY-MM-DD --input turn.csv
[ ] CHECKPOINT: inspect staged state, ledger, pools, Achievability
[ ] Repeat turns until satisfied
[ ] CHECKPOINT: capital pool = 0; SIP pool = 0
[ ] Commit Purpose Staging
    python -m lfs.review_runner commit --as-of YYYY-MM-DD
[ ] CHECKPOINT: confirm authoritative Purpose state + backup

HISTORICAL MEMORY
[ ] Review intended annual data/ changes
[ ] Persist annual snapshot
    git status --short
    git add data/
    git status --short
    git commit -m "Archive Lakshya annual review YYYY-MM-DD"
    git status --short

CURRENT → TARGET
[ ] Confirm LPS, LFS, and LTS share one as-of date
[ ] Run LTS
    python -m lts.runner --as-of YYYY-MM-DD
[ ] Reconcile the new manifest
    python -m lps.runner --as-of YYYY-MM-DD
[ ] CHECKPOINT: manifest is balanced and availability matches position market value
[ ] Review the execution playbook, materialized slices, cascade review, and tax preflight
[ ] CHECKPOINT: each reinvestment folio is one investor, one purpose, and one ISIN
[ ] Treat the artifacts as a review plan, not an execution instruction
[ ] Place the trades at the AMC
[ ] Record each settlement in data/lps/settlement_mapping.csv
    order_id,actual_folio,actual_units,actual_amount,settled_date
[ ] Apply the settlement map
    python -m lps.runner --as-of YYYY-MM-DD
[ ] CHECKPOINT: mapped orders are SETTLED and the placeholder folio is the AMC folio
```

---

# 14. Core operating rule

When in doubt:

```text
observe before interpreting
interpret before optimizing
source before schema
human before automation
```

Or, in Lakshya's shorter language:

> **LPS observes. LFS forms. LTS transitions.**

---

# Appendix — Current Implementation Status and Transition Boundary

**Status date:** 2026-10-01  
**Release:** Production v1.0.0, valuation as-of 2026-09-30. See `docs/Lakshya_Current_Status.md`.  
**Purpose of this appendix:** Enrich the established architecture with the current implementation evidence without replacing or weakening any previously documented contract.

The established architecture remains authoritative. This appendix records the current implementation evidence. It does not redefine the domain model, introduce a second optimizer, or convert a review artifact into execution authority.

## Current boundary

Lakshya continues to separate three responsibilities:

```text
LPS — factual Economic CURRENT
LFS — reviewed formation intent and TARGET inputs
LTS — constrained CURRENT → TARGET analysis
```

The transition foundation currently works from source-derived transaction and position evidence, explicit Purpose attribution, and reviewed formation intent. The human review and external-execution boundary remains intact.

## Implemented transition foundation

The current implementation includes:

- a source-derived Position and acquisition-lot bridge;
- availability and lock-in classification;
- explicit Position → Purpose transition mapping;
- reconciliation reporting at lot, Position, Purpose, and transition levels;
- explicit locked-holding representation;
- selected-fund evidence; and
- slice materialization written by the LTS runner into `data/lts/materialized_transition_slices.csv`.

## Validated evidence

The current validation evidence, from the 2026-09-30 valuation, includes:

- **696 lots** and **34** active slices (53 position rows);
- **604 available** lots and **92 locked** lots, all ELSS and all `RETAIN`;
- no negative lot balances in the validated result;
- position market value **₹14,790,485.6443662**, matching the materialized slices on units and market value;
- **68** slices and **49** pending orders in `MAN-2026-09-30-01`, agreeing with the execution playbook; and
- `pytest python/tests/` passed 408 tests.

The artifacts are a human review plan, not permission to execute transactions.

## Design invariants retained

The implementation must continue to preserve the following:

1. Position identity is `Investor + Folio + ISIN + Slice`. The physical holding remains `Investor + Folio + ISIN`.
2. Ownership and Purpose attribution remain explicit.
3. `transaction_through_date` and `valuation_as_of_date` remain separate.
4. Source facts and analytical interpretation remain distinguishable.
5. Locked holdings are explicit and are not silently treated as available.
6. Unknown facts remain unknown.
7. Materialization is a review artifact, not execution permission.
8. LTS is constrained transition analysis, not a second portfolio optimizer.
9. Source anomalies are classified rather than silently deduplicated or discarded.

## Closed gaps

The 2026-09-26 clean run, with LPS, LFS, and LTS sharing as-of **2026-09-06**, closed the previously open implementation gaps. The figures in this list are that close. The live book is the 2026-09-30 valuation above.

1. Materialization is wired into `python -m lts.runner`. The runner writes `data/lts/materialized_transition_slices.csv` together with the mappings, purpose reports, availability files, and `manifest.json`.
2. Every FINAL-selected fund is funded at its Composition weight. `RETAIN` is the same-Purpose, same-ISIN overlap. A selected fund that the Purpose does not already hold is an `INVEST`, not a missing retain.
3. Position market value, the LFS position snapshot, availability, purpose reports, mappings, slices, and the manifest agree at **₹15,233,131.3171967**. The earlier ₹27,420.24 gap was a NAV-date split: positions had been priced at the 8 Sep print while availability used the 6 Sep as-of print (4 Sep). One shared as-of removes it.
4. The same-day Parag Parikh rows on folio `11002746` / `INF879O01027` are two real purchases. Their running balances step up by the purchased units, and the bank debits match. They are not copies to delete. A repeated zero-unit IFSC note does not change units. Same date, amount, and description are not enough to call two rows duplicates when the running balance differs. Do not silently drop rows.
5. The clean run reproduced the artifact set: 34 active positions, 696 lots (602 available, 94 locked), 46 mappings, 46 slices, and six balanced Purpose reports.

LTS artifacts remain a human review plan. They do not execute transactions and they do not mutate LPS.


## Additional review checklist for the current transition foundation

Before accepting a transition run for human review, verify:

- [ ] lot-level balances are non-negative;
- [ ] available and locked classifications are explicit;
- [ ] Position → Purpose mappings are complete or visibly unresolved;
- [ ] Purpose-level reports reconcile to position market value;
- [ ] every FINAL weight is funded, with RETAIN only for the same Purpose and ISIN;
- [ ] same-day rows are distinguished by running balance before anyone calls them duplicates;
- [ ] availability value matches position market value at the shared as-of;
- [ ] materialized slices trace back to the source Positions;
- [ ] the run is repeatable from a clean `output/` rebuild; and
- [ ] no artifact is presented as an execution instruction.

The existing operating procedure remains in force; this checklist adds transition-specific review gates.
