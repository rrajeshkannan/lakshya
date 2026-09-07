# Lakshya Production Pipeline Sequence

**Status:** Production execution map

**Release:** FINAL / Compromise Programming v1

**As of:** 2026-09-07

This document describes **how the Lakshya review executes**. `docs/Lakshya_Architecture.md` describes what each stage means and owns. `docs/Lakshya_HowTo.md` describes how a reviewer operates the workflow. The documents are intentionally complementary.

---

## 1. End-to-end annual review

The annual review has a completed analytical chain, human-controlled post-FINAL review layers, a deliberate historical persistence boundary, and then a separate CURRENT → TARGET transition stage.

```mermaid
flowchart TD
    A[Manual Fund scope<br/>data/fund/funds_in_scope.csv] --> B[Manual Purpose inputs<br/>data/purpose/purposes.csv]
    B --> C[FUND admission]
    C --> D[Canonical NAV evidence]
    D --> E[TEAM candidate generation]
    E --> F[Collective Timeline / evidence]
    F --> G[TEAM fingerprint]
    G --> H[TEAM 40-D Pareto frontier]
    H --> I[COMPOSITION weight grid]
    I --> J[Persist / reuse Composition fingerprints]
    J --> K[Global COMPOSITION frontier]
    K --> L{MISSION Purpose}
    L --> M[Achievability when finite target exists]
    L --> N[Open-ended Purpose: skip Achievability]
    M --> O[Purpose Protection frontier]
    N --> O
    O --> P[MISSION survivors]
    P --> Q[Trajectory observation]
    Q --> R[FINAL comparison]
    R --> S[Robustness / audit bundle]
    S --> T[Archive FINAL summaries]
    T --> U[Family Architecture Validation]
    U --> V[Human family review]
    V --> W[Purpose Staging INIT]
    W --> X[Human staging turns]
    X --> Y[Achievability + reconciliation]
    Y --> Z{Satisfied?}
    Z -->|No| X
    Z -->|Yes| AA{Both pools zero?}
    AA -->|No| X
    AA -->|Yes| AB[Purpose Staging COMMIT]
    AB --> AC[Authoritative purposes.csv updated]
    AC --> AD[Human annual snapshot review]
    AD --> AE[Git commit / historical snapshot]
    AE --> AF[CURRENT → TARGET transition]
```

The analytical production direction is:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

The complete annual-review direction is:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
        ↓
FAMILY ARCHITECTURE VALIDATION
        ↓
PURPOSE STAGING
        ↓
HISTORICAL SNAPSHOT
        ↓
CURRENT → TARGET TRANSITION
```

The transition stage does not reopen the analytical decision and does not automatically execute transactions.

---

## 2. Human-controlled review boundary

```mermaid
sequenceDiagram
    participant Reviewer as Family reviewer
    participant Production as Lakshya production
    participant Family as Family validation
    participant Staging as Purpose staging
    participant Git as Historical repository
    participant Transition as CURRENT → TARGET

    Reviewer->>Production: review Fund scope + Purpose inputs
    Production-->>Reviewer: FINAL evidence + winner per Purpose
    Reviewer->>Family: run family architecture validation
    Family-->>Reviewer: concentration / dependency observation
    Reviewer->>Staging: initialize workspace
    loop one or more turns
        Reviewer->>Staging: release / acquire / change Purpose levers
        Staging-->>Reviewer: staged state + ledger + Achievability
    end
    Reviewer->>Staging: COMMIT when satisfied and pools = 0
    Staging-->>Reviewer: authoritative Purpose state promoted
    Reviewer->>Git: inspect intended annual data/
    Reviewer->>Git: commit historical snapshot
    Git-->>Reviewer: durable annual record
    Reviewer->>Transition: begin separate CURRENT → TARGET planning
```

The governing principle is:

> **The reviewer controls the terrain; Lakshya calculates the consequences.**

---

# 3. Analytical production sequence

```mermaid
flowchart TD
    A[FUND source] --> B[Admission]
    B --> C[Canonical NAV histories]
    C --> D[TEAM candidates]
    D --> E[Collective Timeline]
    E --> F[Team fingerprint]
    F --> G[40-D weak Pareto frontier]
    G --> H[COMPOSITION 5% grid]
    H --> I[Composition fingerprints]
    I --> J[Global 40-D frontier]
    J --> K[MISSION Purpose qualification]
    K --> L[Achievability when applicable]
    L --> M[Protection-only frontier]
    M --> N[Trajectory observation]
    N --> O[FINAL Purpose surface]
    O --> P[Percentile coordinates]
    P --> Q[Utopia / distance]
    Q --> R[L2 primary ordering]
    R --> S[L∞ diagnostic / joint frontier]
    R --> T[Lp robustness]
    R --> U[Leave-one-spoke sensitivity]
    R --> V[5,000 seeded bootstrap]
    S --> W[FINAL evidence bundle]
    T --> W
    U --> W
    V --> W
```

No stage may use a later stage merely to make its own universe smaller.

---

# 4. Persistence / resume sequence

```mermaid
flowchart LR
    A[Load source] --> B[Validate]
    B --> C{Valid checkpoint?}
    C -->|Yes| D[Reuse]
    C -->|No| E[Compute missing / stale evidence]
    E --> F[Atomic persist]
    F --> G[Validate persisted evidence]
    D --> G
    G --> H[Consume downstream]
```

The critical invariant is:

> **A downstream failure must not invalidate upstream evidence that remains valid.**

Composition checkpoints use the durable, narrow Completion Index to avoid repeating expensive filesystem/JSON validation when the indexed checkpoint metadata still matches. The index is specifically a Composition checkpoint mechanism, not a generic artifact store.

---

# 5. FUND execution

```mermaid
sequenceDiagram
    participant Source as FUND source
    participant Admission as Admission
    participant NAV as Canonical NAV boundary
    participant TEAM as TEAM

    Source->>Admission: load funds_in_scope.csv
    Admission->>Admission: apply CURRENT/POTENTIAL rules
    Admission->>NAV: load / validate NAV histories
    NAV-->>TEAM: canonical Fund histories
```

The 8-year lived-history rule applies to POTENTIAL/new-entry Funds. CURRENT Funds may be younger and remain valid. CURRENT/POTENTIAL do not become hidden downstream quality preferences.

---

# 6. TEAM execution

```mermaid
sequenceDiagram
    participant Funds as Admitted Funds
    participant TeamGen as Candidate generator
    participant Timeline as Collective Timeline
    participant Fingerprint as Team fingerprint
    participant Frontier as TEAM frontier
    participant Composition as COMPOSITION

    Funds->>TeamGen: admitted universe
    TeamGen->>TeamGen: singleton / pair / trio
    TeamGen->>Timeline: constituent canonical histories
    Timeline->>Timeline: common period + union of actual observations
    Timeline->>Timeline: latest NAV on/before each observation
    Timeline->>Fingerprint: collective NAV
    Fingerprint->>Frontier: 28 Elevation + 12 Protection
    Frontier-->>Composition: non-dominated Teams
```

Collective Timeline semantics are exact: no calendar-day manufacture and no interpolation. A singleton Team reproduces its Fund trajectory.

---

# 7. COMPOSITION execution

```mermaid
sequenceDiagram
    participant TEAM as TEAM frontier
    participant Grid as Weight grid
    participant Store as Fingerprint store
    participant Global as Global frontier
    participant MISSION as MISSION

    TEAM->>Grid: non-dominated Teams
    Grid->>Grid: complete positive weights
    Grid->>Store: lookup Composition checkpoint
    alt valid checkpoint exists
        Store-->>Global: reuse evidence
    else missing / stale
        Store->>Store: compute Composition evidence
        Store->>Store: atomic persist + fsync
        Store-->>Global: persisted evidence
    end
    Global->>Global: exact 40-D weak Pareto frontier
    Global-->>MISSION: survivor identities
```

Current positive grid:

```text
singleton: 100%
pair:       19 allocations at 5% increments
trio:      171 allocations at 5% increments
```

A downstream algorithm change alone does not justify rebuilding valid Composition evidence.

---

# 8. MISSION execution

```mermaid
sequenceDiagram
    participant Global as Global Composition frontier
    participant Purpose as Purpose input
    participant Mission as MISSION
    participant Protection as Protection frontier
    participant Trajectory as Trajectory
    participant Final as FINAL

    Global->>Mission: persisted survivor identities
    Purpose->>Mission: Purpose horizon + target
    alt finite target
        Mission->>Mission: Achievability
    else open-ended
        Mission->>Mission: skip Achievability
    end
    Mission->>Protection: Purpose-qualified set
    Protection->>Mission: Protection-only non-dominated set
    Mission->>Trajectory: MISSION survivors
    Purpose->>Trajectory: requested horizon
    Trajectory->>Trajectory: select supported actual observation horizon
    Trajectory-->>Final: descriptive trajectory evidence
```

Supported analytical horizons are `3Y / 5Y / 7Y / 10Y`; the longest supported horizon not beyond the Purpose horizon is selected. Trajectory remains descriptive and does not currently eliminate a MISSION survivor.

---

# 9. FINAL execution

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
    Surface->>Surface: exclude zero-variance spokes only
    Surface->>Norm: percentile coordinates + Utopia
    Norm->>Norm: primary L2 ordering
    Norm->>Robust: L∞ diagnostic / joint frontier
    Norm->>Robust: Lp sweep
    Norm->>Robust: leave-one-spoke sensitivity
    Norm->>Robust: 5,000 seeded bootstrap
    Norm->>Output: winner + ordering evidence
    Robust->>Output: robustness evidence
```

For selected horizon `H`, FINAL uses `7 Elevation(H) + 12 native Protection`. Retained spokes are equally weighted. L2 is the production ordering; robustness does not override the primary definition.

---

# 10. Family Architecture Validation execution

```mermaid
sequenceDiagram
    participant Purpose as Purpose capital
    participant Archive as Archived FINAL
    participant Metadata as Fund / AMC metadata
    participant Validation as Family validation
    participant Reviewer as Human reviewer

    Purpose->>Validation: current Purpose capital
    Archive->>Validation: FINAL winner + Composition weights
    Metadata->>Validation: identity / AMC mapping
    Validation->>Validation: Purpose × fund-weight attribution
    Validation->>Validation: fund / AMC aggregation
    Validation-->>Reviewer: concentration / dependency observation
```

This layer is descriptive. It does not alter FINAL, optimize family allocation, impose concentration limits, or introduce transition assumptions.

---

# 11. Purpose Staging execution

```mermaid
sequenceDiagram
    participant Source as authoritative purposes.csv
    participant Reviewer as reviewer
    participant Stage as staging workspace
    participant Ledger as reconciliation ledger
    participant Ach as Achievability
    participant Commit as commit boundary

    Reviewer->>Stage: INIT
    Stage->>Source: read authoritative state
    Source-->>Stage: isolated staged copy
    loop review turns
        Reviewer->>Stage: Purpose lever changes
        Stage->>Stage: release reductions into pools
        Reviewer->>Stage: acquisition percentages
        Stage->>Stage: allocate from turn-start pool base
        Stage->>Ledger: record releases / acquisitions
        Stage->>Ach: recalculate consequences
        Ach-->>Reviewer: latest Achievability
    end
    Reviewer->>Commit: COMMIT
    Commit->>Commit: require satisfaction + both pools zero
    Commit->>Commit: backup purposes_before_commit.csv
    Commit->>Source: promote staged state
    Source-->>Reviewer: authoritative Purpose state updated
```

Purpose Staging never selects family priorities and never changes upstream analytical decisions.

---

# 12. Historical snapshot execution

```mermaid
sequenceDiagram
    participant Reviewer as Human reviewer
    participant Data as data/
    participant Git as Git repository

    Reviewer->>Data: inspect intended annual changes
    Reviewer->>Data: confirm authoritative + structured review state
    Reviewer->>Git: selectively stage intended data/
    Reviewer->>Git: commit annual snapshot
    Git-->>Reviewer: durable historical state
```

Historical Snapshot is a human-controlled persistence boundary. There is no separate automatic snapshotter. Generated runtime logs and `output/` remain disposable.

---

# 13. CURRENT → TARGET transition sequence

This stage starts **after** the annual snapshot has been deliberately committed. It is not part of the analytical optimizer.

```mermaid
sequenceDiagram
    participant Source as Actual portfolio sources
    participant Current as Economic CURRENT
    participant Review as Reviewed annual state
    participant Target as TARGET construction
    participant Compare as Transition analysis
    participant Human as Human reviewer / executor

    Source->>Current: inspect account / portfolio records
    Current->>Current: establish source-derived holding state
    Review->>Target: Purpose state + FINAL Composition decisions
    Target->>Target: derive fund-level target architecture
    Current->>Compare: actual holdings
    Target->>Compare: desired architecture
    Compare->>Compare: match / retain / change analysis
    Compare->>Compare: apply only evidenced constraints
    Compare-->>Human: feasible transition analysis
    Human->>Human: decide / execute transactions externally
```

The critical distinction is:

```text
Analytical CURRENT = what the reviewed Lakshya architecture says
Economic CURRENT   = what the family actually owns
TARGET             = what the reviewed decisions imply should be owned
```

The first transition task is **source archaeology**, not coding. Inspect the actual portfolio/account material (including the identified Geojit material) to determine what it really provides for holding identity, units, current value, observation date, account/folio context, acquisition/transaction information, cost information, and missing facts.

Only then define the **minimum sufficient CURRENT contract**. Do not infer actual holdings from `funds_in_scope.csv`, FINAL summaries, or Purpose data.

---

# 14. Transition planning non-responsibilities

The CURRENT → TARGET stage does not:

- reopen FUND admission;
- redefine TEAM formation;
- alter Composition weights because of inconvenient current holdings;
- rerun MISSION merely because transition is difficult;
- replace a FINAL winner with a newly optimized fund;
- encode hidden Purpose priorities;
- equate analytical CURRENT with economic CURRENT;
- manufacture tax/cost/transaction facts absent from the source; or
- execute transactions automatically.

There is no production CURRENT schema, transition optimizer, tax engine, or transaction executor yet.

---

# 15. Production audit trail

For each Purpose, the durable/inspectable analytical path is:

```text
FUND evidence
→ TEAM evidence
→ COMPOSITION fingerprint
→ MISSION qualification
→ Trajectory observation
→ FINAL ordering + robustness
→ archived FINAL summary
→ family attribution
→ Purpose staging state
→ historical annual snapshot
```

The transition stage begins from that historical state plus separately sourced actual holdings. It must not pretend the analytical archive is an account statement.

---

# 16. What this document intentionally does not decide

This is an execution document. It does not introduce:

- Composition regions;
- clustering;
- subjective Purpose scoring;
- Purpose-specific spoke weights;
- synthetic Purpose targets;
- arbitrary L∞ thresholds;
- future-return forecasts; or
- causal explanations for why a Composition wins.

It also does not automate family priority selection, concentration tolerance decisions, redemption decisions, tax optimization, or reinvestment transactions.
