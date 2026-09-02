# Lakshya — Current Architecture Checkpoint

**Status:** Authoritative current architectural handoff

**As of:** 2026-09-02

This document consolidates the architectural decisions that must survive conversation and implementation boundaries. When an older stage checkpoint conflicts with this document, this checkpoint is the current decision record; older checkpoints remain historical context.

---

## 1. Fundamental architecture

```text
FUND → TEAM → COMPOSITION → MISSION → TRAJECTORY → FUTURE ENVIRONMENT
```

The core principle is:

> **Information should be introduced at the layer that genuinely earns the need for it.**

And for expensive analytical evidence:

> **Compute once. Persist immediately. Reuse forever.**

Lakshya values functionality, analytical richness, correctness, reproducibility and interpretability ahead of wall-clock speed. Performance should be improved without sacrificing useful evidence.

---

## 2. FUND admission

Fund Admission distinguishes only:

- `CURRENT` — an existing standing fund;
- `POTENTIAL` — a possible new entrant.

The **8-year lived-history requirement applies only to POTENTIAL/new-entry funds**.

A CURRENT fund may be younger than 8 years and still proceed through TEAM, COMPOSITION and MISSION.

Regular-vs-Direct is **not a Lakshya behavioural distinction**. Lakshya must not discriminate between Regular and Direct plans merely because of plan type. Once a Fund is admitted, `CURRENT`/`POTENTIAL` must not leak into downstream behavioural semantics.

The current scope contains 17 Funds. Maximum Team size is 3.

---

## 3. TEAM

TEAM asks:

> **What kind of collective do these teammates form?**

The current Team universe is:

- singleton;
- pair;
- trio.

With 17 Funds and maximum Team size 3, this gives:

- 17 singleton Teams;
- 136 pairs;
- 680 trios;
- 833 Team candidates.

TEAM uses a deliberately weak exact Pareto frontier: only candidates dominated across the complete declared surface are removed.

Current TEAM gate surface:

- 28 Elevation dimensions;
- 12 Protection dimensions;
- 40 total.

FUND Resilience is currently **not** part of the TEAM gate. This is an intentional boundary decision, not a claim that Resilience is unimportant.

TEAM must not import Purpose/MISSION semantics merely to shrink its own universe.

---

## 4. COMPOSITION

A Composition is:

> **Team + complete weights.**

Generated multi-member Compositions use strictly positive weights.

Weight grids:

- singleton: 100%;
- twin: 19 allocations, 5/95 through 95/5;
- trio: 171 allocations on the 5% grid.

The generated candidate universe from the current Team universe is 67,483 Compositions.

A global weak Pareto frontier is applied after Composition fingerprinting. The active persisted global checkpoint must be validated before reuse; historical counts must not be assumed to be current counts.

### Durable Composition evidence

Composition fingerprints are expensive evidence and are persisted individually with:

- stable Composition identity;
- schema version;
- complete Composition/member/weight information;
- NAV evidence;
- Elevation 3Y/5Y/7Y/10Y evidence;
- complete Protection evidence.

Downstream stages load persisted fingerprints rather than recalculating them.

---

## 5. MISSION

MISSION asks:

> **Can this Composition serve this Purpose?**

Current Purpose horizons as of 2026-08-31:

| Purpose | Horizon |
|---|---:|
| Edu_B | 4Y |
| Retirement | 12Y |
| Marriage | 9Y |
| Home_Loan | 9Y |
| Stitch | none |
| Kutti | none |

Purpose model includes purpose identity/current state, required amount, target date/horizon, relative importance and associated-capital relationship.

Stitch/Kutti capital remains associated with Stitch/Kutti at annual review; TEAM/Composition may change but that capital is not freely reallocated elsewhere.

Home_Marriage capital may be redirected toward Retirement if evidence shows Retirement needs more funding.

FAMILY does not prescribe Team or Composition.

### Achievability

MISSION compares the Purpose requirement against observed Elevation terrain.

The analytical horizons are fixed at:

**3Y / 5Y / 7Y / 10Y**

For a Purpose horizon, select the **longest supported analytical horizon <= the Purpose horizon**.

Examples:

- 4Y → 3Y
- 6Y → 5Y
- 8Y → 7Y
- 9Y → 7Y
- 12Y → 10Y

A Purpose does not demand an equally long lived history.

Protection is a separate weak Pareto frontier after achievability.

---

## 6. TRAJECTORY — current contract

TRAJECTORY is **descriptive only**. It does not rank, score, prune or change MISSION survivors.

The crucial symmetry with Elevation is:

> **TRAJECTORY uses the same analytical horizon vocabulary: 3Y / 5Y / 7Y / 10Y.**

A Purpose's 9Y or 12Y horizon must never become a new 9Y or 12Y trajectory horizon.

### Horizon selection

TRAJECTORY first selects the nominal analytical lens using:

> **largest member of {3, 5, 7, 10} that is <= Purpose horizon**

Then, **per MISSION-surviving Composition**, history availability is checked.

If the nominal lens is unavailable, fall back to the next lower canonical lens:

```text
7Y → 5Y → 3Y
10Y → 7Y → 5Y → 3Y
5Y → 3Y
3Y → no observation if unavailable
```

The Composition remains a MISSION survivor throughout.

If no canonical trajectory horizon is observable, record an explicit insufficient-history status rather than silently dropping the survivor or treating missing evidence as zero.

The output must make the distinction visible through fields such as:

- Purpose horizon;
- requested/nominal analytical horizon;
- actual observed trajectory horizon;
- trajectory status.

### Underlying observation convention

`observe_trajectory()` retains the latest observed NAV on or before the requested lookback target as the starting point and preserves the full observed path through the latest NAV. It does not invent observations.

Thus TRAJECTORY reports the best defensible canonical lived-history lens; it does not manufacture a Purpose-length path.

---

## 7. The key boundary lesson

The recent Marriage failure exposed a parameter-leak bug:

```text
WRONG
Purpose.horizon_years → TRAJECTORY horizon

CORRECT
Purpose.horizon_years
        ↓
MISSION analytical comparison
        ↓
canonical 3/5/7/10Y lens
        ↓
TRAJECTORY
```

Marriage = 9Y therefore uses a 7Y lens.
Retirement = 12Y therefore uses a 10Y lens.

The purpose horizon belongs to MISSION. The analytical horizon ladder belongs to Elevation/TRAJECTORY.

This distinction is an architectural invariant and must be protected by tests.

---

## 8. Current real-data checkpoints

The resilient runner has already produced valid upstream evidence that should be reused rather than recomputed unless validation fails.

The latest relevant run loaded **36,665 persisted Global survivors** and completed MISSION for all four finite-horizon Purposes:

- Retirement: 36 MISSION survivors;
- Edu_B: 245;
- Marriage: 245;
- Home_Loan: 245.

MISSION results are therefore upstream of the current trajectory correction.

The old trajectory attempts are **not final** because they used incorrect Purpose-specific horizons:

- Retirement was attempted with 12Y;
- Edu_B with 4Y;
- Marriage attempted 9Y and failed on insufficient history;
- Home_Loan had not completed before the run stopped.

Do not discard the upstream evidence merely because the downstream trajectory implementation was wrong.

The next run should therefore begin from persisted MISSION outputs and regenerate only the corrected TRAJECTORY layer.

---

## 9. Durable execution architecture

Core invariant:

```text
compute → persist → validate → consume
```

Implemented resilience includes:

- individual Composition fingerprint persistence;
- atomic persistence;
- schema and identity validation;
- durable CSV stage checkpoints;
- completion markers;
- input provenance and content hashes;
- ProcessPoolExecutor parallelism;
- worker-context-safe `as_of` propagation;
- failure isolation for expensive Composition work;
- restart/resume paths;
- manifest state;
- console/forensic logging separation.

### Observability

Console is the macro operational dashboard: stage, progress, counts, rate, ETA.

Forensic log is a detailed flight recorder with wall-clock timestamps and structured events.

They must not become duplicate streams.

---

## 10. Testing philosophy

Architectural decisions must be encoded in executable tests, not retained only in conversation.

Tests should protect:

- CURRENT/POTENTIAL admission semantics;
- no Regular/Direct behavioural discrimination;
- canonical 3/5/7/10Y horizon ladder;
- nearest-supported-horizon convention;
- per-Composition trajectory fallback;
- insufficient-history as explicit descriptive state;
- MISSION survivor preservation;
- deterministic results;
- serial/parallel equivalence;
- restartability;
- checkpoint integrity;
- atomicity;
- logging separation.

---

## 11. Engineering priority

The project deliberately prioritizes:

1. architectural correctness;
2. richness and usefulness of analytical outcome;
3. evidence preservation;
4. reproducibility and auditability;
5. resilience/restartability;
6. performance.

Wall-clock time matters because it is the user's waiting time, but speed must not justify weakening the analytical outcome.

---

## 12. Immediate next step

1. Validate the current branch implementation against this checkpoint.
2. Ensure the TRAJECTORY contract is implemented exactly as above.
3. Run the complete automated suite.
4. Inspect existing trajectory outputs for safely reusable raw evidence, but do not treat them as final until validated under the new contract.
5. Re-run only the necessary TRAJECTORY work from persisted MISSION survivors.
6. Inspect the resulting analytical outcomes, not merely process success.

This document is the current architectural memory checkpoint for future conversations.
