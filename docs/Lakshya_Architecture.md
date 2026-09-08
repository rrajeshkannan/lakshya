# Lakshya Production Architecture

**Status:** Authoritative production architecture

**Release:** FINAL / Compromise Programming v1

**As of:** 2026-09-08

This document defines the wider production architecture of Lakshya. `docs/Lakshya_Domain_Model.md` records the bounded-context language and the five cross-context contracts. `docs/Lakshya_Pipeline_Sequence.md` describes execution and persistence boundaries. `docs/Lakshya_HowTo.md` describes practical reviewer operation.

---

# 1. Architectural statement

Lakshya is a **family-specific investment-engineering system**, not a generic optimizer.

Its three bounded systems answer three different questions:

```text
LPS — Lakshya Position System
What capital do we actually have?

LFS — Lakshya Formation System
What investment formation should we have?

LTS — Lakshya Transition System
Given what LPS tells us actually exists, and what LFS says we should have,
how can we move from one to the other?
```

The governing principles are:

> **LPS observes. LFS forms. LTS transitions.**

> **Information should be introduced at the layer that genuinely earns the need for it.**

> **A bounded context exposes what its consumer needs, not everything its producer happens to have.**

> **Compute once. Persist immediately. Reuse forever.**

The architecture separates factual observation, analytical formation, transition planning, human decision, and historical memory. No later layer is allowed to quietly become an earlier layer's optimizer.

---

# 2. Domain map and contracts

```text
                         HUMAN
                           │
                           ▼
                          LPS
                   Lakshya Position System
                       │              │
             Formation Evidence      │ Transition Evidence
                       │              │
                       ▼              ▼
                      LFS ────────► LTS
             Lakshya Formation   Lakshya Transition
                  System              System
```

This is deliberately **not** a serial pipeline.

- LPS is the factual upstream system.
- LFS consumes Formation Evidence from LPS.
- LTS consumes Transition Evidence from LPS and Formation Intent from LFS.
- Human review and execution remain outside the analytical systems.

The five architectural contracts are:

```text
1. Formation Evidence       LPS → LFS
2. Transition Evidence      LPS → LTS
3. Formation Intent         LFS → LTS
4. Transition Proposal      LTS → Human / Staging
5. Promotion / Reconciliation
                            accepted attribution + new evidence → LPS
```

The contracts are deliberately **purpose-built projections**, not giant objects exported from LPS or LFS.

---

# 3. LPS — Lakshya Position System

## 3.1 Native question

> **What capital do we actually have?**

LPS is the authoritative factual home for the family's investment world. It observes; it does not form the target architecture.

It owns:

- authoritative source evidence;
- normalized Transactions;
- historical transaction evidence;
- first-class Positions;
- NAV observations and valuation history;
- Position valuation at an observation date; and
- accepted human-maintained Position → Purpose attribution.

It does not own fund selection, behavioural Fund analysis, formation stages, transition decisions, or transaction execution.

## 3.2 Source boundary

For mutual funds, the CAS is the authoritative evidence boundary for transactions and holdings/history.

Family source policy:

- request the CAS comfortably before the earliest family mutual-fund investment;
- include all folios, including zero-balance folios;
- retain original unmodified PDFs;
- enter passwords interactively and never store them;
- treat warnings or ambiguity as stop-and-ask-human conditions;
- perform full-history import for each annual review; and
- review validation before accepting factual holdings.

Parser-specific schemas remain implementation details. They must not leak into LFS or LTS.

## 3.3 Core data model

```text
LPS
│
├── Transaction
├── Transaction
├── ...
│
└── Position
    ├── Position Identity
    │   ├── Investor
    │   ├── Folio
    │   └── ISIN
    ├── Units
    └── valuation observation when applied
        ├── NAV
        ├── NAV observation date
        ├── valuation as-of date
        └── Market Value
```

Established Position identity is:

```text
Investor + Folio + ISIN
```

Historical Transactions establish Position units and history.

There is no Portfolio dimension. There is no second Position-state wrapper and no second Transaction concept merely for normalization convenience.

## 3.4 Purpose mapping

Purpose is human-defined. LPS records the accepted relationship:

```text
one Position → exactly one Purpose
one Purpose  → zero, one, or many Positions
```

LPS derives Purpose capital from Position valuation. It does not infer attribution from fund identity, folio identity, transaction type, or formation intent.

Unmapped Positions remain visible and require human attention. A Purpose with zero Positions is valid.

## 3.5 Temporal and valuation semantics

Two dates remain explicit:

```text
transaction_through_date
valuation_as_of_date
```

They need not be equal.

NAV write semantics are sparse:

- store actual recorded observations;
- do not manufacture holiday/weekend observations; and
- do not interpolate missing calendar days.

NAV read semantics are as-of:

```text
NAV as of X
= latest recorded NAV observation on or before X
```

## 3.6 Formation Evidence — LPS → LFS

LPS exposes a purpose-built Formation Evidence projection:

```text
FormationEvidence
├── funds
│   └── fund identity required by formation
└── nav_histories
    └── ISIN → normalized NAV history
```

The fund universe represented by Positions is automatically available. Separately, the human reviewer may supply:

```text
potential_funds_in_scope
```

for additional funds not represented by Positions.

No separate admissibility gate exists inside LFS. Reviewer-selected potential funds are assumed to have passed the human admissibility decision before entering this contract.

Formation Evidence contains no Position attribution, transaction history, transition information, or Fund Fingerprints.

The NAV acquisition mechanism must ultimately derive requested ISINs from Positions plus reviewer-selected potential funds rather than from the legacy `funds_in_scope.csv` mechanism.

## 3.7 Transition Evidence — LPS → LTS

LPS exposes a purpose-built Transition Evidence projection:

```text
Transition Evidence
├── Positions
│   ├── Investor
│   ├── Folio
│   ├── ISIN
│   ├── Units
│   └── valuation observation
│       ├── NAV
│       ├── observation date
│       └── Market Value
├── Transactions
│   └── relevant historical transaction evidence
├── Position → Purpose attribution
└── transition-relevant Fund metadata
```

Transactions themselves are the acquisition evidence. LTS may derive acquisition lots, holding periods, and FIFO consequences from historical Transactions rather than requiring an invented second acquisition object.

Transition-relevant Fund metadata is consumer-driven. LTS may need mechanically relevant attributes such as asset/category characteristics, lock-in characteristics, or other evidence-backed transition constraints. It does not consume behavioural Fund Fingerprints.

Broader Fund metadata is deliberately subject to dependency review after LTS is implemented.

---

# 4. LFS — Lakshya Formation System

## 4.1 Native question

> **What investment formation should we have?**

LFS owns the complete formation engine:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL → TARGET
```

These are stages inside LFS, not separate bounded systems.

## 4.2 FUND

> **What kind of teammate is this fund?**

FUND establishes observed individual-fund behavioural evidence from NAV history. Elevation and Protection are behavioural evidence families, not forecasts.

The Fund Fingerprint is an LFS analytical intermediate. It is not an LPS fact and is not a cross-system contract.

The Fund-level weak-Pareto pruning gate between FUND and TEAM also belongs entirely inside LFS:

```text
LFS
  FUND
    ↓ Fund Fingerprint
  FUND → TEAM gate
    ↓ surviving Funds
  TEAM
```

LPS never needs to know the Fingerprint. LTS never needs to know it.

## 4.3 TEAM

> **What kind of collective do these teammates form?**

TEAM forms deterministic singleton, pair, and trio candidates, maximum size 3. Collective evidence is formed from constituent Fund histories rather than by averaging Fund scores first.

The declared comparator surface is:

```text
28 Elevation + 12 Protection = 40 dimensions
```

TEAM uses exact weak Pareto non-dominance:

```text
Elevation  → UP
Protection → DOWN
```

TEAM is elimination, not ranking. It does not import MISSION semantics merely to reduce its universe.

## 4.4 COMPOSITION

> **Where does capital sit within a collective?**

A Composition is **Team + complete weights**.

Canonical positive-weight grid:

```text
singleton: 100%
pair:       19 allocations at 5% increments
trio:      171 allocations at 5% increments
```

Composition fingerprints are durable reusable evidence containing identity, weights and behavioural evidence including NAV, Elevation and Protection. Expensive evidence is persisted immediately and consumed downstream rather than silently recomputed.

The Completion Index is a deliberately narrow Composition checkpoint mechanism, not a generic artifact store.

## 4.5 MISSION

> **Can this Composition serve this Purpose?**

MISSION is the first stage where Purpose semantics enter the analytical contract.

Supported analytical horizons are:

```text
3Y / 5Y / 7Y / 10Y
```

For a finite Purpose horizon, the longest supported analytical horizon not exceeding that horizon is selected. Examples:

```text
4Y → 3Y    6Y → 5Y    8Y → 7Y
9Y → 7Y   12Y → 10Y  13Y → 10Y
```

For an open Purpose, the analytical horizon is locked to 7Y. It is not a separate Purpose input.

The logical sequence is:

```text
Global Composition frontier
        ↓
Achievability, when a finite target exists
        ↓
Protection-only frontier
        ↓
MISSION survivors
        ↓
Trajectory observation
```

Trajectory is descriptive and does not eliminate a MISSION survivor. Insufficient trajectory history is an explicit insufficient-evidence result, not a silent rejection.

## 4.6 FINAL

> **Among already-qualified MISSION Compositions, which is the strongest practical compromise?**

FINAL is production ordering, not another admission stage.

For selected horizon H:

```text
7 Elevation(H) + 12 native Protection
```

Zero-variance spokes are removed deterministically. Retained spokes are equally weighted and converted to population-relative desirability coordinates in `[0,1]`, with higher always better. The Utopia Point is the best observed value on each retained spoke.

```text
d(i,j) = 1 - x(i,j)
L2(i) = sqrt(sum(d(i,j)^2))
```

The smallest unweighted L2 distance is the production winner. L-infinity remains a worst-spoke diagnostic and participates in a joint `(L2, L∞)` frontier; there is no arbitrary L-infinity kill threshold.

FINAL records:

- Lp winner sweep from 1.00 to 10.00 in 0.25 increments;
- leave-one-spoke sensitivity; and
- 5,000 deterministic population bootstrap resamples by default.

Robustness evidence describes stability; it does not override the primary winner.

The production contract is versioned. Changes to the decision rule, spoke surface, percentile semantics, primary norm, weighting, L-infinity treatment, bootstrap semantics, p sweep, tie-breaking, or winner meaning require deliberate release/version changes with tests and documentation.

## 4.7 TARGET

TARGET is not a new optimization stage. It is the fund-level formation implied by reviewed Purpose state and selected FINAL Composition decisions:

```text
authoritative Purpose state
        ↓
selected FINAL Composition per Purpose
        ↓
Composition fund weights
        ↓
fund-level TARGET architecture
```

The LFS → LTS Formation Intent contract preserves the Purpose-level mapping even when multiple Purposes select the same Composition:

```text
Purpose A → Composition A
Purpose B → Composition A
Purpose C → Composition A
Purpose D → Composition A
Purpose E → Composition A
Purpose F → Composition B
```

LFS does not assign Investor, Folio, Position identity, tax treatment, or transition actions.

---

# 5. LTS — Lakshya Transition System

## 5.1 Native question

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

LTS is not another portfolio optimizer.

## 5.2 Formation Intent — LFS → LTS

The LFS output is intentionally semantic:

```text
Purpose → Composition
```

It preserves Purpose identity even when multiple Purposes select the same Composition.

It does **not** contain Position IDs, Investor/Folio assignments, tax treatment, or transaction instructions.

## 5.3 Transition Proposal — LTS → Human / Staging

LTS produces:

> **a proposed transformation of Positions and Purpose-attributions.**

More fully:

> **LTS produces a proposed transformation of Positions and Purpose-attributions, suitable for human review, execution, and subsequent promotion into the LPS mapping after the resulting Positions are observed.**

One or more candidate simulations may coexist. A proposal is non-authoritative and must not mutate LPS factual Positions or accepted attribution.

A proposed Position can temporarily use:

```text
Investor + existing Folio + ISIN
```

or:

```text
Investor + NEW-FOLIO-001 + ISIN
```

where `NEW-FOLIO-001` is a simulation-local placeholder and never a real-world folio identity. A proposal-local Position ID may also distinguish separate intended allocations before a real folio exists.

The design does not introduce a generic `Action` abstraction merely for implementation convenience. A new domain concept must earn its existence through demonstrated need.

## 5.4 Transition constraints

Where genuinely evidenced by source material, LTS may reason about:

- ELSS lock-in;
- acquisition-date tax consequences;
- STCG/LTCG implications;
- exit loads;
- transaction costs;
- liquidity;
- minimum transaction constraints;
- SIP/STP/SWP sequencing; and
- retain/exit/stage/switch/redeem/invest alternatives.

Transactions already retained by LPS are the evidence from which acquisition chronology may be derived. If a source gap prevents a conclusion, the fact remains unknown.

## 5.5 Human execution boundary

LTS proposes. The human executes.

LTS must not:

- reopen FUND admission;
- redefine TEAM formation;
- alter Composition weights because of existing holdings;
- rerun MISSION merely because transition is inconvenient;
- replace a FINAL winner with a newly optimized fund;
- encode hidden Purpose priorities;
- invent tax/cost/transaction facts; or
- execute transactions automatically.

---

# 6. Reconciliation and Promotion

After a selected LTS proposal is effected by the human, new authoritative source evidence is imported into LPS.

LPS reconstructs the resulting factual Positions from that evidence.

The reconciliation workflow then:

1. detects factual changes and candidate matches to the staged proposal;
2. identifies newly observed Positions, including real folios corresponding to proposal-local NEW markers;
3. presents proposed Purpose attribution to the reviewer; and
4. records the reviewer's accepted Purpose attribution in LPS.

The governing rule is:

> **LTS proposes. External evidence establishes Positions. Human acceptance establishes Purpose attribution. LPS records the resulting factual state.**

This asymmetry is intentional:

```text
Position proposal
    ↓
human execution
    ↓
external evidence
    ↓
LPS establishes resulting Position
```

and:

```text
Purpose-attribution proposal
    ↓
human acceptance
    ↓
promotion
    ↓
LPS accepted Purpose attribution
```

Promotion does not manufacture a Position. It reconciles a proposal against subsequently observed evidence.

---

# 7. Post-FINAL family review layers

These layers sit after FINAL and before the deliberate annual persistence boundary. They are not optimization stages.

```text
FINAL
  ↓
FAMILY ARCHITECTURE VALIDATION
  ↓
PURPOSE STAGING
  ↓
HISTORICAL SNAPSHOT
```

## 7.1 Family Architecture Validation

Native question:

> **Given the independent Purpose-level decisions together, where does family capital depend on common Funds or investment organizations?**

This is attribution, not optimization.

Core contract:

```text
Purpose capital
        ×
FINAL Composition fund weight
        =
Attributed capital
```

Structured annual outputs:

```text
family_capital_attribution.csv
family_fund_concentration.csv
family_amc_concentration.csv
family_purpose_dependency.csv
family_attribution_manifest.json
```

It does not impose concentration limits, penalize common dependencies, alter FINAL winners, create substitute Compositions, optimize family allocation, declare dependencies safe/unsafe, or introduce transition-cost assumptions.

Integrity is fail-closed for malformed Purpose capital, duplicate/missing Fund metadata, malformed/non-100% Composition weights, unknown Fund ISINs, manifest/hash mismatches, and attribution non-reconciliation.

## 7.2 Purpose Staging

Purpose Staging is a deliberately small human-in-the-loop reconciliation workspace. It does not alter FUND, TEAM, COMPOSITION, MISSION, FINAL, or selected FINAL Composition.

The human controls the meaningful Purpose inputs. A finite `due` derives its analytical horizon; an open due uses the fixed 7Y analytical horizon. `analytical_horizon_years` is therefore not a human Purpose field.

The accounting contract is:

```text
Purpose reduction → common pool
pool acquisition  → another Purpose
```

Acquisition percentages use the same pool base at the start of the acquisition phase for that turn; they are not applied sequentially to a shrinking pool.

The reviewer cannot silently create capital or SIP by increasing a capital value or monthly plan. Changes to desired or due change analytical requirements; they do not manufacture cash release.

The authoritative `data/purpose/purposes.csv` remains unchanged until explicit COMMIT. COMMIT requires reviewer satisfaction and both pools equal to zero; the authoritative file is backed up before promotion.

## 7.3 Historical Snapshot

Historical Snapshot is a human-controlled Git persistence boundary. It is memory, not a transaction ledger.

The durable record includes appropriate reviewed material under:

```text
data/fund/
data/purpose/
data/reviews/<as-of>/
```

Generated runtime output and forensic logs remain disposable/Git-ignored where configured.

---

# 8. Shared event vocabulary

Lakshya uses a shared factual event vocabulary across observation and transition planning. LPS records events that actually appear in authoritative evidence; LTS may reason about planned events until they become observed evidence.

```text
Purchase
Systematic Investment
Redemption
Switch In
Switch Out
Systematic Investment Rejection
STP-related
SWP-related
Stamp Duty
STT Paid
```

This gives observation and planning a common language without requiring LPS to know future events or LTS to own source parsing.

---

# 9. Production invariants

1. **LPS observes. LFS forms. LTS transitions.**
2. Observed is not inferred.
3. Unknown is not zero.
4. A Purpose horizon is not a demand for equivalent lived Fund history.
5. A calculation does not automatically become a downstream input.
6. Persisted evidence is reused rather than silently recomputed.
7. A higher stage consumes only information whose semantic need it has earned.
8. Experimental exploration may discover a rule; production codifies the rule explicitly.
9. A production rule changes only through deliberate versioned release.
10. Rich evidence may be compressed for a higher-order boundary, but compression must not erase meaning.
11. A later-stage failure does not invalidate valid upstream evidence.
12. Family-level observation does not retroactively change an upstream winner.
13. Human Purpose priority is expressed through review inputs, not hidden system ranking.
14. Historical persistence records reviewed state; it is not an automatic transaction ledger.
15. Economic state is source-derived and must never be inferred from analytical outputs.
16. Transition planning must not become a second portfolio optimizer.
17. A proposed Position is not an established Position.
18. A proposal-local NEW folio marker is never a factual folio.
19. External evidence establishes Position facts.
20. Human acceptance establishes Purpose attribution.
21. Fund Fingerprints belong entirely inside LFS.
22. Domain concepts are not invented for implementation convenience.

Preferred lifecycle:

```text
compute → persist → validate → consume
```

---

# 10. What the architecture deliberately rejects

Without an earned domain need, Lakshya does not introduce:

- Portfolio as a separate dimension;
- a wrapper around Positions representing a second state model;
- a second Transaction concept;
- Fund Fingerprints outside LFS;
- automatic Purpose inference or trimming;
- hidden Purpose priority rankings;
- transition-time re-optimization of formation;
- fabricated folio identities;
- invented tax/cost facts;
- automatic transaction execution; or
- a generic Action abstraction merely because transition code needs verbs.

This is deliberate conservatism, not missing functionality.

---

# 11. Parking / deliberately deferred questions

The architecture deliberately parks the following until evidence earns them:

- formal LPS contract versioning beyond the current release discipline;
- Fund metadata minimization after LTS dependency archaeology;
- benchmark evidence as an analytical lens;
- legacy Fund evidence/ratio/downside machinery not yet proven necessary;
- broader Fund scheme attributes in LPS;
- NAV source/evidence evolution beyond the established architecture;
- unusual transaction/identity edge cases;
- richer Purpose mapping;
- Purpose residual/over-target automation;
- unmapped-Position automation;
- a formal Z-trigger framework for rare exceptions;
- broader LPS reference-data expansion; and
- Purpose-specific external views until a consumer earns one.

Parking means deliberately refusing to make architecture pay for a need before evidence demonstrates it.

---

# 12. Engineering consequence

The contracts are the primary architectural fulcrum.

When a new requirement appears, the first question is:

> **Which bounded context genuinely owns this knowledge, and which contract earns the need for it?**

The second question is:

> **Is this a fact, an analytical intermediate, an intent, a proposal, or an accepted promoted fact?**

Implementation must express the domain model rather than silently redefine it.

The complete domain map, contract definitions, ubiquitous language, and invariants are maintained in `docs/Lakshya_Domain_Model.md`.
