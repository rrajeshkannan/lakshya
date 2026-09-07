# Lakshya Purpose Staging Review

## Purpose

Purpose Staging is a deliberately small human-in-the-loop review workspace after FINAL. It lets the reviewer experiment with Purpose requirements and common-pool redistribution without changing the authoritative `data/purpose/purposes.csv` until the reviewer explicitly commits.

The production architecture remains:

`FUND → TEAM → COMPOSITION → MISSION → FINAL → FAMILY ARCHITECTURE VALIDATION → PURPOSE STAGING → HISTORICAL SNAPSHOT`

After the annual snapshot is deliberately committed, the separate **CURRENT → TARGET transition** begins. Purpose Staging does not perform that transition and does not need actual holding/account information.

Purpose Staging does **not** alter FUND, TEAM, COMPOSITION, MISSION, FINAL, or the selected FINAL Composition. It reruns only the existing Achievability calculation against the observed upper return already persisted for each Purpose's FINAL winner.

## Reviewer controls

The staged Purpose retains the four Purpose controls already present in `purposes.csv`:

- `value` — current capital
- `monthly_plan` — monthly contribution
- `desired` — target capital
- `due` / `analytical_horizon_years` — Purpose horizon

A turn may also contain:

- `capital_acquire_pct` — percentage of the currently available capital pool to acquire for that Purpose
- `sip_acquire_pct` — percentage of the currently available monthly-SIP pool to acquire for that Purpose

Acquisition percentages are reviewer instructions for that turn. They are not stored as family priorities and do not teach Lakshya any Purpose ranking.

## Staging lifecycle

### 1. Initialize

```bash
python python/run_purpose_staging.py init --as-of 2026-09-06
```

Creates under `data/reviews/<as-of>/purpose_staging/`:

- `purposes_staged.csv` — isolated working copy
- `reconciliation_ledger.csv` — cumulative turn-by-turn economic movements
- `achievability_latest.csv` — latest analytical result
- `staging_state.json` — workspace state and pool balances
- `staging.log` — forensic review log

The authoritative `data/purpose/purposes.csv` is not changed.

### 2. Run a review turn

Prepare a CSV containing the required header:

```text
purpose,value,monthly_plan,desired,due,analytical_horizon_years,capital_acquire_pct,sip_acquire_pct
```

Blank lever fields mean “leave unchanged.” A turn can contain one or more Purposes.

Example:

```text
purpose,value,monthly_plan,desired,due,analytical_horizon_years,capital_acquire_pct,sip_acquire_pct
Home_Loan,600000,10000,,,,,
Retirement,,,,,,60,
```

Then:

```bash
python python/run_purpose_staging.py turn --as-of 2026-09-06 --input path/to/turn.csv
```

The turn:

1. applies the reviewer’s staged lever changes;
2. releases reductions in `value` and `monthly_plan` into their respective pools;
3. applies acquisition percentages to the pool available at the start of the acquisition phase;
4. records the movement in the cumulative ledger;
5. reruns Achievability for every staged Purpose; and
6. pauses for the reviewer to inspect the new state.

A percentage is always applied to the pool available for that turn. For example, 60% and 40% recipients receive 60% and 40% of the same pool base; they are not applied sequentially to a shrinking pool.

Any unallocated pool remains in the staging workspace for the next turn.

## Important accounting rule

A reviewer may not silently create capital or SIP by increasing `value` or `monthly_plan`. Increases are funded through the common-pool acquisition instruction. This preserves the conservation principle during review.

Changes to `desired` or horizon alter the Purpose requirement and therefore its Achievability result. They do not by themselves manufacture a cash release. An actual capital/SIP release enters the pool when the staged `value` or `monthly_plan` is reduced.

## 3. Repeat

The reviewer can run as many turns as necessary:

`input → working → Achievability → result → input → ...`

There is no priority field and no automatic “most important Purpose” decision. The system knows only the analytical state; the reviewer expresses family priority through the Purpose levers and the acquisition percentages for each turn.

## 4. Commit

Commit only when the reviewer is satisfied and both common-pool balances are zero:

```bash
python python/run_purpose_staging.py commit --as-of 2026-09-06
```

Before commit, the authoritative Purpose file is backed up into the staging workspace as `purposes_before_commit.csv`. The staged file is then promoted to `data/purpose/purposes.csv` and the workspace becomes `COMMITTED`.

A non-zero remaining pool blocks commit. This prevents an incomplete redistribution from silently becoming the new authoritative Purpose state.

## Historical handoff

Purpose Staging is not itself the annual persistence boundary. After an explicit successful commit, the reviewer inspects the intended annual `data/` changes and deliberately commits the historical snapshot to Git.

The resulting historical snapshot is the durable handoff into the next annual review. It is **not** a transaction ledger and it does not contain an automatically derived actual-holdings state.

The next stage is deliberately separate:

```text
HISTORICAL SNAPSHOT
        ↓
CURRENT → TARGET transition
```

## Design position

Purpose Staging is a review workspace, not an optimizer. Its job is to make the arithmetic and conservation bookkeeping easy while leaving family prioritisation with the human reviewer.

The reviewer controls the terrain; Lakshya calculates the consequences.
