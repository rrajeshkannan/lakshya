# Lakshya Production Architecture

**Status:** Authoritative production architecture

**Release:** Domain Boundary Freeze v1

**As of:** 2026-09-08

This document defines Lakshya's production architecture. The authoritative bounded-context model and five cross-context contracts are specified in `docs/Lakshya_Domain_Model.md`. Execution detail belongs in `docs/Lakshya_Pipeline_Sequence.md`; practical operation belongs in `docs/Lakshya_HowTo.md`.

---

# 1. Architectural statement

Lakshya is a **family-specific investment-engineering system**, not a generic optimizer.

Its three bounded contexts answer three different questions:

```text
LPS — Lakshya Position System
What capital do we actually have?

LFS — Lakshya Formation System
What investment formation should we have?

LTS — Lakshya Transition System
Given what exists and what we intend, how can we move from one to the other?
```

The governing principles are:

> **LPS observes. LFS forms. LTS transitions.**

> **Information should be introduced at the layer that genuinely earns the need for it.**

> **A bounded context exposes what its consumer needs, not everything its producer happens to have.**

> **Compute once. Persist immediately. Reuse forever.**

The architecture separates factual observation, analytical formation, transition planning, human decision, and historical memory.

---

# 2. Domain map

```text
                         HUMAN
                           │
                           ▼
                          LPS
                   Lakshya Position System
                       │              │
                       │              │
                       ▼              ▼
                      LFS            LTS
             Lakshya Formation   Lakshya Transition
                  System              System
                       │              ▲
                       └──────────────┘
```

This is deliberately **not** a serial pipeline.

- LPS is the factual upstream system.
- LFS consumes formation evidence from LPS.
- LTS consumes transition evidence from LPS and formation intent from LFS.
- Human review and execution remain outside the analytical systems.

The five contracts defining these boundaries are:

```text
1. Formation Evidence       LPS → LFS
2. Transition Evidence      LPS → LTS
3. Formation Intent         LFS → LTS
4. Transition Proposal      LTS → Human / Staging
5. Reconciliation / Promotion
                            Human + new source evidence → LPS
```

See `docs/Lakshya_Domain_Model.md` for the complete contract definitions and invariants.

---

# 3. LPS — Lakshya Position System

## Native question

> **What capital do we actually have?**

LPS is the authoritative factual home for the family's investment world.

It owns:

- authoritative source evidence;
- normalized Transactions;
- historical transaction evidence;
- first-class Positions;
- NAV observations and valuation history;
- Position valuation at an observation date; and
- accepted human-maintained Position → Purpose attribution.

It does not own fund selection, behavioural Fund analysis, formation stages, transition decisions, or transaction execution.

## Position identity

An established Position is identified by:

```text
Investor + Folio + ISIN
```

Historical Transactions establish Position units and history.

A Position has exactly one Purpose attribution once accepted into LPS. A Purpose may have zero, one, or many Positions. A Purpose with zero Positions is therefore valid.

## Purpose mapping

The family defines Purpose. LPS records accepted Position → Purpose attribution and derives Purpose capital from Position valuation.

LPS does not infer Purpose attribution from fund identity, folio identity, transaction type, or formation intent.

## NAV and valuation

LPS stores sparse factual NAV observations and applies as-of semantics:

```text
NAV as of X
= latest recorded NAV observation on or before X
```

Transaction and valuation dates remain distinct facts.

## Formation Evidence

For LFS, LPS exposes a purpose-built formation projection:

```text
Funds represented by Positions
+
NAV observations / history
```

The reviewer may separately provide `potential_funds_in_scope` for funds not represented by existing Positions.

## Transition Evidence

For LTS, LPS exposes:

```text
Positions
+
relevant Transactions
+
Position → Purpose attribution
+
transition-relevant Fund metadata
```

The exact metadata surface is intentionally consumer-driven. Broader metadata remains subject to later dependency review.

---

# 4. LFS — Lakshya Formation System

## Native question

> **What investment formation should we have?**

LFS owns the complete formation engine:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL → TARGET
```

These are stages inside LFS, not separate bounded contexts.

## FUND

> **What kind of teammate is this fund?**

FUND establishes observed individual-fund behavioural evidence from NAV history.

Fund Fingerprint construction belongs entirely inside LFS. The Fund-level weak-Pareto pruning gate between FUND and TEAM also belongs inside LFS. LPS does not know Fund Fingerprints.

## TEAM

> **What kind of collective do these teammates form?**

TEAM forms deterministic singleton, pair, and trio candidates, maximum size 3, using the established 40-dimensional behavioural surface and exact weak Pareto non-dominance.

TEAM does not import Purpose semantics merely to reduce its universe.

## COMPOSITION

> **Where does capital sit within a collective?**

A Composition is Team + complete weights.

Canonical positive-weight grid:

```text
singleton = 100%
pair       = 19 allocations at 5% increments
trio      = 171 allocations at 5% increments
```

Composition fingerprints are durable reusable evidence. Expensive evidence is persisted immediately and consumed downstream rather than silently recomputed.

## MISSION

> **Can this Composition serve this Purpose?**

MISSION is the first formation stage where Purpose semantics enter the analytical contract.

Supported analytical horizons are:

```text
3Y / 5Y / 7Y / 10Y
```

For a finite Purpose horizon, the longest supported analytical horizon not exceeding that Purpose horizon is selected. History availability is evaluated per Composition; insufficient trajectory history produces an explicit insufficient-evidence result and does not eliminate a MISSION survivor.

## FINAL

> **Among already-qualified MISSION Compositions, which is the strongest practical compromise?**

FINAL performs the established compromise selection using the selected horizon, the retained Elevation and native Protection spokes, population-relative desirability, unweighted L2 as the primary norm, and the documented robustness diagnostics.

## TARGET

TARGET is not another optimizer. It is the formation implied by reviewed Purpose decisions and the selected FINAL Composition for each Purpose.

The LFS → LTS contract preserves the Purpose-level mapping even when multiple Purposes select the same Composition:

```text
Purpose A → Composition A
Purpose B → Composition A
Purpose C → Composition A
...
Purpose F → Composition B
```

LFS does not assign Investor, Folio, Position identity, tax treatment, or transition actions.

---

# 5. LTS — Lakshya Transition System

## Native question

> **Given what LPS tells us actually exists, and what LFS says we should have, how can we move from one to the other?**

LTS receives two intentionally different contracts:

```text
LPS → Transition Evidence
LFS → Formation Intent
```

Its work is constrained transition analysis:

```text
factual Positions
      +
formation intent
      ↓
match / retain / change / sequence
      ↓
transition simulation
      ↓
Transition Proposal
```

## Transition Proposal

LTS stages one or more candidate simulations containing:

```text
proposed Position transformation
+
proposed Purpose-attribution transformation
```

A proposed Position may contain:

```text
Investor + ISIN + Folio: NEW
```

`NEW` is a proposal marker, never a factual folio identity.

The proposal is non-authoritative and does not mutate LPS or execute transactions.

Multiple simulations may coexist. The reviewer chooses which proposal, if any, to effect.

LTS does not introduce an `Action` abstraction merely for implementation convenience. A new domain concept must earn its existence through demonstrated need.

## Transition constraints

Where genuinely evidenced by source material, LTS may reason about lock-ins, acquisition-date tax consequences, STCG/LTCG implications, exit loads, transaction costs, liquidity, minimum transaction constraints, and SIP/STP/SWP sequencing.

Missing facts remain missing. Lakshya does not manufacture tax lots, acquisition dates, costs, or folio facts.

## Human execution boundary

LTS proposes. The human executes.

LTS never executes transactions automatically, reopens formation selection, or changes TARGET merely because transition is inconvenient.

---

# 6. Reconciliation and Promotion

After a selected LTS proposal is effected by the human, the next authoritative MyCAMS evidence is imported into LPS.

LPS reconstructs the resulting factual Positions from the new evidence.

The reconciliation workflow then:

1. automatically detects factual changes and candidate matches to the staged proposal;
2. identifies newly observed Positions, including real folios corresponding to proposal `NEW` markers;
3. presents proposed Purpose attribution to the reviewer; and
4. records the reviewer's accepted Purpose attribution in LPS.

The governing rule is:

> **Automatic reconciliation. Human attribution acceptance.**

Therefore:

> **LTS proposes. External evidence establishes Positions. The human establishes Purpose attribution. LPS records the resulting factual state.**

Promotion does not manufacture a Position. It reconciles a proposal against subsequently observed evidence and records the accepted attribution.

---

# 7. Historical Snapshot

Historical Snapshot is the human-controlled Git persistence boundary for reviewed annual state and analytical evidence. It is not a transaction ledger and does not establish Position facts independently of LPS source evidence.

The durable record includes appropriate reviewed material under:

```text
data/fund/
data/purpose/
data/reviews/<as-of>/
```

Generated runtime output and forensic logs remain disposable where configured.

---

# 8. Domain invariants

1. **LPS observes. LFS forms. LTS transitions.**
2. Observed is not inferred.
3. Unknown is not zero.
4. One established Position maps to exactly one Purpose.
5. One Purpose may have zero, one, or many Positions.
6. A Purpose may exist before any Position is assigned to it.
7. Fund Fingerprints belong entirely inside LFS.
8. LTS never chooses TARGET formation.
9. LTS never mutates factual LPS Positions during simulation.
10. `NEW` is never a factual folio identity.
11. External source evidence establishes Position facts.
12. Human acceptance establishes Purpose attribution.
13. LTS proposals are non-authoritative.
14. LPS is the authoritative factual home of Transactions, Positions, and accepted Purpose attribution.
15. A downstream convenience must not silently alter an upstream analytical contract.
16. Domain concepts are not invented solely for implementation convenience.

---

# 9. What the architecture deliberately rejects

Without an earned domain need, Lakshya does not introduce:

- Portfolio as a separate dimension;
- a wrapper around Positions representing a second state model;
- a second Transaction concept;
- Fund Fingerprints outside LFS;
- automatic Purpose inference or trimming;
- hidden Purpose priority rankings;
- transition-time re-optimization of formation;
- fabricated folio identities;
- invented tax/cost facts; or
- automatic transaction execution.

This is deliberate conservatism, not missing functionality.

---

# 10. Engineering consequence

The contracts are the primary architectural fulcrum.

When a new requirement appears, the first question is:

> **Which bounded context genuinely owns this knowledge, and which contract earns the need for it?**

Implementation must express the domain model rather than silently redefine it.

The complete domain map, contract definitions, ubiquitous language, and invariants are maintained in `docs/Lakshya_Domain_Model.md`.
