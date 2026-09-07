# Lakshya — How To Run

This is the practical operating guide for a Lakshya annual review. Follow it in order. Analytical internals are documented in `docs/Lakshya_Architecture.md` and the execution sequence is documented in `docs/Lakshya_Pipeline_Sequence.md`.

**As of:** 2026-09-07

---

# 1. Before you start

Run commands from the repository root.

```bash
cd /path/to/lakshya
python -m pip install -r python/requirements.txt
```

Do not edit generated files under `output/` or `data/reviews/` by hand.

## 1A. Review Fund scope

Review:

```text
data/fund/funds_in_scope.csv
```

The two admission categories are:

- `CURRENT` — already held / currently part of the family portfolio;
- `POTENTIAL` — a possible new entry.

These are scope/admission categories, not quality rankings or hidden Purpose priorities. The 8-year lived-history rule applies to POTENTIAL/new-entry Funds; CURRENT Funds may be younger and remain valid.

## 1B. Review Purpose inputs

Review:

```text
data/purpose/purposes.csv
```

Update Purpose values, targets, SIPs or dates deliberately before starting a new analytical review.

---

# 2. Run production

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

Resume an interrupted upstream run only when appropriate:

```bash
python python/run_production.py --as-of YYYY-MM-DD --resume-from global
python python/run_production.py --as-of YYYY-MM-DD --resume-from mission
```

A normal annual review does not require deleting `output/`; valid checkpoints are reused automatically.

A deliberate clean rebuild, when genuinely required, is:

```bash
rm -rf output/*
python python/run_production.py --as-of YYYY-MM-DD
```

The analytical chain is:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

---

# 3. MANUAL CHECKPOINT — inspect FINAL

Stop and inspect, for every Purpose being reviewed:

```text
output/final_<Purpose>_summary.csv
```

Confirm:

- the expected file exists;
- production completed successfully;
- a FINAL winner exists; and
- the result is complete and sensible.

If anything is missing or unexpected, stop. Do not edit generated output to make the review continue.

---

# 4. Run Family Architecture Validation

After production:

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

These are descriptive family-level observations. Do not manually alter FINAL winners because of what you see here.

The generated `family_attribution.log` is forensic runtime output and is Git-ignored.

---

# 5. MANUAL CHECKPOINT — review the family picture

Look at:

1. attribution of family capital across Funds;
2. Fund concentration;
3. AMC concentration; and
4. Purpose dependencies.

This is observation, not optimization. If the family understands the result and is ready to review Purpose requirements, continue.

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

The authoritative `data/purpose/purposes.csv` is not changed by INIT. `staging.log` is a Git-ignored forensic log.

---

# 7. MANUAL CHECKPOINT — decide the staging turn

The reviewer controls:

- `value` — current capital;
- `monthly_plan` — monthly contribution;
- `desired` — target;
- `due` — target date;
- `analytical_horizon_years` — analytical horizon.

A turn may additionally specify:

- `capital_acquire_pct`;
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

The system backs up the authoritative Purpose file as:

```text
purposes_before_commit.csv
```

and promotes the staged file to:

```text
data/purpose/purposes.csv
```

A non-zero pool blocks the commit.

---

# 11. MANUAL CHECKPOINT — after Purpose commit

Confirm:

- staging state is `COMMITTED`;
- `data/purpose/purposes.csv` contains the intended state; and
- `purposes_before_commit.csv` exists in the staging workspace.

---

# 12. Persist the annual historical snapshot

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

The durable annual state is the reviewed authoritative input plus structured review evidence under `data/`.

---

# 13. NEXT STAGE — CURRENT → TARGET transition

**Stop the annual-review workflow here.** The next stage is deliberately separate from the analytical production chain.

The transition begins only after the historical snapshot has been deliberately committed.

Its three states must remain distinct:

```text
ANALYTICAL CURRENT
= what the reviewed Lakshya architecture says today

ECONOMIC CURRENT
= what the family actually owns at the chosen observation date

TARGET
= what the reviewed Purpose + FINAL decisions imply should be owned
```

Do not assume that the analytical CURRENT is the economic CURRENT.

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

The transition layer is not a new portfolio optimizer. It must not replace a FINAL winner merely because an existing holding is inconvenient.

Lakshya may eventually calculate and present a transition analysis, but redemption, purchase, switch and reinvestment remain human-controlled external actions.

---

# 14. Errors and recovery

If a command fails:

1. stop;
2. read the error carefully;
3. do not edit generated files to work around it;
4. do not continue to the next checkpoint;
5. fix the input/checkpoint problem or ask for help.

Do not delete or casually overwrite annual review archives under:

```text
data/reviews/YYYY-MM-DD/
```

Common staging issues:

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

---

# 15. One-page annual checklist

```text
[ ] Review data/fund/funds_in_scope.csv
    CURRENT = existing scope/holdings category
    POTENTIAL = possible new candidates

[ ] Review data/purpose/purposes.csv

[ ] Run production
    python python/run_production.py --as-of YYYY-MM-DD

[ ] CHECKPOINT: inspect final_<Purpose>_summary.csv

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

[ ] CHECKPOINT: review intended annual data/ changes

[ ] Persist annual snapshot
    git status --short
    git add data/
    git status --short
    git commit -m "Archive Lakshya annual review YYYY-MM-DD"
    git status --short

[ ] STOP

[ ] Begin CURRENT → TARGET as a separate stage
    FIRST TASK = source archaeology
```
