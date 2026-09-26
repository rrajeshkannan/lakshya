# LFS Historical Position Snapshot

## Purpose

LFS formation is evaluated at one explicit `formation_as_of` boundary.  The
financial Position state consumed by Purpose-capital formation must represent
that same boundary rather than the latest persisted Position valuation.

## Contract

```text
formation_as_of = T
        |
        +-- Transactions with transaction_date <= T
        |       -> net units by Investor + Folio + ISIN
        |
        +-- LPS NAV evidence
        |       -> latest recorded NAV on or before T
        |
        +-- accepted Position Purpose attribution
        |
        v
Positions_AsOf(T)
        |
        v
Purpose.capital
        |
        v
MISSION Achievability
```

The historical adapter is an LFS input-formation concern. It does not teach
MISSION or Achievability how to value Positions.

## Persistence and resume

The single LFS runner forms the historical Position snapshot once at the input
boundary and persists it under `output/` as:

```text
positions_as_of_<YYYY-MM-DD>.csv
positions_as_of_<YYYY-MM-DD>.csv.complete.json
```

The completion marker binds the snapshot to its `as_of` date, output bytes,
and source-input hashes. A subsequent run can load the validated snapshot
instead of rebuilding it.

MISSION checkpoints additionally bind their completion markers to a hash of:

- `purposes.csv` intent; and
- the validated `Positions_AsOf(T)` snapshot.

Consequently, `resume_from="mission"` continues to reuse valid expensive
upstream evidence while recomputing MISSION when Purpose inputs have changed.
Trajectory checkpoints continue to depend on the resulting MISSION checkpoint.

## Attribution limitation

The current LPS Position state contains accepted Purpose attribution, but does
not yet persist effective-dated attribution history. The adapter therefore
carries the accepted attribution from the current Position state when forming
`Positions_AsOf(T)`. It does not invent historical attribution events. A future
LPS attribution-history contract can replace this input without changing the
MISSION Purpose model.

## Non-goals

- No persistent date/provenance fields are added to `Purpose` merely because
  `capital` is derived.
- `purposes.csv` remains intent-only.
- Achievability does not value Positions.
- Purpose Staging remains a separate current/review workflow.
- LFS does not acquire an independent valuation date separate from its
  formation boundary.

---

# Appendix — Current Implementation Status and Transition Boundary

**Status date:** 2026-09-26  
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

The current validation evidence includes:

- **696 lots** and **34 Position summaries**;
- **602 available** lots and **94 locked** lots;
- no negative lot balances in the validated result;
- six balanced Purpose reports; and
- numerical reconciliation within floating-point tolerance.

The 2026-09-26 clean run reconciles. The artifacts are a human review plan, not permission to execute transactions.

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

## Closed gaps

The 2026-09-26 clean run, with LPS, LFS, and LTS sharing as-of **2026-09-06**, closed the previously open implementation gaps:

1. Materialization is wired into `python -m lts.runner`. The runner writes `data/lts/materialized_transition_slices.csv` together with the mappings, purpose reports, availability files, and `manifest.json`.
2. Every FINAL-selected fund is funded at its Composition weight. `RETAIN` is the same-Purpose, same-ISIN overlap. A selected fund that the Purpose does not already hold is an `INVEST`, not a missing retain.
3. Position market value, the LFS position snapshot, availability, purpose reports, mappings, slices, and the manifest agree at **₹15,233,131.3171967**. The earlier ₹27,420.24 gap was a NAV-date split: positions had been priced at the 8 Sep print while availability used the 6 Sep as-of print (4 Sep). One shared as-of removes it.
4. The same-day Parag Parikh rows on folio `11002746` / `INF879O01027` are two real purchases. Their running balances step up by the purchased units, and the bank debits match. They are not copies to delete. A repeated zero-unit IFSC note does not change units. Same date, amount, and description are not enough to call two rows duplicates when the running balance differs. Do not silently drop rows.
5. The clean run reproduced the artifact set: 34 active positions, 696 lots (602 available, 94 locked), 46 mappings, 46 slices, and six balanced Purpose reports.

LTS artifacts remain a human review plan. They do not execute transactions and they do not mutate LPS.


## Snapshot implications for transition evidence

A historical snapshot that is used alongside transition analysis should preserve or reference:

- the source and transaction-through boundary;
- the valuation-as-of boundary;
- Position identity;
- accepted Purpose attribution;
- locked versus available interpretation;
- unresolved source anomalies; and
- the status of any transition artifact as proposed, reviewed, or promoted.

The snapshot remains historical memory. It must not be used as a substitute for fresh source evidence when establishing the family's current factual Positions.
