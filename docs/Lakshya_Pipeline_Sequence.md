# Lakshya Production Pipeline Sequence

**Status:** Production execution map

**Release:** FINAL / Compromise Programming v1

This document describes **how the Lakshya review executes from manual inputs through the analytical pipeline, family-level observation, Purpose Staging, and historical persistence**. The companion architecture document describes **what each stage means, owns, consumes, and guarantees**. The two documents are intentionally complementary rather than repetitive.

---

## 1. End-to-end Lakshya review sequence

The complete annual review has two distinct parts: the analytical production chain and the human-controlled post-FINAL review layers.

```mermaid
flowchart TD
    A[Manual Fund scope<br/>data/fund/funds_in_scope.csv] --> B[Manual Purpose inputs<br/>data/purpose/purposes.csv]
    B --> C[FUND admission]
    C --> D[Persisted NAV evidence]
    D --> E[TEAM candidate generation]
    E --> F[TEAM collective evidence]
    F --> G[TEAM fingerprint]
    G --> H[TEAM 40-D Pareto frontier]
    H --> I[COMPOSITION 5% weight grid]
    I --> J[Persisted Composition fingerprint]
    J --> K[Global COMPOSITION 40-D Pareto frontier]
    K --> L{MISSION Purpose}
    L --> M[Achievability when finite target exists]
    L --> N[Open-ended Purpose: no Achievability]
    M --> O[Purpose Protection frontier]
    N --> O
    O --> P[MISSION survivors]
    P --> Q[Purpose Trajectory observation]
    Q --> R[FINAL Purpose comparison surface]
    R --> S[Population-relative radial coordinates]
    S --> T[Distance from Utopia]
    T --> U[L2 primary ordering]
    T --> V[L-infinity diagnostic]
    U --> W[L2/L-infinity joint frontier]
    U --> X[Lp robustness]
    U --> Y[Leave-one-spoke sensitivity]
    U --> Z[5,000-resample population bootstrap]
    W --> AA[FINAL evidence bundle]
    X --> AA
    Y --> AA
    Z --> AA
    AA --> AB[Archive FINAL summaries]
    AB --> AC[Family Architecture Validation]
    AC --> AD[Human review checkpoint]
    AD --> AE[Purpose Staging INIT]
    AE --> AF[Human staging turn]
    AF --> AG[Achievability + reconciliation]
    AG --> AH{Satisfied?}
    AH -->|No| AF
    AH -->|Yes| AI{Both pools zero?}
    AI -->|No| AF
    AI -->|Yes| AJ[Purpose Staging COMMIT]
    AJ --> AK[Authoritative purposes.csv updated]
    AK --> AL[Annual historical snapshot]
    AL --> AM[Git commit / historical snapshot]
    AM --> AN[CURRENT → TARGET transition planning]
```

The analytical production direction is:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

The complete review direction is:

```text
manual inputs
    ↓
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

The final transition is deliberately outside the analytical production decision. Lakshya does not automatically execute redemption or reinvestment.

---

## 2. Human-controlled review boundary

The annual review begins and ends with explicit human control. The system calculates consequences; it does not invent family priorities or transaction instructions.

```mermaid
sequenceDiagram
    participant Reviewer as Family reviewer
    participant Scope as Fund scope
    participant Purpose as Purpose inputs
    participant Production as Lakshya production
    participant Family as Family validation
    participant Staging as Purpose staging
    participant Git as Historical repository
    participant Transition as CURRENT → TARGET planning

    Reviewer->>Scope: review / update CURRENT & POTENTIAL
    Reviewer->>Purpose: review / update Purpose inputs
    Reviewer->>Production: start annual production review
    Production-->>Reviewer: FINAL evidence + winner per Purpose
    Reviewer->>Family: run family architecture validation
    Family-->>Reviewer: concentration / dependency observation
    Reviewer->>Staging: initialize review workspace
    loop reviewer turns
        Reviewer->>Staging: release / acquire / change Purpose levers
        Staging-->>Reviewer: staged state + ledger + Achievability
    end
    Reviewer->>Staging: commit when satisfied and pools = 0
    Staging-->>Purpose: promote staged Purpose state
    Reviewer->>Git: inspect and commit intended data/ annual snapshot
    Git-->>Reviewer: durable historical record
    Reviewer->>Transition: begin separate CURRENT → TARGET planning
```

The key boundary is:

> **The reviewer controls the terrain; Lakshya calculates the consequences.**

---

# 3. End-to-end production sequence

```mermaid
flowchart TD
    A[FUND source of truth] --> B[FUND admission]
    B --> C[Persisted NAV evidence]
    C --> D[TEAM candidate generation]
    D --> E[TEAM collective evidence]
    E --> F[TEAM fingerprint]
    F --> G[TEAM 40-D Pareto frontier]
    G --> H[COMPOSITION 5% weight grid]
    H --> I[Persisted Composition fingerprint]
    I --> J[Global COMPOSITION 40-D Pareto frontier]
    J --> K{MISSION Purpose}
    K --> L[Achievability when finite target exists]
    K --> M[Open-ended Purpose: no Achievability]
    L --> N[Purpose Protection frontier]
    M --> N
    N --> O[MISSION survivors]
    O --> P[Purpose Trajectory observation]
    P --> Q[FINAL Purpose comparison surface]
    Q --> R[Population-relative radial coordinates]
    R --> S[Distance from Utopia]
    S --> T[L2 primary ordering]
    S --> U[L-infinity diagnostic]
    T --> V[L2/L-infinity joint frontier]
    T --> W[Lp robustness]
    T --> X[Leave-one-spoke sensitivity]
    T --> Y[Population bootstrap]
    V --> Z[FINAL evidence bundle]
    W --> Z
    X --> Z
    Y --> Z
```

No stage is permitted to use a later stage merely to make its own universe smaller.

---

# 4. Stage ownership at a glance

| Stage | Produces | Consumed downstream |
|---|---|---|
| FUND | admitted Funds, NAV evidence, Fund behavioural evidence | TEAM |
| TEAM | Team candidates, collective evidence, Team fingerprint, TEAM frontier | COMPOSITION |
| COMPOSITION | complete weighted Compositions, persisted fingerprints, global frontier | MISSION |
| MISSION | Purpose-qualified survivors, trajectory evidence | FINAL |
| FINAL | ordering, robustness diagnostics, winner, audit bundle | Family Architecture Validation / human review |
| FAMILY ARCHITECTURE VALIDATION | family attribution, concentration and dependency observations | human review / Purpose Staging context |
| PURPOSE STAGING | staged Purpose state, reconciliation, Achievability | authoritative Purpose input after explicit commit |
| HISTORICAL SNAPSHOT | durable annual `data/` state | future annual review |

The production invariant is:

```text
compute → persist → validate → consume
```

---

# 5. FUND execution

```mermaid
sequenceDiagram
    participant Source as FUND source
    participant Admission as FUND admission
    participant NAV as NAV evidence
    participant TEAM as TEAM

    Source->>Admission: load data/fund/funds_in_scope.csv
    Admission->>Admission: apply CURRENT/POTENTIAL admission rules
    Admission-->>TEAM: admitted Fund universe
    NAV->>TEAM: persisted canonical NAV histories
```

### Execution notes

The 8-year lived-history rule applies to POTENTIAL/new-entry Funds. CURRENT Funds may be younger and remain valid.

`CURRENT` and `POTENTIAL` are admission concepts, not hidden downstream preferences.

Regular versus Direct is not a Lakshya analytical distinction.

FUND evidence remains descriptive. FUND does not perform Purpose suitability or portfolio allocation.

---

# 6. TEAM execution

```mermaid
sequenceDiagram
    participant Funds as Admitted Funds
    participant TeamGen as TEAM candidate generator
    participant Evidence as Collective evidence
    participant Fingerprint as Team fingerprint
    participant Frontier as TEAM frontier
    participant Composition as COMPOSITION

    Funds->>TeamGen: admitted Fund universe
    TeamGen->>TeamGen: generate singleton / pair / trio candidates
    TeamGen->>Evidence: construct collective NAV/evidence
    Evidence->>Fingerprint: build Team Behavioural Fingerprint
    Fingerprint->>Frontier: evaluate declared 40-D gate
    Frontier-->>Composition: non-dominated Team identities
```

TEAM uses:

```text
28 Elevation + 12 Protection = 40 dimensions
```

with Elevation horizons `3Y / 5Y / 7Y / 10Y` and the seven declared rolling measures.

TEAM uses weak exact Pareto non-dominance. It does not import Purpose semantics merely to reduce the frontier.

Fund-level Resilience is not currently part of the TEAM comparator gate because TEAM has not earned that downstream need. The evidence remains a FUND-level concept.

---

# 7. COMPOSITION execution

```mermaid
sequenceDiagram
    participant TEAM as TEAM frontier
    participant Grid as Composition grid
    participant Store as Composition fingerprint store
    participant Global as Global frontier
    participant MISSION as MISSION

    TEAM->>Grid: receive non-dominated Teams
    Grid->>Grid: generate complete weights
    Grid->>Store: request missing Composition fingerprint
    Store->>Store: compute expensive evidence once
    Store->>Store: atomic write + fsync
    Store-->>Global: persisted Composition fingerprints
    Global->>Global: apply 40-D weak Pareto frontier
    Global-->>MISSION: global survivor identities
```

The positive weight grid is:

```text
singleton: 100%
pair:       19 allocations at 5% increments
trio:      171 allocations at 5% increments
```

The persistence rule is important:

> A downstream algorithm change does not justify rebuilding a valid upstream Composition fingerprint.

Recomputation requires a genuine upstream evidence or fingerprint-schema change.

---

# 8. MISSION execution

```mermaid
sequenceDiagram
    participant Global as Global frontier
    participant Purpose as Purpose definition
    participant Mission as MISSION
    participant Protection as Purpose Protection frontier
    participant Trajectory as TRAJECTORY
    participant Final as FINAL

    Global->>Mission: persisted global survivor identities
    Purpose->>Mission: Purpose horizon + target inputs
    alt finite target Purpose
        Mission->>Mission: Achievability gate
    else open-ended Purpose
        Mission->>Mission: skip Achievability
    end
    Mission->>Protection: Purpose-qualified Compositions
    Protection->>Mission: Protection-only non-dominated set
    Mission-->>Trajectory: MISSION survivors
    Purpose->>Trajectory: requested Purpose horizon
    Trajectory->>Trajectory: select supported analytical observation horizon
    Trajectory-->>Final: persisted trajectory evidence
```

### Mission horizon execution rule

Supported analytical horizons are:

```text
3Y / 5Y / 7Y / 10Y
```

The canonical selection is the longest supported horizon not beyond the Purpose horizon.

Examples:

```text
4Y  → 3Y
6Y  → 5Y
8Y  → 7Y
9Y  → 7Y
12Y → 10Y
13Y → 10Y
```

Purpose horizon is never converted into a requirement for equivalent lived history.

### Trajectory execution rule

Trajectory observation uses the lower-level observation convention:

```text
latest observed NAV = end
requested target start = end - requested years
actual start = latest observation on/before target start
preserve every observed point from actual start to latest
normalize relative to actual start NAV
```

The output retains Purpose horizon, nominal analytical horizon, actual selected horizon and status.

Trajectory is descriptive in the current architecture and does not itself remove a MISSION survivor.

---

# 9. FINAL execution

FINAL receives **only MISSION survivors**. It does not reopen MISSION eligibility.

```mermaid
sequenceDiagram
    participant Mission as MISSION survivors
    participant Evidence as Persisted Composition evidence
    participant Surface as FINAL surface
    participant Coordinates as Percentile coordinates
    participant Norms as Compromise norms
    participant Robust as Robustness suite
    participant Output as FINAL outputs

    Mission->>Surface: Purpose survivor identities
    Evidence->>Surface: selected-horizon Elevation + native Protection
    Surface->>Surface: validate complete evidence
    Surface->>Surface: exclude zero-variance spokes only
    Surface->>Coordinates: convert native evidence to radial coordinates
    Coordinates->>Norms: x(i,j) in [0,1]
    Norms->>Norms: Utopia U(j) = 1
    Norms->>Norms: d(i,j) = 1 - x(i,j)
    Norms->>Norms: primary L2 ordering
    Norms->>Norms: L-infinity worst-spoke diagnostic
    Norms->>Robust: Lp sweep
    Norms->>Robust: leave-one-spoke sensitivity
    Norms->>Robust: 5,000 population bootstrap
    Norms->>Output: winner + complete ordering evidence
    Robust->>Output: robustness evidence
```

---

# 10. FINAL comparison surface

For Purpose-selected Elevation horizon `H`, FINAL begins with:

```text
7 Elevation(H) + 12 native Protection
```

All retained individual spokes have equal weight.

Protection is not given an artificial horizon.

A spoke is removed only when it has zero variance across the current comparison population.

For the current five 245-Composition Purpose populations:

```text
19 candidate spokes
− 1 zero-variance spoke
= 18 informative spokes
```

The current zero-variance spoke is:

```text
elevation_7y_positive_period_pct
```

The same construction is performed independently for each Purpose. No Purpose inherits another Purpose's winner or spoke set.

---

# 11. FINAL mathematical execution

For each retained spoke `j` and Composition `i`:

```text
native evidence
      ↓
population-relative percentile coordinate x(i,j)
      ↓
Protection direction reversed so higher = better
      ↓
Utopia U(j) = 1
      ↓
distance / regret d(i,j) = 1 - x(i,j)
```

Primary ordering:

$$
L_2(i)=\sqrt{\sum_j d_{ij}^{2}}
$$

Worst-spoke diagnostic:

$$
L_\infty(i)=\max_j d_{ij}
$$

Joint diagnostic:

```text
minimize (L2, L∞)
```

Robustness:

```text
p = 1.00 … 10.00 in steps of 0.25
+
leave one retained spoke out at a time
+
5,000 seeded population bootstrap resamples
```

No second normalization is applied to the percentile coordinates.

No subjective Purpose score is introduced.

---

# 12. Family Architecture Validation execution

Family Architecture Validation runs **after FINAL has been archived**. It observes the family-level consequence of independently derived Purpose decisions without changing those decisions.

```mermaid
sequenceDiagram
    participant Purpose as data/purpose/purposes.csv
    participant Archive as Archived FINAL summaries
    participant Manifest as Review manifest
    participant Metadata as Fund metadata
    participant Attribution as Family validation
    participant Review as Human reviewer

    Purpose->>Attribution: Purpose current capital
    Archive->>Attribution: FINAL winner + Composition weights
    Manifest->>Attribution: verify archive integrity / lineage
    Metadata->>Attribution: fund + AMC identity
    Attribution->>Attribution: Purpose capital × fund weight
    Attribution->>Attribution: aggregate fund concentration
    Attribution->>Attribution: aggregate AMC / ecosystem concentration
    Attribution->>Attribution: reconcile Purpose-level totals
    Attribution-->>Review: family attribution / concentration / dependency
```

The layer consumes already-earned production information only. It does not recompute FINAL, inspect candidate populations, impose concentration thresholds, or alter winners.

Its central attribution contract is:

```text
Purpose current capital
        ×
FINAL Composition fund weight
        =
Attributed capital
```

The generated forensic log is not part of the canonical annual snapshot and is ignored by Git.

---

# 13. Purpose Staging execution

Purpose Staging begins only after the family-level observation has been reviewed. It is a human-in-the-loop reconciliation workspace, not an optimizer.

```mermaid
sequenceDiagram
    participant Source as Authoritative purposes.csv
    participant Reviewer as Human reviewer
    participant Workspace as Purpose staging workspace
    participant Achievability as Achievability engine
    participant Ledger as Reconciliation ledger
    participant Commit as Commit boundary

    Reviewer->>Workspace: INIT review workspace
    Workspace->>Source: read authoritative Purpose state
    Source-->>Workspace: copy Purpose state
    Workspace-->>Reviewer: staged state + empty pools

    loop one or more review turns
        Reviewer->>Workspace: submit Purpose lever changes
        Workspace->>Workspace: release reduced capital / SIP
        Reviewer->>Workspace: specify pool acquisition percentages
        Workspace->>Workspace: allocate from same turn-start pool base
        Workspace->>Ledger: record releases + acquisitions
        Workspace->>Achievability: recalculate staged consequences
        Achievability-->>Reviewer: latest Achievability
        Workspace-->>Reviewer: staged state + pools + ledger
    end

    Reviewer->>Commit: request COMMIT
    Commit->>Commit: require reviewer satisfaction
    Commit->>Commit: require capital pool = 0
    Commit->>Commit: require SIP pool = 0
    Commit->>Commit: backup purposes_before_commit.csv
    Commit->>Source: promote staged Purpose state
    Commit-->>Reviewer: COMMITTED
```

The conservation rule is:

```text
Purpose value reduction  → capital pool
Purpose SIP reduction    → SIP pool
pool acquisition         → another Purpose
```

A reviewer cannot silently create capital or SIP by directly increasing `value` or `monthly_plan`.

Acquisition percentages apply to the **same pool available at the start of the acquisition phase** for that turn; they are not applied sequentially to a shrinking pool.

The structured staging artifacts are retained under:

```text
data/reviews/YYYY-MM-DD/purpose_staging/
```

The generated `staging.log` remains beside them for forensic diagnosis but is ignored by Git.

---

# 14. Historical snapshot execution

After Purpose Staging is explicitly committed, the annual review reaches its persistence boundary. The durable `data/` state becomes part of Lakshya's historical memory.

```mermaid
sequenceDiagram
    participant Reviewer as Human reviewer
    participant Data as Lakshya data/
    participant Ignore as Git ignore rules
    participant Git as Git repository

    Reviewer->>Data: inspect annual review changes
    Data-->>Reviewer: authoritative inputs + review artifacts
    Reviewer->>Ignore: exclude generated runtime logs
    Ignore-->>Reviewer: staging.log / family_attribution.log excluded
    Reviewer->>Git: git status
    Reviewer->>Git: git diff --cached after selective staging
    Reviewer->>Git: commit intended annual snapshot
    Git-->>Reviewer: durable review history
```

The intended persistence distinction is:

| Material | Persistence role |
|---|---|
| `data/fund/` authoritative inputs | durable, version-controlled |
| `data/purpose/` authoritative inputs | durable, version-controlled |
| `data/reviews/<as-of>/` structured annual artifacts | durable, version-controlled |
| `data/reviews/<as-of>/purpose_staging/` structured staging state | durable, version-controlled |
| `staging.log` | generated forensic log, Git-ignored |
| `family_attribution.log` | generated forensic log, Git-ignored |
| `output/` | disposable/regenerable runtime area |

The annual snapshot is a historical record, not a transaction ledger or automatic trading instruction.

---

# 15. Persistence and resume semantics

A production stage follows this pattern:

```text
load
  ↓
validate
  ↓
reuse valid checkpoint ──────────────┐
  ↓                                 │
compute missing/stale evidence      │
  ↓                                 │
atomic persist                      │
  ↓                                 │
validate                            │
  ↓                                 │
consume ◀───────────────────────────┘
```

The critical resume principle is:

> **A downstream failure must not invalidate upstream evidence that remains valid.**

Thus a future FINAL contract can be rerun against the same MISSION evidence without rebuilding FUND, TEAM or COMPOSITION unless the dependency contract genuinely changes.

---

# 16. Production audit trail

For each Purpose, FINAL produces:

```text
axes
signatures
distances
results
Lp sweep
leave-one-spoke sensitivity
bootstrap
joint L2/L∞ frontier
summary
```

The compact production hand-off is:

```text
final_<Purpose>_summary.csv
```

The remaining artifacts preserve the path from **30,000 feet to 3 feet** so that the winner is auditable rather than merely asserted.

Family Architecture Validation then produces the family-level attribution and dependency record, while Purpose Staging preserves the human reconciliation path.

---

# 17. What this document intentionally does not decide

This is an execution document. It does not define or introduce new analytical concepts beyond the production contract.

It therefore does not add:

- Composition regions;
- clustering;
- arbitrary k-neighbour connectivity;
- subjective Purpose scoring;
- Purpose-specific spoke weights;
- synthetic Purpose targets;
- arbitrary L-infinity thresholds;
- future-return forecasts; or
- causal explanations for why a Composition wins.

It also does not automate:

- family priority selection;
- concentration tolerance decisions;
- Purpose priority decisions;
- redemption decisions;
- tax or exit-load optimization; or
- reinvestment transactions.

Those belong to future explicitly versioned production contracts or human-controlled transition planning only if evidence earns them.

---

# 18. Production release boundary

FINAL v1 is production-complete when:

- the architecture is documented;
- the execution sequence is deterministic apart from explicitly seeded bootstrap sampling;
- incomplete required evidence fails loudly;
- zero-variance handling is explicit;
- expensive upstream evidence is reused;
- outputs are written atomically;
- the FINAL contract is versioned;
- tests cover the mathematical invariants; and
- exploratory machinery is not required for the production decision.

The broader annual review is complete for archival purposes when:

- manual Fund and Purpose inputs have been reviewed;
- production and Family Architecture Validation have been reviewed;
- Purpose Staging has been explicitly committed;
- intended `data/` changes have been inspected; and
- the annual snapshot has been committed to Git, excluding Git-ignored generated logs.

Any future change to the decision rule is a deliberate production version change, not an undocumented edit to the current pipeline.
