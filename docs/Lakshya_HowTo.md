# Lakshya — How To Run

This is the practical operating guide for a Lakshya annual review. `docs/Lakshya_Architecture.md` defines the contracts; `docs/Lakshya_Pipeline_Sequence.md` defines execution and persistence boundaries.

**As of:** 2026-09-08

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

Do not edit generated files under `output/` or `data/reviews/` by hand.

## 1A. LPS — prepare factual source evidence

For the mutual-fund holdings boundary, use the family's authoritative CAS evidence.

Policy:

- request the CAS comfortably before the earliest family mutual-fund investment;
- include all folios, including zero-balance folios;
- retain the original unmodified CAS PDFs;
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

Review:

```text
data/fund/funds_in_scope.csv
```

The two admission categories are:

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

# 2. Run LFS production

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

The LFS analytical chain is:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

TARGET is the reviewed fund-level formation implied by the selected FINAL Composition decisions and Purpose state.

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

# 4. Run Family Architecture Validation

After production and FINAL archival:

```bash
python python/run_family_attribution.py --as-of YYYY-MM-DD
```

Example:

```bash
python python/run_family_attribution.py --as-of 2026-09-06
```

Review:

```text
family_capital_attribution.csv
family_fund_concentration.csv
family_amc_concentration.csv
family_purpose_dependency.csv
family_attribution_manifest.json
```

The core attribution is:

```text
Purpose current capital
        ×
FINAL Composition fund weight
        =
Attributed capital
```

Look at:

1. attribution of family capital across Funds;
2. Fund concentration;
3. AMC/ecosystem concentration; and
4. Purpose dependencies.

This is **observation, not optimization**. Do not manually alter FINAL winners because of what you see here.

The generated `family_attribution.log` is forensic runtime output and is Git-ignored.

---

# 5. MANUAL CHECKPOINT — review the family picture

Ask only the descriptive question at this boundary:

> Where does the family architecture depend on common Funds or investment organizations?

Do not turn the observation into a concentration rule unless a later analytical investigation earns such a rule.

---

# 6. Start Purpose Staging

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
data/reviews/YYYY-MM-DD/purpose_staging/
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

# 7. MANUAL CHECKPOINT — decide the staging turn

The reviewer controls:

- `value` — current capital;
- `monthly_plan` — monthly contribution;
- `desired` — target;
- `due` — target date;
- `analytical_horizon_years` — analytical horizon;
- `capital_acquire_pct`; and
- `sip_acquire_pct`.

Use this header:

```text
purpose,value,monthly_plan,desired,due,analytical_horizon_years,capital_acquire_pct,sip_acquire_pct
```

Blank fields mean unchanged.

Example:

```text
purpose,value,monthly_plan,desired,due,analytical_horizon_years,capital_acquire_pct,sip_acquire_pct
Home_Loan,600000,10000,,,,,
Retirement,,,,,,60,
```

Do not create money or SIP by directly increasing `value` or `monthly_plan`. Release from another Purpose first, then acquire from the common pool.

---

# 8. Run a staging turn

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

Changing `desired` or the horizon changes the analytical requirement; it does not create a capital release.

---

# 9. MANUAL CHECKPOINT — inspect every turn

After every turn, inspect:

```text
data/reviews/YYYY-MM-DD/purpose_staging/purposes_staged.csv
data/reviews/YYYY-MM-DD/purpose_staging/reconciliation_ledger.csv
data/reviews/YYYY-MM-DD/purpose_staging/achievability_latest.csv
data/reviews/YYYY-MM-DD/purpose_staging/staging_state.json
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

# 10. Commit Purpose Staging

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

# 11. MANUAL CHECKPOINT — after Purpose commit

Confirm:

- staging state is `COMMITTED`;
- `data/purpose/purposes.csv` contains the intended state; and
- `purposes_before_commit.csv` exists in the staging workspace.

---

# 12. Persist the annual Historical Snapshot

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
- `data/fingerprints/composition/`;
- `staging.log`;
- `family_attribution.log`;
- runtime contents under `output/`.

The durable annual state is reviewed authoritative input plus structured review evidence under `data/`.

---

# 13. NEXT STAGE — LTS CURRENT → TARGET

**Stop the annual-review workflow here.** The transition stage is deliberately separate from LFS analytical production.

The three states must remain distinct:

```text
ANALYTICAL CURRENT
= what the reviewed Lakshya architecture says

ECONOMIC CURRENT
= what the family actually owns at the chosen observation date

TARGET
= what the reviewed Purpose + FINAL decisions imply should be owned
```

LPS supplies Economic CURRENT. LFS supplies TARGET. LTS analyzes the path between them.

## 13A. First task: source archaeology

There is **no production transition command yet**.

Before coding, inspect the actual portfolio/account material available to the family, especially the identified Geojit material. Determine what the source actually provides for:

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

## 13B. Intended transition sequence

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

# 14. Errors and recovery

If a command fails:

1. stop;
2. read the error carefully;
3. do not edit generated files to work around it;
4. do not continue to the next checkpoint;
5. repair the input/checkpoint problem or ask for help.

Do not casually delete or overwrite annual review archives under:

```text
data/reviews/YYYY-MM-DD/
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

# 15. One-page annual checklist

```text
LPS — FACTUAL OBSERVATION
[ ] Obtain authoritative full-history CAS / source evidence
[ ] Preserve original evidence; enter password interactively
[ ] Validate source import; stop on ambiguity
[ ] Reconcile family-wide data/lps/transactions.csv
[ ] Reconstruct / validate data/lps/positions.csv
[ ] Apply applicable NAV observation for valuation_as_of_date
[ ] Confirm transaction_through_date and valuation_as_of_date separately
[ ] Review Purpose mapping; one Position → one Purpose
[ ] Accept Economic CURRENT only after human review

LFS — FORMATION
[ ] Review data/fund/funds_in_scope.csv
[ ] Review data/purpose/purposes.csv
[ ] Run production
    python python/run_production.py --as-of YYYY-MM-DD
[ ] CHECKPOINT: inspect final_<Purpose>_summary.csv
[ ] Confirm FINAL results
[ ] Derive/review TARGET from existing Purpose + FINAL decisions

FAMILY REVIEW
[ ] Run Family Architecture Validation
    python python/run_family_attribution.py --as-of YYYY-MM-DD
[ ] CHECKPOINT: inspect attribution / concentration / dependency

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

LTS — TRANSITION
[ ] STOP annual-review workflow
[ ] Begin CURRENT → TARGET separately
[ ] FIRST TASK = source archaeology
[ ] Define only the minimum sufficient CURRENT contract
```

---

# 16. Core operating rule

When in doubt:

```text
observe before interpreting
interpret before optimizing
source before schema
human before automation
```

Or, in Lakshya's shorter language:

> **LPS observes. LFS forms. LTS transitions.**
