# Lakshya — How To Run

This is the practical operating guide for a Lakshya annual review. `docs/Lakshya_Architecture.md` defines the contracts; `docs/Lakshya_Pipeline_Sequence.md` defines execution and persistence boundaries.

**As of:** 2026-09-14

The three-system mental model is:

```text
LPS — observe actual capital
LFS — form the reviewed architecture
LTS — transition CURRENT → TARGET
```

Follow the annual review in order. Do not skip a manual checkpoint.

---

# 1. Before you start

Run commands from the repository root:

```bash
cd /path/to/lakshya
python -m pip install -r python/requirements.txt
```

Do not edit generated files under `output/` or `data/lfs/` by hand.

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

Each record retains investor identity. A Position is identified by `Investor + Folio + ISIN`.

The LPS data model has **Transactions and Positions**. Do not introduce a `CurrentState` object or a Portfolio dimension merely to make a view convenient.

## 1B. LPS — valuation semantics

Keep these dates separate:

```text
transaction_through_date
valuation_as_of_date
```

NAV evidence is sparse. Store actual recorded observations only. For a NAV read as of a date, use the latest recorded observation on or before that date.

Do not manufacture holiday/weekend NAVs or interpolate calendar days.

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
data/purpose/purposes.csv
```

Purpose values, targets, SIPs and dates are human-controlled inputs. LFS does not infer or invent them.

---

# 2. Run LFS-Main production

Use:

```bash
python python/run_production.py --as-of YYYY-MM-DD
```

Example:

```bash
python python/run_production.py --as-of 2026-09-06
```

Optional selected Purposes:

```bash
python python/run_production.py --as-of YYYY-MM-DD --purposes Retirement Edu_B
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
python python/run_production.py --as-of YYYY-MM-DD
```

---

# 3. MANUAL CHECKPOINT — inspect FINAL

For every Purpose being reviewed, inspect:

```text
output/final_<Purpose>_summary.csv
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
python python/run_purpose_staging.py init --as-of YYYY-MM-DD
```

Example:

```bash
python python/run_purpose_staging.py init --as-of 2026-09-06
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

The authoritative `data/purpose/purposes.csv` is not changed by INIT. `staging.log` is a forensic log.

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
python python/run_purpose_staging.py turn --as-of YYYY-MM-DD --input path/to/turn.csv
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
python python/run_purpose_staging.py commit --as-of YYYY-MM-DD
```

Before promotion, the authoritative Purpose file is backed up as:

```text
purposes_before_commit.csv
```

The staged file is then promoted to:

```text
data/purpose/purposes.csv
```

A non-zero pool blocks the commit. This prevents an incomplete redistribution from silently becoming authoritative.

---

# 9. MANUAL CHECKPOINT — after Purpose commit

Confirm:

- staging state is `COMMITTED`;
- `data/purpose/purposes.csv` contains the intended state; and
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

## 11A. First task: source archaeology

There is **no production transition command yet**.

Before coding, inspect the actual portfolio/account source material and determine what it genuinely provides for:

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

Only after source archaeology should the **minimum sufficient CURRENT contract** be defined.

## 11B. Intended transition sequence

```text
historical snapshot
        ↓
source archaeology
        ↓
minimum sufficient CURRENT contract
        ↓
source-derived Economic CURRENT
        ↓
TARGET from existing reviewed decisions
        ↓
CURRENT vs TARGET comparison
        ↓
source-derived constraints / feasibility
        ↓
human transition plan / execution
```

Potential future constraints include ELSS lock-in, acquisition-date tax consequences, STCG/LTCG implications, exit loads, transaction costs, liquidity, minimum transaction constraints, SIP/STP/SWP sequencing, and retain/exit/stage/switch/redeem/invest alternatives — only where the source evidence genuinely supports them.

LTS must not become a second portfolio optimizer and cannot execute transactions automatically.

---

# 12. Errors and recovery

If a command fails:

1. stop;
2. read the error carefully;
3. do not edit generated files to work around it;
4. do not continue to the next checkpoint;
5. repair the input/checkpoint problem or ask for help.

Do not casually delete or overwrite annual review archives under:

```text
data/lfs/YYYY-MM-DD/
```

Common issues:

### `Purpose source is missing required columns`

Check:

```text
data/purpose/purposes.csv
```

Required columns:

```text
name,due,value,desired,monthly_plan,analytical_horizon_years
```

### `Unknown Purpose(s)`

Check the spelling against `data/purpose/purposes.csv`.

### `Staging state missing; initialize first`

Run:

```bash
python python/run_purpose_staging.py init --as-of YYYY-MM-DD
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
[ ] Apply applicable NAV observation for valuation_as_of_date
[ ] Confirm transaction_through_date and valuation_as_of_date separately
[ ] Review Purpose mapping; one Position → one Purpose
[ ] Accept Economic CURRENT only after human review

LFS-MAIN — FORMATION
[ ] Review formation scope and Purpose inputs
[ ] Run production
    python python/run_production.py --as-of YYYY-MM-DD
[ ] CHECKPOINT: inspect final_<Purpose>_summary.csv
[ ] Confirm FINAL results

PURPOSE STAGING
[ ] Initialize Purpose Staging
    python python/run_purpose_staging.py init --as-of YYYY-MM-DD
[ ] CHECKPOINT: decide staging turn
[ ] Run staging turn
    python python/run_purpose_staging.py turn --as-of YYYY-MM-DD --input turn.csv
[ ] CHECKPOINT: inspect staged state, ledger, pools, Achievability
[ ] Repeat turns until satisfied
[ ] CHECKPOINT: capital pool = 0; SIP pool = 0
[ ] Commit Purpose Staging
    python python/run_purpose_staging.py commit --as-of YYYY-MM-DD
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
[ ] STOP annual-review workflow
[ ] Begin CURRENT → TARGET separately
[ ] FIRST TASK = source archaeology
[ ] Define only the minimum sufficient CURRENT contract
[ ] Derive TARGET from committed Purpose state + selected FINAL decisions
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

**Status date:** 2026-09-23  
**Purpose of this appendix:** Enrich the established architecture with the current implementation evidence without replacing or weakening any previously documented contract.

The established architecture remains authoritative. This appendix records the current state of the implementation and the remaining engineering work; it does not redefine the domain model, introduce a second optimizer, or convert diagnostic output into execution authority.

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
- a slice-materialization foundation intended to produce reviewable artifacts.

## Validated evidence

The current validation evidence includes:

- **696 lots** and **34 Position summaries**;
- **602 available** lots and **94 locked** lots;
- no negative lot balances in the validated result;
- six balanced Purpose reports; and
- numerical reconciliation within floating-point tolerance.

These are implementation-validation observations, not a claim that the transition workflow is execution-ready.

## Design invariants retained

The implementation must continue to preserve the following:

1. Position identity is `Investor + Folio + ISIN`.
2. Ownership and Purpose attribution remain explicit.
3. `transaction_through_date` and `valuation_as_of_date` remain separate.
4. Source facts and analytical interpretation remain distinguishable.
5. Locked holdings are explicit and are not silently treated as available.
6. Unknown facts remain unknown.
7. Materialization is a review artifact, not execution permission.
8. LTS is constrained transition analysis, not a second portfolio optimizer.
9. Source anomalies are classified rather than silently deduplicated or discarded.

## Known gaps

The current implementation still has open issues:

1. Materialization is not yet fully integrated into the runner and final artifact contract.
2. Selected-fund retention behavior requires a data-driven correction; it must not be repaired with hard-coded exceptions.
3. A valuation discrepancy remains approximately **₹27,420.24**.
4. Exact duplicate transaction rows remain present and must be classified explicitly rather than silently deduplicated.
5. End-to-end artifact production and repeatable clean-run validation still require completion.

## Required engineering sequence

```text
classify source anomalies
        ↓
correct retention semantics
        ↓
integrate materialization into the runner
        ↓
finalize the artifact contract
        ↓
reconcile end to end
        ↓
repeat validation from a clean run
        ↓
present evidence for human review
```

Until these gates are completed, generated outputs should be treated as engineering evidence and diagnostics—not transaction instructions.


## Additional review checklist for the current transition foundation

Before accepting a transition run for human review, verify:

- [ ] lot-level balances are non-negative;
- [ ] available and locked classifications are explicit;
- [ ] Position → Purpose mappings are complete or visibly unresolved;
- [ ] Purpose-level reports reconcile;
- [ ] selected-fund retention behavior is explained from data;
- [ ] duplicate source rows are classified, not silently removed;
- [ ] valuation differences are either explained or recorded as open issues;
- [ ] materialization artifacts are traceable to source Positions and lots;
- [ ] the run is repeatable from a clean input state; and
- [ ] no artifact is presented as an execution instruction.

The existing operating procedure remains in force; this checklist adds transition-specific review gates.
