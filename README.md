# Lakshya

Lakshya is a **family-specific investment-engineering system** for observing what the family actually owns, forming what the family should own, and planning how to move from one to the other.

Its architecture is deliberately split into three bounded systems:

```text
LPS — Lakshya Position System
What capital do we actually have?
        ↓
LFS — Lakshya Formation System
What investment formation should we have?
        ↓
LTS — Lakshya Transition System
How do we move from CURRENT to TARGET?
```

> **LPS observes. LFS forms. LTS transitions.**

> **Information should be introduced at the layer that genuinely earns the need for it.**

> **Compute once. Persist immediately. Reuse forever.**

---

# 1. LPS — Lakshya Position System

### What capital do we actually have?

LPS owns the family's **factual investment world**. It ingests authoritative source evidence, validates Transactions, reconstructs Positions, maintains NAV/valuation observations, and provides CURRENT to transition analysis.

The core data model is deliberately small:

```text
LPS
├── Transactions
└── Positions
```

A Position is identified by:

```text
Investor + Folio + ISIN
```

One Position may have many historical Transactions. Position is first-class. There is **no Portfolio dimension** and **no `CurrentState` domain object**.

Purpose mapping is human-maintained:

```text
one Position → exactly one Purpose
one Purpose  → zero, one, or many Positions
```

LPS does not guess Purpose mapping, invent missing facts, or automatically rebalance an over-target Purpose.

### Temporal semantics

LPS keeps these distinct:

```text
transaction_through_date
valuation_as_of_date
```

NAV evidence stores actual observations only. A NAV read "as of X" returns the latest recorded observation on or before X. No holiday NAVs are invented and no calendar-day interpolation is performed.

CURRENT is a **valuation snapshot/view**, not another domain entity.

---

# 2. LFS — Lakshya Formation System

### What investment formation should we have?

LFS forms the reviewed target architecture through the established analytical stages:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

TARGET is deliberately **not** a pre-staging optimization stage. It is derived only after the reviewed Purpose state has passed Purpose Staging:

```text
FINAL
  ↓
Purpose Staging
  ↓
Historical Snapshot
  ↓
TARGET
```

| Stage | Native question |
|---|---|
| FUND | What kind of teammate is this fund? |
| TEAM | What kind of collective do these teammates form? |
| COMPOSITION | Where does capital sit within a collective? |
| MISSION | Can this Composition serve this Purpose? |
| FINAL | Among qualified Compositions, which is the strongest practical compromise? |
| TARGET | What fund-level formation follows from the reviewed Purpose state and selected FINAL decisions? |

FUND establishes observed individual-fund behaviour, including Elevation and Protection. TEAM forms singleton/pair/trio collectives and applies the 40-dimensional Elevation + Protection comparator. COMPOSITION explores complete positive allocations. MISSION introduces Purpose semantics. FINAL performs production compromise ordering.

The production FINAL surface is:

```text
7 Elevation dimensions at selected horizon
+
12 native Protection dimensions
```

Zero-variance spokes are removed deterministically; retained spokes are equally weighted. Primary ordering is minimum unweighted Euclidean distance to the observed Utopia Point. L-infinity is a diagnostic/joint-frontier dimension, not an arbitrary kill threshold. FINAL also records Lp sweep, leave-one-spoke sensitivity, and 5,000 deterministic bootstrap resamples.

The family controls `data/purpose/purposes.csv`. LFS does not parse CAS, reconstruct actual holdings, or execute transactions.

---

# 3. Post-FINAL human review

After FINAL, the review enters a deliberately separate human-controlled staging boundary.

```text
FINAL
  ↓
PURPOSE STAGING
  ↓
HISTORICAL SNAPSHOT
```

## Purpose Staging

Purpose Staging is a **human-in-the-loop reconciliation workspace**. The reviewer can change only the permitted staging levers: `value`, `monthly_plan`, and capital/SIP acquisition percentages. Each Purpose's `desired` target and `due` date remain fixed context; analytical horizon is derived and is not a staging input.

```text
Purpose reduction → common pool
pool acquisition  → another Purpose
```

No capital or SIP may be silently created. The authoritative `purposes.csv` changes only at explicit COMMIT after reviewer satisfaction and both pools are zero.

---

# 4. Historical Snapshot

The annual snapshot is a human-controlled Git persistence boundary. After Purpose Staging is committed, the reviewer inspects intended changes and commits the reviewed state.

```text
data/lps/
data/purpose/
data/lfs/
```

Runtime output and forensic logs remain disposable/Git-ignored where configured. Historical memory is not a transaction ledger and does not prove current holdings.

---

# 5. CURRENT and TARGET

The annual-review hand-off is deliberately ordered:

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
ANALYTICAL CURRENT = what the reviewed Lakshya architecture says
ECONOMIC CURRENT   = what the family actually owns
TARGET             = what the reviewed Purpose state + FINAL decisions imply should be owned
```

LPS supplies Economic CURRENT from source evidence. TARGET is the fund-level formation implied by the committed Purpose state and selected FINAL Composition decisions. Neither state is inferred from the other.

---

# 6. LTS — Lakshya Transition System

### How do we move from CURRENT to TARGET?

LTS receives:

```text
LPS → Economic CURRENT + factual history
LFS → TARGET from reviewed decisions
```

It performs constrained transition analysis:

```text
CURRENT
   ↓
match / retain / change
   ↓
source-evidenced constraints
   ↓
feasible sequence
   ↓
human transition plan
```

Possible constraints include acquisition history, lock-ins, tax consequences, exit loads, transaction costs, liquidity, minimum transaction rules, and sequencing — but only where the source actually provides the required facts.

LTS is **not a second portfolio optimizer** and does not execute transactions.

---

# 7. Annual review flow

```text
AUTHORITATIVE SOURCE EVIDENCE
          │
          ▼
        LPS
 Transactions → Positions → valuation
          │
          ├──────────────────────────────┐
          ▼                              │
        LFS-MAIN                         │
 FUND → TEAM → COMPOSITION → MISSION → FINAL
                                         │
                                         ▼
                                  PURPOSE STAGING
                                         │
                                         ▼
                                  HISTORICAL SNAPSHOT
                                         │
                                         ▼
                                       CURRENT
                                         │
                                         ▼
                                       TARGET
                                         │
                                         ▼
                                  LTS CURRENT → TARGET
```

LPS also supplies factual Transition Evidence directly to LTS. The LFS formation chain and the LPS factual chain remain separate bounded responsibilities.

For the practical annual procedure, see `docs/Lakshya_HowTo.md`.
For execution sequence and persistence boundaries, see `docs/Lakshya_Pipeline_Sequence.md`.
For the architectural contract, see `docs/Lakshya_Architecture.md`.

---

# 8. Evidence philosophy

Lakshya preserves depth.

**30,000 feet ↔ 3 feet**

Observed is not inferred. Unknown is not zero. Compression may organize evidence, but must not erase meaning.

```text
PHILOSOPHY
    ↓
SPECIFICATION
    ↓
TESTS
    ↓
IMPLEMENTATION
    ↓
EVIDENCE
    ↓
INTERPRETATION
```

> **The domain model is allowed to dictate the implementation; implementation convenience is not allowed to invent domain concepts.**

That is why Lakshya has Transactions and Positions rather than `CanonicalTransaction`, and why CURRENT is a valuation view rather than a `CurrentState` entity.

---

# 9. Production release discipline

```text
FINAL_CONTRACT_VERSION = 1
```

Changes to the production decision rule require a deliberate versioned release with tests and documentation.

> **We were not searching for a portfolio. We were building a road on which a portfolio could eventually be discovered.**

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


## Documentation navigation

The existing documents retain their original detail and remain the primary references:

- `docs/Lakshya_Architecture.md` — complete production architecture and cross-context contracts.
- `docs/Lakshya_Domain_Model.md` — bounded contexts, ubiquitous language, and invariants.
- `docs/Lakshya_HowTo.md` — practical operating procedures and review gates.
- `docs/Lakshya_Pipeline_Sequence.md` — execution, persistence, and reconciliation sequence.
- `docs/architecture/historical_position_snapshot.md` — historical snapshot boundary.
- `docs/architecture/resilient_pipeline_decomposition.md` — decomposition and resilience principles.
