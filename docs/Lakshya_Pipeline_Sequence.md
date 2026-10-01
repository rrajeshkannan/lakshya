# Lakshya Production Pipeline Sequence

**Status:** Production execution map

**Release:** FINAL / Compromise Programming v1

**As of:** 2026-09-14

This document describes **how the Lakshya review executes**. `docs/Lakshya_Architecture.md` defines the wider production architecture; `docs/Lakshya_Domain_Model.md` defines the bounded contexts and five cross-context contracts; `docs/Lakshya_HowTo.md` defines practical reviewer operation.

---

# 1. Three-system execution map

Lakshya has three bounded systems with separate execution responsibilities:

```text
                         HUMAN
                           │
                           ▼
                          LPS
                   source evidence
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
               LFS                   LTS
        formation engine       transition engine
                │                     ▲
                └─────────────────────┘
```

The annual review does **not** form factual Positions by running the formation engine, and transition analysis does not replace formation selection.

The principal contracts are:

```text
LPS → LFS   Formation Evidence
LPS → LTS   Transition Evidence
LFS → LTS   Formation Intent
LTS → Human Transition Proposal
Human + new source evidence → LPS Reconciliation / Promotion
```

This is not a forced serial `LPS → LFS → LTS` pipeline. LPS feeds both downstream consumers; LFS additionally feeds LTS.

---

# 2. End-to-end annual review

```mermaid
flowchart TD
    A[Authoritative source evidence] --> B["LPS: Transactions"]
    B --> C["LPS: Positions"]
    C --> D["LPS: valuation observation"]
    D --> E["Economic CURRENT / factual views"]

    E --> F[Formation Evidence]
    F --> G["LFS-Main: FUND"]
    G --> H["FUND-level weak-Pareto gate"]
    H --> I["LFS-Main: TEAM"]
    I --> J["LFS-Main: COMPOSITION"]
    J --> K["LFS-Main: MISSION"]
    K --> L["LFS-Main: FINAL"]

    L --> M[Purpose Staging INIT]
    M --> N[Human staging turns]
    N --> O["Achievability + reconciliation"]
    O --> P{"Satisfied and pools zero?"}
    P -->|No| N
    P -->|Yes| Q[Purpose Staging COMMIT]
    Q --> R[Human annual snapshot review]
    R --> S[Historical Snapshot]
    S --> T["TARGET from committed Purpose + FINAL"]

    C --> U[Transition Evidence]
    S --> V[Reviewed annual state]
    T --> W[Formation Intent]
    U --> X[LTS transition analysis]
    V --> X
    W --> X
    X --> Y[Transition Proposal]
    Y --> Z[Human execution]
    Z --> AA[New authoritative source evidence]
    AA --> A
```

The durable annual review therefore has three distinct concerns:

```text
LPS → factual investment evidence → Economic CURRENT

LFS-Main → FUND → TEAM → COMPOSITION → MISSION → FINAL

Purpose Staging → reviewed Purpose state

Historical Snapshot → durable annual memory

TARGET → committed Purpose state + selected FINAL decisions

LTS → transition analysis using LPS facts + LFS intent
```

Purpose Staging is a human reconciliation boundary, not an additional optimizer. TARGET is derived after the reviewed Purpose state is committed; it is not produced by LFS-Main before staging.

---

# 3. Human-controlled boundaries

```mermaid
sequenceDiagram
    participant Reviewer as Family reviewer
    participant LPS as LPS
    participant LFS as "LFS-Main"
    participant Stage as Purpose staging
    participant Git as Historical repository
    participant Target as TARGET
    participant LTS as LTS

    Reviewer->>LPS: provide authoritative source evidence
    LPS-->>Reviewer: validated Transactions / Positions / factual views
    Reviewer->>LFS: review formation scope + Purpose inputs
    LFS-->>Reviewer: FINAL evidence
    Reviewer->>Stage: INIT
    loop one or more review turns
        Reviewer->>Stage: release / acquire permitted Purpose levers
        Stage-->>Reviewer: staged state + ledger + Achievability
    end
    Reviewer->>Stage: COMMIT when satisfied and pools = 0
    Stage-->>Reviewer: authoritative Purpose state promoted
    Reviewer->>Git: inspect and commit annual snapshot
    Git-->>Target: committed annual state
    Target-->>Reviewer: fund-level TARGET formation
    Reviewer->>LTS: begin separate CURRENT → TARGET analysis
    LTS-->>Reviewer: one or more transition simulations
    Reviewer->>Reviewer: select / execute externally
```

Governing principle:

> **The reviewer controls the terrain; Lakshya calculates the consequences.**

---

# 4. LPS execution — source to Positions

## 4.1 Source boundary

LPS starts with authoritative source evidence. For mutual funds, the family's authoritative account statement / CAS is the evidence boundary for transactions and holdings/history.

Family policy:

- request the statement comfortably before the earliest family mutual-fund investment;
- include all folios, including zero-balance folios;
- retain the original unmodified source PDFs;
- enter passwords interactively and never store them;
- treat warnings or ambiguity as stop-and-ask-human conditions;
- perform full-history import for each annual review; and
- review validation before accepting the resulting factual state.

The parser/library is an implementation boundary, not the LPS domain model. Parser-specific schemas must not leak into LFS or LTS.

## 4.2 Transactions

Validated source events become LPS `Transaction` records. A Transaction is factual at the LPS boundary; there is no second derived Transaction concept.

The family-wide transaction collection is:

```text
data/lps/transactions.csv
```

Each record retains investor identity. Re-importing one investor's full-history source replaces that investor's records while retaining other investors' records, making annual full-history import idempotent.

Shared event vocabulary includes:

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

LPS records what actually appears in evidence. LTS may later reason about planned events; the vocabulary remains shared.

## 4.3 Positions

Positions are reconstructed from Transactions and stored family-wide:

```text
data/lps/positions.csv
```

Established Position identity is:

```text
Investor + Folio + ISIN + Slice
```

The physical holding is `Investor + Folio + ISIN`. The slice is the virtual Purpose-bearing portion. The opening book is `slice-1`. A Position is first-class and contains factual unit state. Valuation is applied as an observation rather than turning valuation into a separate state entity.

One accepted Position maps to exactly one Purpose. A Purpose may have zero, one, or many Positions.

## 4.4 Valuation

LPS applies an applicable NAV observation to the Position collection to derive valuation.

Two dates remain distinct:

```text
transaction_through_date
valuation_as_of_date
```

NAV evidence is sparse: only actual recorded observations are written. NAV reads are as-of reads:

```text
NAV as of X
= latest recorded NAV observation on or before X
```

No holiday observations are invented and no interpolation is performed.

LPS derives Purpose capital from Position valuation and accepted Position → Purpose attribution.

---

# 5. Formation Evidence — LPS → LFS

LPS exposes a purpose-built formation projection rather than a giant LPS object:

```text
Formation Evidence
├── funds
│   └── Fund identity required by formation
└── nav_histories
    └── ISIN → normalized NAV history
```

The formation fund universe has two sources:

```text
1. Funds represented by LPS Positions
2. Human-selected potential_funds_in_scope
```

The second source covers funds not represented by existing Positions. The reviewer is responsible for bringing only admissible candidates into `potential_funds_in_scope`; LFS does not contain a separate admissibility gate.

The legacy `data/lps/funds_in_scope.csv` mechanism is an implementation artifact to be replaced as this contract is implemented. NAV acquisition should ultimately derive ISINs from Positions plus reviewer-selected potential funds.

Formation Evidence contains no Position attribution, transaction history, transition information, or Fund Fingerprints.

---

# 6. LFS-Main analytical production sequence

```mermaid
flowchart TD
    A[Formation Evidence] --> B[FUND]
    B --> C[Fund Fingerprint]
    C --> D[Fund-level weak-Pareto gate]
    D --> E[Surviving Funds]
    E --> F[TEAM candidate generation]
    F --> G[Collective Timeline]
    G --> H[TEAM fingerprint]
    H --> I[TEAM 40-D weak Pareto frontier]
    I --> J["COMPOSITION 5% weight grid"]
    J --> K[Composition fingerprints]
    K --> L[Global Composition frontier]
    L --> M[MISSION Purpose qualification]
    M --> N[Achievability when applicable]
    N --> O[Protection-only frontier]
    O --> P[MISSION survivors]
    P --> Q[Trajectory observation]
    Q --> R[FINAL Purpose surface]
    R --> S[Percentile coordinates]
    S --> T["Utopia / L2 ordering"]
    T --> U[Robustness bundle]
    U --> V["FINAL evidence for staging / TARGET"]
```

No stage may use a later stage merely to make its own universe smaller.

---

# 7. FUND execution

```mermaid
sequenceDiagram
    participant Evidence as Formation Evidence
    participant Fund as FUND
    participant Fingerprint as Fund Fingerprint
    participant Gate as Fund-level Pareto gate
    participant Team as TEAM

    Evidence->>Fund: Fund identity + NAV history
    Fund->>Fingerprint: construct behavioural fingerprint
    Fingerprint->>Gate: Fund-stage behavioural dimensions
    Gate-->>Team: surviving Fund universe
```

Fund Fingerprint is an LFS analytical intermediate. It never crosses a bounded-context contract.

The Fund-level weak-Pareto gate is a pruning boundary between FUND and TEAM. It is elimination, not ranking.

The 8-year lived-history rule applies to POTENTIAL/new-entry Funds. Existing family Funds may be younger and remain valid. These are admission concepts, not hidden downstream quality preferences.

Regular versus Direct is not a Lakshya analytical distinction.

Scheme Name and AMC remain useful factual identity/reference fields. Generic category/benchmark fields are not promoted unless a downstream contract genuinely consumes them.

---

# 8. TEAM execution

```mermaid
sequenceDiagram
    participant Funds as Surviving Funds
    participant TeamGen as Candidate generator
    participant Timeline as Collective Timeline
    participant Fingerprint as TEAM fingerprint
    participant Frontier as TEAM frontier
    participant Composition as COMPOSITION

    Funds->>TeamGen: surviving universe
    TeamGen->>TeamGen: singleton / pair / trio
    TeamGen->>Timeline: constituent histories
    TeamGen->>Fingerprint: candidate identity
    Timeline->>Timeline: common historical period + actual observations
    Timeline->>Timeline: latest NAV on/before each observation
    Timeline->>Fingerprint: collective NAV / evidence
    Fingerprint->>Frontier: 28 Elevation + 12 Protection
    Frontier-->>Composition: non-dominated Teams
```

TEAM forms deterministic singleton, pair, and trio candidates, maximum size 3.

The declared comparator surface is:

```text
28 Elevation + 12 Protection = 40 dimensions
```

Weak Pareto non-dominance is:

```text
Elevation  → UP
Protection → DOWN
```

TEAM is elimination, not ranking.

Collective Timeline uses common actual observation dates and applicable recorded NAV observations. It does not manufacture calendar days or interpolate. A singleton reproduces its Fund trajectory.

---

# 9. COMPOSITION execution and checkpointing

```mermaid
sequenceDiagram
    participant TEAM as TEAM frontier
    participant Grid as Weight grid
    participant Store as Fingerprint store
    participant Index as Completion Index
    participant Global as Global frontier
    participant Mission as MISSION

    TEAM->>Grid: non-dominated Teams
    Grid->>Grid: complete positive weights
    Grid->>Index: checkpoint lookup
    alt valid checkpoint index entry
        Index->>Store: locate persisted fingerprint
        Store-->>Global: reuse evidence
    else missing / stale
        Grid->>Store: compute Composition evidence
        Store->>Store: atomic persist + fsync
        Store-->>Index: record completion
        Store-->>Global: persisted evidence
    end
    Global->>Global: exact 40-D weak Pareto frontier
    Global-->>Mission: survivor identities
```

Canonical positive-weight grid:

```text
singleton: 100%
pair:       19 allocations at 5% increments
trio:      171 allocations at 5% increments
```

A Composition is **Team + complete weights**.

Composition fingerprints are durable reusable evidence containing identity, weights and behavioural evidence including NAV, Elevation and Protection.

The Completion Index is a **narrow Composition checkpoint mechanism**, not a generic artifact store.

A downstream algorithm change alone does not justify rebuilding valid Composition evidence.

The general persistence rule is:

```text
compute → persist → validate → consume
```

A downstream failure must not invalidate upstream evidence that remains valid.

---

# 10. MISSION execution

```mermaid
sequenceDiagram
    participant Global as Global Composition frontier
    participant Purpose as Purpose input
    participant Mission as MISSION
    participant Ach as Achievability
    participant Protection as Protection frontier
    participant Trajectory as Trajectory
    participant Final as FINAL

    Global->>Mission: persisted survivor identities
    Purpose->>Mission: derived horizon + target
    alt finite target
        Mission->>Ach: calculate Achievability
        Ach-->>Mission: qualification evidence
    else open Purpose
        Mission->>Mission: skip Achievability
    end
    Mission->>Protection: Purpose-qualified set
    Protection->>Mission: Protection-only non-dominated set
    Mission->>Trajectory: MISSION survivors
    Purpose->>Trajectory: requested horizon
    Trajectory->>Trajectory: select supported actual observation horizon
    Trajectory-->>Final: descriptive trajectory evidence
```

Supported analytical horizons are:

```text
3Y / 5Y / 7Y / 10Y
```

For a finite Purpose due, derive the Purpose horizon and select the longest supported analytical horizon not exceeding it. Examples:

```text
4Y → 3Y    6Y → 5Y    8Y → 7Y
9Y → 7Y   12Y → 10Y  13Y → 10Y
```

For an open Purpose, the analytical horizon is fixed at 7Y. It is not a separate Purpose input.

History availability is evaluated per Composition. Insufficient trajectory history produces an explicit insufficient-evidence result rather than silently eliminating a MISSION survivor. Trajectory is descriptive and does not eliminate a MISSION survivor.

---

# 11. FINAL execution

FINAL receives only MISSION survivors and does not reopen MISSION eligibility.

```mermaid
sequenceDiagram
    participant Mission as MISSION survivors
    participant Evidence as Persisted evidence
    participant Surface as FINAL surface
    participant Norm as Compromise ordering
    participant Robust as Robustness suite
    participant Output as FINAL bundle

    Mission->>Surface: Purpose survivor identities
    Evidence->>Surface: selected-horizon Elevation + native Protection
    Surface->>Surface: remove zero-variance spokes only
    Surface->>Norm: percentile coordinates + Utopia
    Norm->>Norm: primary L2 ordering
    Norm->>Robust: L-infinity diagnostic / joint frontier
    Norm->>Robust: Lp sweep
    Norm->>Robust: leave-one-spoke sensitivity
    Norm->>Robust: 5,000 deterministic bootstrap
    Norm->>Output: winner + ordering evidence
    Robust->>Output: robustness evidence
```

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

FINAL also records:

- Lp winner sweep from 1.00 to 10.00 in 0.25 increments;
- leave-one-spoke sensitivity; and
- 5,000 deterministic population bootstrap resamples by default.

Robustness evidence describes stability; it does not override the primary winner.

---

# 12. Purpose Staging execution

```mermaid
sequenceDiagram
    participant Source as "data/lfs/purpose.csv"
    participant Reviewer as reviewer
    participant Stage as staging workspace
    participant Ledger as reconciliation ledger
    participant Ach as Achievability
    participant Commit as commit boundary

    Reviewer->>Stage: INIT
    Stage->>Source: read authoritative state
    Source-->>Stage: isolated staged copy
    loop one or more review turns
        Reviewer->>Stage: permitted Purpose lever changes
        Stage->>Stage: release reductions into pools
        Reviewer->>Stage: acquisition percentages
        Stage->>Stage: allocate from turn-start pool base
        Stage->>Ledger: record releases / acquisitions
        Stage->>Ach: recalculate consequences
        Ach-->>Reviewer: latest Achievability
    end
    Reviewer->>Commit: COMMIT
    Commit->>Commit: require reviewer satisfaction + both pools zero
    Commit->>Commit: backup purposes_before_commit.csv
    Commit->>Source: promote staged state
    Source-->>Reviewer: authoritative Purpose state updated
```

Purpose Staging is a separate execution stage from LFS-Main production. It does not alter FUND, TEAM, COMPOSITION, MISSION, FINAL, or selected FINAL Composition.

The permitted staging levers are:

```text
value
monthly_plan
capital_acquire_pct
sip_acquire_pct
```

`desired` and `due` remain fixed context. `analytical_horizon_years` is derived and is not a human Purpose field.

The accounting contract is:

```text
Purpose reduction → common pool
pool acquisition  → another Purpose
```

Acquisition percentages use the same pool base at the start of the acquisition phase for that turn; they are not applied sequentially to a shrinking pool.

The reviewer cannot silently create capital or SIP by increasing a capital value or monthly plan. Changes to desired or due are upstream Purpose-input changes, not staging levers.

The authoritative `data/lfs/purpose.csv` remains unchanged until explicit COMMIT. COMMIT requires reviewer satisfaction and both pools equal to zero; the authoritative file is backed up before promotion.

---

# 13. Historical Snapshot execution

```mermaid
sequenceDiagram
    participant Reviewer as Human reviewer
    participant Data as "data/"
    participant Git as Git repository

    Reviewer->>Data: inspect intended annual changes
    Reviewer->>Data: confirm authoritative + structured review state
    Reviewer->>Git: selectively stage intended data/
    Reviewer->>Git: commit annual snapshot
    Git-->>Reviewer: durable historical state
```

Historical Snapshot is a human-controlled Git persistence boundary. There is no separate automatic snapshotter.

The durable record includes appropriate reviewed material under:

```text
data/lps/
data/lfs/
data/lts/
data/nav/
```

Runtime output and forensic logs remain disposable where configured.

Historical Snapshot is memory. It is not a transaction ledger and does not establish Position facts independently of LPS source evidence.

---

# 14. CURRENT → TARGET execution

The authoritative annual sequence is:

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

CURRENT and TARGET are deliberately different states:

```text
ANALYTICAL CURRENT
= what the reviewed Lakshya architecture says

ECONOMIC CURRENT
= what the family actually owns at the chosen observation date

TARGET
= what the committed Purpose state + selected FINAL decisions imply should be owned
```

Economic CURRENT is source-derived by LPS. TARGET is derived from the committed Purpose state and selected FINAL Composition decisions. Neither is inferred from the other.

TARGET is not another optimization stage:

```text
committed Purpose state
        ↓
selected FINAL Composition per Purpose
        ↓
Composition fund weights
        ↓
fund-level TARGET architecture
```

Formation Intent then preserves the Purpose-level mapping for LTS:

```text
Purpose → Composition
```

---

# 15. Transition Evidence — LPS → LTS

LTS receives a purpose-built Transition Evidence projection:

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

Transactions themselves are the available historical acquisition/event evidence. LTS may derive acquisition lots, holding periods, and FIFO consequences from them; no second acquisition-evidence object is introduced without demonstrated need.

LTS consumes Fund metadata only insofar as it affects transition mechanics. It does not consume behavioural Fund Fingerprints, TEAM, COMPOSITION, MISSION, or FINAL as analytical objects.

---

# 16. LTS transition sequence

This sequence begins after the reviewed annual persistence boundary. It is not part of the LFS analytical optimizer.

```mermaid
sequenceDiagram
    participant LPS as LPS
    participant Intent as LFS Formation Intent
    participant Compare as LTS comparison
    participant Sim as LTS simulation
    participant Human as "Human reviewer / executor"

    LPS->>Compare: factual Positions + history + attribution
    Intent->>Compare: Purpose → Composition mappings
    Compare->>Compare: match / retain / change
    Compare->>Compare: apply evidenced transition constraints
    Compare->>Sim: candidate transition simulation
    Sim-->>Human: proposed Position + attribution transformations
    Human->>Human: review / select / execute externally
```

The native LTS reasoning is:

```text
factual Positions
      +
Formation Intent
      ↓
what matches?
what can remain?
what differs?
what must change?
what constraints apply?
what sequence is feasible?
      ↓
Transition Proposal
```

The physical holding remains:

```text
Investor + Folio + ISIN
```

LPS stores the virtual slice on that holding:

```text
Investor + Folio + ISIN + Slice
```

The slice keeps one physical folio from being treated as a new Position when it serves more than one Purpose. The opening book is `slice-1`. `bridge_positions` reads that book into the cascade. `build_owned_positions` refuses to invent percentages.

Run LTS only after LPS and LFS have used the same as-of date. The runner reads that date from `data/lfs/purpose_summaries.csv` and refuses a different `--as-of`.

```bash
python -m lts.runner --as-of YYYY-MM-DD
```

The economic plan uses the market values stored on `data/lps/positions.csv`. Availability reprices the same units from `data/nav/` as of that date. Those two prices agree only when the CAS import valued the positions at the same as-of.

Investor matters because different investors can have different tax consequences. Folio matters because the same ISIN may appear in different folios and Purpose relationships.

A proposed Position that requires a new folio may use a simulation-local placeholder:

```text
Investor + NEW-FOLIO-001 + ISIN
```

The placeholder is not a fabricated real-world folio. A proposal-local Position ID may distinguish multiple intended allocations before actual folio creation.

LTS does not introduce a generic `Action` abstraction merely because transition logic contains verbs. The concept must earn its existence.

---

# 17. Transition constraints and source archaeology

LTS may use only constraints the source evidence supports.

The account statement must establish what is genuinely available for:

- holding identity;
- units and value;
- observation date;
- account/folio representation;
- acquisition/transaction information;
- cost information and granularity;
- source-authoritative versus presentation fields; and
- facts the source does not provide.

Missing facts remain missing. Lakshya must not manufacture cost basis, acquisition dates, tax lots, exit costs, account semantics, or transaction constraints.

Where genuinely evidenced, LTS may eventually reason about:

- ELSS lock-in;
- acquisition-date tax consequences;
- STCG/LTCG implications;
- exit loads;
- transaction costs;
- liquidity;
- minimum transaction constraints;
- SIP/STP/SWP sequencing; and
- retain/exit/stage/switch/redeem/invest alternatives.

The source must earn each constraint.

---

# 18. Transition Proposal and reconciliation / promotion

LTS produces:

> **a proposed transformation of Positions and Purpose-attributions.**

The proposal is non-authoritative. Multiple simulations may coexist. No simulation mutates factual LPS state.

After a selected proposal is effected by the human:

```mermaid
flowchart TD
    A[LTS selected proposal] --> B[Human effects transition]
    B --> C[New authoritative source evidence]
    C --> D[LPS import]
    D --> E[LPS reconstructs factual Positions]
    E --> F[Automatic reconciliation]
    F --> G[Reviewer reviews proposed Purpose attribution]
    G --> H[LPS records accepted attribution]
```

The reconciliation workflow:

1. detects factual changes and candidate matches to the staged proposal;
2. identifies newly observed Positions, including real folios corresponding to proposal-local NEW markers;
3. presents proposed Purpose attribution to the reviewer; and
4. records accepted attribution in LPS.

The governing rule is:

> **LTS proposes. External evidence establishes Positions. Human acceptance establishes Purpose attribution. LPS records the resulting factual state.**

This is intentionally asymmetric:

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

# 19. Persistence and resume semantics

The general persisted-evidence lifecycle is:

```mermaid
flowchart LR
    A["Load source / checkpoint"] --> B[Validate]
    B --> C{"Valid checkpoint?"}
    C -->|Yes| D[Reuse]
    C -->|No| E["Compute missing / stale evidence"]
    E --> F[Atomic persist]
    F --> G[Validate persisted evidence]
    D --> G
    G --> H[Consume downstream]
```

The invariant is:

> **A downstream failure must not invalidate upstream evidence that remains valid.**

Composition uses its narrow Completion Index to avoid unnecessary filesystem/JSON validation when indexed checkpoint metadata remains valid. This does not turn the index into a generic artifact store.

---

# 20. Human control and failure boundaries

```mermaid
flowchart TD
    Human[Human]
    Human --> H1["provides / reviews source evidence"]
    Human --> H2["defines / reviews Purpose"]
    Human --> H3[reviews formation scope and results]
    Human --> H4[accepts Purpose attribution]
    Human --> H5[effects transactions externally]

    LPS[LPS]
    LPS --> L1[establishes factual investment state from evidence]

    LFS[LFS]
    LFS --> F1[forms investment architecture]

    LTS[LTS]
    LTS --> T1[stages constrained transition proposals]
```

Fail-closed boundaries apply where factual or analytical integrity is required. Ambiguous source evidence stops the factual pipeline for human review rather than silently guessing.

Formation and transition are not allowed to compensate for missing facts by inventing them.

---

# 21. Pipeline invariants

1. **LPS observes. LFS forms. LTS transitions.**
2. Observed is not inferred.
3. Unknown is not zero.
4. One established Position maps to exactly one Purpose.
5. One Purpose may have zero, one, or many Positions.
6. A Purpose may exist before any Position is assigned to it.
7. Fund Fingerprints belong entirely inside LFS.
8. The Fund-level weak-Pareto gate belongs between FUND and TEAM inside LFS.
9. TARGET is derived only from committed Purpose state + selected FINAL decisions.
10. LTS never chooses TARGET formation.
11. LTS never mutates factual LPS Positions during simulation.
12. A proposal-local NEW folio marker is never a factual folio identity.
13. External source evidence establishes Position facts.
14. Human acceptance establishes Purpose attribution.
15. LTS proposals are non-authoritative.
16. A downstream convenience must not silently alter an upstream contract.
17. A calculation does not automatically become a downstream input.
18. Persisted evidence is reused rather than silently recomputed.
19. Domain concepts are not invented solely for implementation convenience.

The complete domain and contract definitions are maintained in `docs/Lakshya_Domain_Model.md`.

---

# Appendix — Current Implementation Status and Transition Boundary

**Status date:** 2026-10-01  
**Release:** Production v1.0.0, valuation as-of 2026-09-30. See `docs/Lakshya_Current_Status.md`.  
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

1. Position identity is `Investor + Folio + ISIN + Slice`. The physical holding remains `Investor + Folio + ISIN`.
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


## Current transition-stage sequence

The current implementation adds the following evidence-producing sequence beneath the existing pipeline:

```text
source Transactions
        ↓
lot reconstruction
        ↓
availability / lock classification
        ↓
Position bridge
        ↓
Purpose mapping
        ↓
lot → Position → Purpose reconciliation
        ↓
slice materialization
        ↓
human review artifact
```

This sequence is subordinate to the established pipeline and does not bypass the existing LPS, LFS, Purpose Staging, Historical Snapshot, or human review boundaries.

A balanced aggregate must not be treated as sufficient by itself. The underlying source rows, lot lineage, Position identity, Purpose attribution, and any classified anomaly must remain inspectable.
