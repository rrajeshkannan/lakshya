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
FUND → TEAM → COMPOSITION → MISSION → FINAL → TARGET
```

| Stage | Native question |
|---|---|
| FUND | What kind of teammate is this fund? |
| TEAM | What kind of collective do these teammates form? |
| COMPOSITION | Where does capital sit within a collective? |
| MISSION | Can this Composition serve this Purpose? |
| FINAL | Among qualified Compositions, which is the strongest practical compromise? |
| TARGET | What fund-level formation follows from the reviewed Purpose decisions? |

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

# 3. Family review layers

After FINAL, two deliberately non-optimizing review layers precede the annual historical boundary:

```text
FINAL
  ↓
FAMILY ARCHITECTURE VALIDATION
  ↓
PURPOSE STAGING
  ↓
HISTORICAL SNAPSHOT
```

## Family Architecture Validation

This is **descriptive attribution, not optimization**. It asks where independently derived Purpose decisions create common Fund/AMC dependency.

```text
Purpose current capital
        ×
FINAL Composition fund weight
        =
Attributed capital
```

It observes Fund concentration, AMC/ecosystem concentration, and Purpose dependency. It does not alter FINAL, impose concentration limits, create substitute Compositions, or optimize family allocation.

## Purpose Staging

Purpose Staging is a **human-in-the-loop reconciliation workspace**. The reviewer can change `value`, `monthly_plan`, `desired`, `due` / analytical horizon, and capital/SIP acquisition percentages.

```text
Purpose reduction → common pool
pool acquisition  → another Purpose
```

No capital or SIP may be silently created. The authoritative `purposes.csv` changes only at explicit COMMIT after reviewer satisfaction and both pools are zero.

---

# 4. Historical Snapshot

The annual snapshot is a human-controlled Git persistence boundary. After Purpose Staging is committed, the reviewer inspects intended changes and commits the reviewed state.

```text
data/fund/
data/purpose/
data/reviews/<as-of>/
```

Runtime output and forensic logs remain disposable/Git-ignored where configured. Historical memory is not a transaction ledger and does not prove current holdings.

---

# 5. LTS — Lakshya Transition System

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

The three states must remain distinct:

```text
ANALYTICAL CURRENT = what the reviewed Lakshya architecture says
ECONOMIC CURRENT   = what the family actually owns
TARGET             = what the reviewed decisions imply should be owned
```

---

# 6. Annual review flow

```text
HUMAN INPUTS
   │
   ├── funds_in_scope.csv
   └── purposes.csv
          │
          ▼
        LFS
 FUND → TEAM → COMPOSITION → MISSION → FINAL → TARGET
          │
          ▼
 Family Architecture Validation
          │
          ▼
 Purpose Staging
          │
          ▼
 Historical Snapshot
          │
          ▼
        LTS
 CURRENT ←──────────────→ TARGET
          │
          ▼
 Human transition plan / execution
```

LPS supplies the factual side independently:

```text
source evidence
    ↓
Transactions
    ↓
Positions
    ↓
valuation observation
    ↓
Economic CURRENT
```

Thus the LTS hand-off is:

```text
LPS → CURRENT + factual history
LFS → TARGET
```

---

# 7. Running Lakshya

Canonical analytical entry point:

```bash
python python/run_production.py --as-of YYYY-MM-DD
```

Example:

```bash
python python/run_production.py --as-of 2026-09-06
```

Selected Purposes may be supplied with `--purposes`. The production pipeline is checkpoint-aware and reuses valid persisted work.

For practical operation, see `docs/Lakshya_HowTo.md`.
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
