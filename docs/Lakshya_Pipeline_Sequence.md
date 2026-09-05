# Lakshya Production Pipeline Sequence

**Status:** Production execution map

**Release:** FINAL / Compromise Programming v1

This document describes **how the production pipeline executes**. The companion architecture document describes **what each stage means, owns, consumes, and guarantees**. The two documents are intentionally complementary rather than repetitive.

---

## 1. End-to-end production sequence

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

The execution direction is therefore:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

No stage is permitted to use a later stage merely to make its own universe smaller.

---

# 2. Stage ownership at a glance

| Stage | Produces | Consumed downstream |
|---|---|---|
| FUND | admitted Funds, NAV evidence, Fund behavioural evidence | TEAM |
| TEAM | Team candidates, collective evidence, Team fingerprint, TEAM frontier | COMPOSITION |
| COMPOSITION | complete weighted Compositions, persisted fingerprints, global frontier | MISSION |
| MISSION | Purpose-qualified survivors, trajectory evidence | FINAL |
| FINAL | ordering, robustness diagnostics, winner, audit bundle | human decision layer |

The production invariant is:

```text
compute → persist → validate → consume
```

---

# 3. FUND execution

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

# 4. TEAM execution

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

# 5. COMPOSITION execution

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

# 6. MISSION execution

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

# 7. FINAL execution

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

# 8. FINAL comparison surface

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

# 9. FINAL mathematical execution

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

\[
L_2(i)=\sqrt{\sum_j d_{ij}^{2}}
\]

Worst-spoke diagnostic:

\[
L_\infty(i)=\max_j d_{ij}
\]

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

# 10. Persistence and resume semantics

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

# 11. Production audit trail

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

---

# 12. What this document intentionally does not decide

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

Those belong to future experiments or future explicitly versioned production contracts only if evidence earns them.

---

# 13. Production release boundary

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

Any future change to the decision rule is a deliberate production version change, not an undocumented edit to the current pipeline.
