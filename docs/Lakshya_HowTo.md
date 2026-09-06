# Lakshya — How To Run

This is the practical operating guide for running Lakshya. Follow it in order. You do not need to understand the analytical internals to run a review.

---

## 1. Before you start

Run commands from the **repository root**.

Make sure Python and the project dependencies are installed:

```bash
cd /path/to/lakshya
python -m pip install -r python/requirements.txt
```

Do not edit generated files under `output/` or `data/reviews/` by hand.

The authoritative Purpose input is:

```text
data/purpose/purposes.csv
```

If Purpose values, targets, SIPs or dates have changed since the last review, make those changes in the authoritative input **before starting a new production review**.

---

# 2. Run the production review

Use the review date as `YYYY-MM-DD`.

```bash
python python/run_production.py --as-of YYYY-MM-DD
```

Example:

```bash
python python/run_production.py --as-of 2026-09-06
```

This runs the production chain:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

A normal annual review does **not** require deleting `output/`. Valid checkpoints are reused automatically.

### If you intentionally want a clean rebuild

Only do this when a deliberate full rebuild is required:

```bash
rm -rf output/*
python python/run_production.py --as-of YYYY-MM-DD
```

### Optional: run selected Purposes

```bash
python python/run_production.py --as-of YYYY-MM-DD --purposes Retirement Edu_B
```

### If a previous upstream run was interrupted

Resume from the appropriate persisted checkpoint:

```bash
python python/run_production.py --as-of YYYY-MM-DD --resume-from global
```

or:

```bash
python python/run_production.py --as-of YYYY-MM-DD --resume-from mission
```

Use these only when an interrupted run needs to be resumed.

---

# 3. MANUAL CHECKPOINT — review the production result

**Stop here and review before continuing.**

For each Purpose in the review, inspect:

```text
output/final_<Purpose>_summary.csv
```

For example:

```text
output/final_Retirement_summary.csv
output/final_Edu_B_summary.csv
output/final_Home_Loan_summary.csv
output/final_Marriage_summary.csv
output/final_Stitch_summary.csv
output/final_Kutti_summary.csv
```

Check:

- the file exists for every Purpose being reviewed;
- the run completed without an error;
- a FINAL winner is present;
- the summary looks complete and sensible.

If anything is missing or unexpected, **stop**. Do not manually edit the output to make the review continue. See [Errors and recovery](#9-errors-and-recovery).

The detailed FINAL evidence is available in `output/` if a deeper review is needed.

---

# 4. Run Family Architecture Validation

After the production review has completed successfully:

```bash
python python/run_family_attribution.py --as-of YYYY-MM-DD
```

Example:

```bash
python python/run_family_attribution.py --as-of 2026-09-06
```

This creates the family-level review artifacts under:

```text
data/reviews/YYYY-MM-DD/
```

The main files are:

```text
family_capital_attribution.csv
family_fund_concentration.csv
family_amc_concentration.csv
family_purpose_dependency.csv
family_attribution_manifest.json
```

---

# 5. MANUAL CHECKPOINT — review the family picture

**Stop here and review before starting Purpose Staging.**

Open the four CSV files above and look at:

1. how family capital is attributed across funds;
2. fund concentration;
3. AMC concentration;
4. which Purposes depend on which funds/compositions.

This step is **observation only**. Do not change the FINAL winners manually because of what you see here.

If the result is understood and the family is ready to review its Purpose requirements, continue to Purpose Staging.

---

# 6. Start Purpose Staging

Purpose Staging is the review workspace used to adjust Purpose requirements and redistribute released capital/SIP before committing the new Purpose state.

Initialize it once for the review:

```bash
python python/run_purpose_staging.py init --as-of YYYY-MM-DD
```

Example:

```bash
python python/run_purpose_staging.py init --as-of 2026-09-06
```

The workspace is created at:

```text
data/reviews/YYYY-MM-DD/purpose_staging/
```

It contains:

```text
purposes_staged.csv
reconciliation_ledger.csv
achievability_latest.csv
staging_state.json
staging.log
```

The authoritative `data/purpose/purposes.csv` is **not changed** by `init`.

---

# 7. MANUAL CHECKPOINT — decide what to change in Purpose Staging

Before each staging turn, the reviewer decides what should happen.

The reviewer can change:

- `value` — current capital;
- `monthly_plan` — monthly SIP/contribution;
- `desired` — target;
- `due` — target date;
- `analytical_horizon_years` — analytical horizon.

A turn can also specify:

- `capital_acquire_pct` — percentage of the available capital pool to give to a Purpose;
- `sip_acquire_pct` — percentage of the available monthly-SIP pool to give to a Purpose.

Create a small CSV for the turn with this exact header:

```text
purpose,value,monthly_plan,desired,due,analytical_horizon_years,capital_acquire_pct,sip_acquire_pct
```

Leave a field blank when it should remain unchanged.

Example:

```text
purpose,value,monthly_plan,desired,due,analytical_horizon_years,capital_acquire_pct,sip_acquire_pct
Home_Loan,600000,10000,,,,,
Retirement,,,,,,60,
```

Save the file somewhere convenient, for example:

```text
review_turn_01.csv
```

### Important

Do **not** increase `value` or `monthly_plan` directly to create money or SIP.

If a Purpose needs additional capital or SIP, first release it from another Purpose by reducing its staged `value` or `monthly_plan`, then allocate the available pool using acquisition percentages.

---

# 8. Run the staging turn

```bash
python python/run_purpose_staging.py turn --as-of YYYY-MM-DD --input path/to/turn.csv
```

Example:

```bash
python python/run_purpose_staging.py turn --as-of 2026-09-06 --input review_turn_01.csv
```

The system will:

1. apply the requested Purpose changes;
2. put reductions in `value` into the capital pool;
3. put reductions in `monthly_plan` into the SIP pool;
4. allocate requested pool percentages;
5. update the reconciliation ledger;
6. recalculate Achievability; and
7. stop for review.

Acquisition percentages in a turn are applied to the **same pool available at the start of the acquisition phase**. They are not applied sequentially to a shrinking pool.

Any unallocated pool remains available for the next turn.

---

# 9. MANUAL CHECKPOINT — review every staging turn

After **every** `turn` command, stop and inspect:

```text
data/reviews/YYYY-MM-DD/purpose_staging/purposes_staged.csv
data/reviews/YYYY-MM-DD/purpose_staging/reconciliation_ledger.csv
data/reviews/YYYY-MM-DD/purpose_staging/achievability_latest.csv
data/reviews/YYYY-MM-DD/purpose_staging/staging_state.json
```

Check:

### A. Purpose values

Are the staged `value`, `monthly_plan`, `desired` and dates what the reviewer intended?

### B. Pool balances

Check `staging_state.json`:

```text
pool_capital
pool_monthly_sip
```

Make sure every released amount is accounted for.

### C. Reconciliation ledger

Check that every release and acquisition appears in:

```text
reconciliation_ledger.csv
```

### D. Achievability

Check:

```text
achievability_latest.csv
```

Pay particular attention to the status for each finite-target Purpose.

Possible statuses are:

```text
NOT_APPLICABLE
INSUFFICIENT_EVIDENCE
WITHIN_OBSERVED_TERRAIN
BEYOND_OBSERVED_TERRAIN
```

The system is reporting the consequence of the reviewer's changes. It is not choosing the family priority.

### E. Decide whether another turn is needed

If the staged state is not yet what the family wants, prepare another turn and repeat:

```text
review → turn → inspect → review → turn → inspect → ...
```

There is no fixed number of turns.

---

# 10. Finish Purpose Staging

Only finish when:

- the reviewer is satisfied with every staged Purpose;
- all released capital has been deliberately allocated or otherwise reconciled;
- `pool_capital` is zero; and
- `pool_monthly_sip` is zero.

Then run:

```bash
python python/run_purpose_staging.py commit --as-of YYYY-MM-DD
```

Example:

```bash
python python/run_purpose_staging.py commit --as-of 2026-09-06
```

Before committing, the system backs up the authoritative Purpose file inside the staging workspace as:

```text
purposes_before_commit.csv
```

The staged Purpose file is then promoted to:

```text
data/purpose/purposes.csv
```

A non-zero capital or SIP pool blocks the commit.

---

# 11. MANUAL CHECKPOINT — after commit

Confirm that:

- the command completed successfully;
- the staging state is `COMMITTED`;
- `data/purpose/purposes.csv` contains the intended final Purpose state;
- `purposes_before_commit.csv` exists in the staging workspace.

Keep the annual review archive under:

```text
data/reviews/YYYY-MM-DD/
```

Commit the intended annual review artifacts to Git according to the repository's normal review practice.

---

# 12. What happens next

At this point the analytical review and Purpose reconciliation are complete.

The next Lakshya stage is the separate **CURRENT → TARGET transition**:

```text
actual holdings
      ↓
redemption / cost / tax / exit constraints
      ↓
transition plan
      ↓
reinvestment
      ↓
target architecture
```

Do **not** treat the FINAL winner or Purpose Staging result as an instruction to immediately sell or buy units. Actual redemption and reinvestment require the separate transition-planning stage.

---

# 13. Errors and recovery

## Rule 1 — stop when a command fails

If a command exits with an error:

1. stop;
2. read the error message carefully;
3. do not edit generated files to work around it;
4. do not continue to the next manual checkpoint;
5. fix the stated input/checkpoint problem or ask for help.

## Rule 2 — do not delete historical review archives

Do not delete or overwrite files under:

```text
data/reviews/YYYY-MM-DD/
```

unless there is an explicit reason to correct a review record.

## Common problems

### `Purpose source is missing required columns`

Check:

```text
data/purpose/purposes.csv
```

The required columns are:

```text
name,due,value,desired,monthly_plan,analytical_horizon_years
```

### `Unknown Purpose(s)`

The command or staging CSV contains a Purpose name that is not present in the current Purpose source. Check the spelling against `data/purpose/purposes.csv`.

### `Staging state missing; initialize first`

Run:

```bash
python python/run_purpose_staging.py init --as-of YYYY-MM-DD
```

Do not create `staging_state.json` manually.

### `Acquisition percentages cannot exceed 100%`

The total capital acquisition percentages, or total SIP acquisition percentages, in that turn exceed 100%. Correct the turn CSV and run the turn again.

### `Purpose ... increased value ... through pool percentages`

A staging turn tried to increase `value` directly. Reduce another Purpose first to release capital, then allocate the pool with `capital_acquire_pct`.

### `Purpose ... increased monthly_plan ... through pool percentages`

A staging turn tried to increase SIP directly. Reduce another Purpose's `monthly_plan` first to release SIP, then allocate the pool with `sip_acquire_pct`.

### `Required MISSION checkpoint is missing`

The production run has not produced the required MISSION survivor checkpoint for that Purpose, or the checkpoint is not available for the requested review. Stop and rerun/check the production stage before attempting FINAL again.

### `MISSION checkpoint is empty`

Stop. Do not try to manufacture a winner. Rerun/check the production pipeline and inspect the relevant MISSION output.

### Commit says the pool is non-zero

Do not force the commit. Return to the staging turns and deliberately allocate the remaining capital/SIP pool, then run `commit` again.

---

# 14. If you are unsure what to do

Use this decision tree:

```text
Command failed?
    ↓ yes
STOP → read error → fix input/checkpoint → rerun

Command succeeded?
    ↓
Manual checkpoint
    ↓
Result understood?
    ├── no  → STOP and ask for help
    └── yes
          ↓
     next stage
```

For Purpose Staging:

```text
turn
 ↓
inspect values + ledger + pools + Achievability
 ↓
satisfied?
 ├── no → another turn
 └── yes
        ↓
pools both zero?
 ├── no → reconcile pool
 └── yes
        ↓
commit
```

---

# 15. One-page annual checklist

```text
[ ] Update/check data/purpose/purposes.csv

[ ] Run production
    python python/run_production.py --as-of YYYY-MM-DD

[ ] CHECKPOINT: inspect final_<Purpose>_summary.csv for every Purpose

[ ] Run Family Architecture Validation
    python python/run_family_attribution.py --as-of YYYY-MM-DD

[ ] CHECKPOINT: inspect family attribution / concentration / dependency

[ ] Initialize Purpose Staging
    python python/run_purpose_staging.py init --as-of YYYY-MM-DD

[ ] CHECKPOINT: decide the Purpose changes for this turn

[ ] Run staging turn
    python python/run_purpose_staging.py turn --as-of YYYY-MM-DD --input turn.csv

[ ] CHECKPOINT: inspect staged Purposes, ledger, pools and Achievability

[ ] Repeat staging turns until satisfied

[ ] CHECKPOINT: confirm capital pool = 0 and SIP pool = 0

[ ] Commit Purpose Staging
    python python/run_purpose_staging.py commit --as-of YYYY-MM-DD

[ ] CHECKPOINT: confirm authoritative purposes.csv and backup

[ ] STOP

[ ] CURRENT → TARGET transition planning is the next separate stage
```
