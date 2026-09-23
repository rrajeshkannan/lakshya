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
