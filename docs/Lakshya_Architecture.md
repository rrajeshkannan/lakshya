# Lakshya Production Architecture

**Status:** Authoritative production architecture

**Release:** FINAL / Compromise Programming v1

**As of:** 2026-09-07

This is the single architecture document for Lakshya. It describes what each stage means, what it owns, what it may consume, and where the annual review deliberately hands off to the separate CURRENT → TARGET transition. Execution detail belongs in `docs/Lakshya_Pipeline_Sequence.md`; practical operation belongs in `docs/Lakshya_HowTo.md`.

---

# 1. Architectural statement

Lakshya is a family-specific investment-engineering system. It earns a portfolio decision through progressively higher-order evidence, makes the family-level consequence visible, provides a human-controlled Purpose reconciliation workspace, preserves the reviewed annual state, and then begins a separate transition analysis between what the family actually owns and what the reviewed architecture says it should own.

The analytical production chain is:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

The complete annual-review architecture is:

```text
FUND
  ↓
TEAM
  ↓
COMPOSITION
  ↓
MISSION
  ↓
FINAL
  ↓
FAMILY ARCHITECTURE VALIDATION
  ↓
PURPOSE STAGING
  ↓
HISTORICAL SNAPSHOT
  ↓
CURRENT → TARGET TRANSITION
```

The last stage is deliberately a **separate next-stage architecture**, not an extension of the analytical optimizer.

| Stage | Question | Nature |
|---|---|---|
| FUND | What kind of teammate is this fund? | individual behavioural evidence |
| TEAM | What kind of collective do these teammates form? | structural collective evidence |
| COMPOSITION | Where does capital sit within a collective? | allocation geometry |
| MISSION | Can this Composition serve this Purpose? | Purpose-specific qualification |
| FINAL | Among qualified Compositions, which is the strongest practical compromise? | production ordering |
| FAMILY ARCHITECTURE VALIDATION | What family-level concentration/dependency follows from the independent Purpose decisions? | descriptive attribution |
| PURPOSE STAGING | What happens when the reviewer changes Purpose requirements and redistributes released capital/SIP? | human-in-loop reconciliation |
| HISTORICAL SNAPSHOT | What reviewed state should become durable annual memory? | human-controlled persistence |
| CURRENT → TARGET | What must change between actual holdings and the reviewed target architecture? | separate transition analysis |

The architecture deliberately separates **evidence construction**, **eligibility/elimination**, **ordering**, **family-level observation**, **human reconciliation**, **historical persistence**, and **transaction transition analysis**.

> **Information should be introduced at the layer that genuinely earns the need for it.**

For expensive evidence:

> **Compute once. Persist immediately. Reuse forever.**

Lakshya does not automatically redeem, purchase, switch, or otherwise transact on behalf of the family.

---

# 2. Cross-stage production discipline

Lakshya follows these invariants:

1. **Observed is not inferred.**
2. **Unknown is not zero.**
3. A Purpose horizon is not a demand for equivalent lived Fund history.
4. A calculation does not automatically become a downstream input.
5. Persisted evidence is reused rather than silently recomputed.
6. A higher stage consumes only information whose semantic need it has earned.
7. Experimental exploration may discover a rule; production codifies the rule explicitly.
8. A production rule changes only through a deliberate versioned release.
9. Rich evidence may be compressed for a higher-order boundary, but compression must not erase meaning.
10. A later-stage failure does not invalidate valid upstream evidence.
11. Family-level observation does not retroactively change an upstream winner.
12. Human Purpose priority is expressed through review inputs, not encoded as a hidden system ranking.
13. Historical persistence records reviewed state; it is not an automatic transaction ledger.
14. Actual holdings are source-derived; analytical CURRENT must never be mistaken for economic CURRENT.
15. Transition planning must not become a second portfolio optimizer.

Preferred lifecycle:

```text
compute → persist → validate → consume
```

---

# 3. FUND — individual behavioural entity

FUND asks:

> **What kind of teammate is this fund?**

FUND owns Fund admission, canonical NAV evidence, Fund behavioural calculations, Fund fingerprints, lineage, persistence, and Fund-level Compass views.

The principal behavioural evidence families are:

```text
Elevation
Protection
```

Evidence quality is a guardrail around interpretation, not a behavioural dimension.

The explicit family scope source is:

```text
data/fund/funds_in_scope.csv
```

The 8-year lived-history rule applies to **POTENTIAL/new-entry** Funds. CURRENT Funds may be younger and remain valid. CURRENT/POTENTIAL are admission concepts, not hidden downstream preferences. Regular versus Direct is not a Lakshya analytical distinction.

The NAV boundary is canonical and rejects ambiguous duplicate dates. Canonical histories are chronological, numeric, positive and unique.

Elevation is observed through rolling-return distributions across:

```text
3Y / 5Y / 7Y / 10Y
```

using the declared seven rolling measures. Protection is the Fund's drawdown-severity surface, including severity quantiles and threshold frequencies. These describe historical terrain; they are not forecasts.

FUND does not own Team formation, Purpose suitability, portfolio composition, allocation per Purpose, MISSION decisions, or FINAL optimization.

---

# 4. TEAM — collective behavioural entity

TEAM asks:

> **What kind of collective do these teammates form?**

The current universe contains singleton, pair, and trio Teams; maximum Team size is 3. Candidate generation is deterministic.

TEAM constructs collective evidence from the constituent Fund histories rather than averaging or compressing Fund scores before collective analysis:

```text
admitted Fund histories
        ↓
Team candidate
        ↓
Collective Timeline / collective NAV
        ↓
collective behavioural evidence
        ↓
Team Behavioural Fingerprint
```

Collective NAV uses the latest actual constituent NAV on or before each actual collective observation date, over the common historical period. It does not manufacture calendar observations or interpolate.

TEAM's declared comparator surface is:

```text
28 Elevation + 12 Protection = 40 dimensions
```

TEAM applies exact weak Pareto non-dominance with:

```text
Elevation  → UP
Protection → DOWN
```

TEAM is elimination, not ranking. It must not import MISSION semantics merely to make its universe smaller.

TEAM owns candidate formation, collective evidence, Team fingerprints, the 40-D comparator surface, unavailable-evidence handling, exact frontier calculation, and orchestration.

TEAM does not own Purpose suitability, allocation, MISSION, or FINAL.

> **TEAM must not decide what MISSION wants.**

---

# 5. COMPOSITION — capital allocation inside a collective

COMPOSITION asks:

> **Where does capital sit within a Team?**

A Composition is **Team + complete weights**. The current positive grid is:

```text
singleton: 100%
pair:       19 allocations at 5% increments
trio:      171 allocations at 5% increments
```

Composition fingerprints are durable reusable evidence containing identity, members, weights and behavioural evidence including NAV, Elevation and Protection. The fingerprint store uses stable identity paths, schema/kind validation, atomic writes, `fsync`, and lossless rehydration.

The global Composition frontier uses the same 40-D Elevation + Protection surface and weak Pareto non-dominance. Purpose-specific qualification begins from that global evidence rather than inventing a second identical gate merely to force another reduction.

COMPOSITION owns complete allocations, identity, evidence, persistence, and the global frontier. It does not decide Purpose suitability.

---

# 6. MISSION — Purpose-specific qualification

MISSION asks:

> **Can this Composition serve this Purpose?**

MISSION is the first stage where Purpose semantics enter the analytical contract.

A Purpose may have a finite target/deadline or an open-ended objective with an explicit analytical horizon. Open-ended Purposes still receive Elevation, Protection and Trajectory observation; only Achievability is skipped when there is no finite target requirement.

Supported analytical horizons are:

```text
3Y / 5Y / 7Y / 10Y
```

The rule is the longest supported horizon not beyond the Purpose horizon. For example:

```text
4Y → 3Y    6Y → 5Y    8Y → 7Y
9Y → 7Y   12Y → 10Y  13Y → 10Y
```

The production logical sequence is:

```text
Global Composition frontier
        ↓
Purpose Achievability, when applicable
        ↓
Purpose Protection frontier
        ↓
MISSION survivors
        ↓
Purpose Trajectory observation
```

Trajectory is descriptive and does not currently remove a MISSION survivor. It uses the latest observed NAV as end, selects the actual observation on/before the requested start, preserves observed points through end, and normalizes relative to the actual start. Nominal and actual horizons remain explicit.

MISSION owns Purpose qualification and Purpose-facing interpretation. It does not silently redefine the global Composition evidence contract.

---

# 7. FINAL — production ordering

FINAL asks:

> **Among already-qualified MISSION Compositions, which is the strongest practical compromise against the best evidence the surviving population can actually attain?**

FINAL is an **ordering stage**, not another admission stage. It receives only MISSION survivors and does not reopen upstream eligibility.

For Purpose-selected Elevation horizon `H`, the comparison surface is:

```text
7 Elevation(H) + 12 native Protection
```

A spoke is removed only when it has zero variance across the current comparison population. Retained spokes are equally weighted.

Native values are converted to population-relative percentile coordinates in `[0,1]`; Protection direction is reversed so higher is always better. The Utopia Point is `1` on every retained spoke and:

```text
d(i,j) = 1 - x(i,j)
```

Primary ordering is unweighted Euclidean distance:

\[
L_2(i)=\sqrt{\sum_j d_{ij}^{2}}
\]

The smallest L2 distance is the production winner.

L-infinity remains a worst-spoke diagnostic and joint `(L2, L∞)` frontier; it is not an arbitrary kill threshold. FINAL also performs the declared Lp sweep, leave-one-spoke sensitivity, and 5,000 seeded population bootstrap. Robustness outputs describe stability and do not override the primary winner.

Any future change to the decision rule requires a deliberate production contract version.

---

# 8. FAMILY ARCHITECTURE VALIDATION — descriptive family observation

Family Architecture Validation runs after FINAL archival. It answers:

> **Given those Purpose-level decisions together, where does family capital depend on common funds or investment organizations?**

It is **attribution, not optimization**.

Its core contract is:

```text
Purpose current capital
        ×
FINAL Composition fund weight
        =
Attributed capital
```

It aggregates at Fund and AMC level while retaining Purpose breadth/dependency. It consumes authoritative Purpose capital, archived FINAL summaries, review-manifest lineage, and Fund/AMC metadata. It does not recompute FINAL, inspect candidate populations, impose concentration limits, alter winners, create substitutes, optimize family allocation, declare a dependency safe/unsafe, or introduce transition-cost assumptions.

Its structured annual outputs are:

```text
family_capital_attribution.csv
family_fund_concentration.csv
family_amc_concentration.csv
family_purpose_dependency.csv
family_attribution_manifest.json
```

The generated attribution log is forensic runtime output and is Git-ignored.

A discovered dependency is an observation. Whether the family should tolerate it is a later analytical question.

---

# 9. PURPOSE STAGING — human-in-the-loop reconciliation

Purpose Staging is a deliberately small review workspace, not an optimizer.

It lets the reviewer change:

- `value`;
- `monthly_plan`;
- `desired`;
- `due` / `analytical_horizon_years`;
- `capital_acquire_pct`; and
- `sip_acquire_pct`.

Released capital/SIP enters a common pool. Acquisition percentages apply to the same pool base at the start of the acquisition phase. The reviewer may not silently create capital or SIP by directly increasing `value` or `monthly_plan`.

Each turn records reconciliation and recalculates Achievability. The authoritative `data/purpose/purposes.csv` remains untouched until explicit COMMIT. Commit requires reviewer satisfaction and both pools equal to zero.

Purpose Staging never selects family priorities and never alters FUND, TEAM, COMPOSITION, MISSION, FINAL, or the selected FINAL Composition.

---

# 10. HISTORICAL SNAPSHOT — annual persistence boundary

Historical Snapshot is a **human-controlled Git persistence boundary**, not a separate automatic snapshot engine.

After Purpose Staging is explicitly committed, the reviewer inspects the intended annual `data/` changes and commits them to Git. The durable record includes authoritative Fund/Purpose inputs and structured annual review artifacts. Generated logs and runtime output remain disposable/Git-ignored.

The historical snapshot is:

```text
reviewed analytical state
        +
reviewed Purpose state
        +
structured annual evidence
        ↓
Git history
```

It is not a transaction ledger and does not prove what the family currently owns.

No separate `snapshot.py`, universal artifact store, or automatic transaction persistence layer is required by this architecture.

---

# 11. CURRENT → TARGET TRANSITION — separate next-stage architecture

The transition stage begins **after** the annual historical snapshot boundary. It is intentionally not a new optimizer.

Its central distinction is:

```text
ANALYTICAL CURRENT
    = what the reviewed Lakshya architecture currently says

ECONOMIC CURRENT
    = what the family actually owns at the chosen observation date

TARGET
    = what the reviewed Lakshya decisions imply the family should own
```

These states must never be conflated.

### 11.1 Analytical CURRENT

The annual review contains Purpose decisions and selected FINAL Compositions. This is evidence of the reviewed analytical architecture. It is not evidence of actual units, current value, folios, acquisition history, cost basis, or transaction constraints.

### 11.2 Economic CURRENT

Economic CURRENT is source-derived observation of actual holdings. It may include, if genuinely present in the source:

- holding/scheme identity;
- units;
- current value;
- account/folio context;
- acquisition information;
- observation date; and
- other source fields demonstrably needed by transition analysis.

Lakshya must not infer these facts from analytical outputs.

### 11.3 TARGET

TARGET is derived from already-reviewed decisions:

```text
authoritative Purpose state
        ↓
selected FINAL Composition per Purpose
        ↓
Composition fund weights
        ↓
fund-level TARGET architecture
```

Target construction does not introduce new fund-selection criteria merely because the existing holdings are inconvenient.

### 11.4 Transition reasoning

The intended relationship is:

```text
CURRENT actual holdings
        +
TARGET desired architecture
        ↓
what matches?
what can remain?
what differs?
what must change?
what constraints apply?
what sequence is feasible?
        ↓
human transition plan
```

It must not become:

```text
CURRENT
  ↓
new optimizer
  ↓
new portfolio decision
```

### 11.5 Source archaeology before schema

The first task is to inspect the actual portfolio/account material, especially the Geojit material identified for this project. Only after that inspection should the minimum sufficient CURRENT contract be defined.

The archaeology must establish what the source actually provides for:

- holding identity;
- units and current value;
- observation date;
- account/folio representation;
- acquisition/transaction information;
- cost information and granularity;
- source-authoritative versus presentation fields; and
- facts that the source does not provide.

Missing facts remain explicitly missing. Lakshya must not manufacture cost basis, acquisition dates, tax lots, exit costs, account semantics, or transaction constraints merely to complete a model.

> **Do not design the CURRENT schema from imagination when the source can tell us what it actually contains.**

### 11.6 Human execution boundary

Lakshya may calculate a transition analysis and present a feasible plan, but final redemption, purchase, switch, or reinvestment actions remain human-controlled.

The transition stage does not:

- reopen FUND admission;
- redefine TEAM formation;
- alter Composition weights because of existing holdings;
- rerun MISSION merely because a transition is inconvenient;
- replace a FINAL winner with a newly optimized fund;
- encode hidden Purpose priorities;
- equate analytical CURRENT with economic CURRENT;
- invent missing tax/cost/transaction facts; or
- execute transactions automatically.

The intended next-stage sequence is:

```text
HISTORICAL SNAPSHOT
        ↓
source archaeology
        ↓
minimum sufficient CURRENT contract
        ↓
source-derived CURRENT observation
        ↓
TARGET from existing reviewed decisions
        ↓
CURRENT vs TARGET comparison
        ↓
source-derived transition constraints / feasibility
        ↓
human transition plan
```

No production CURRENT schema, transition optimizer, tax engine, or transaction executor is authorized until the source archaeology earns the need.

---

# 12. Versioning and release discipline

The current production FINAL contract is:

```text
FINAL_CONTRACT_VERSION = 1
```

Changes to the Purpose-facing surface, percentile semantics, primary norm, spoke weighting, L-infinity elimination, bootstrap semantics, p sweep, tie-breaking, or winner meaning require a deliberate production version change.

Diagnostics that do not change the decision rule still require documentation and tests.

---

# 13. Deliberately parked concepts

Production v1 deliberately does not depend on:

- Composition regions;
- clustering;
- arbitrary k-neighbour connectivity;
- subjective Purpose scores;
- Purpose-specific spoke weights;
- synthetic maximum-Elevation/maximum-Protection targets;
- arbitrary L-infinity kill thresholds;
- fund-house narrative as an optimization input;
- future-return forecasting; or
- causal claims about why a Composition wins.

These remain experiments unless future evidence earns them and a new production version explicitly adopts them.

---

# 14. Current production architecture in one page

```text
FUND
│
├─ admission
├─ canonical NAV
├─ Elevation
└─ Protection
        │
        ▼
TEAM
│
├─ singleton / pair / trio
├─ Collective Timeline
├─ 28 Elevation + 12 Protection
└─ exact weak Pareto frontier
        │
        ▼
COMPOSITION
│
├─ Team + complete weights
├─ positive 5% grid
├─ persisted fingerprint
└─ global 40-D weak Pareto frontier
        │
        ▼
MISSION
│
├─ Purpose qualification
├─ Achievability when applicable
├─ Protection-only frontier
└─ Trajectory observation
        │
        ▼
FINAL
│
├─ Purpose-selected 7 Elevation + 12 Protection
├─ zero-variance exclusion only
├─ percentile coordinates / Utopia
├─ L2 primary ordering
├─ L∞ diagnostic + joint frontier
├─ Lp sweep
├─ leave-one-spoke sensitivity
└─ 5,000 seeded bootstrap
        │
        ▼
FAMILY ARCHITECTURE VALIDATION
│
├─ Purpose × FINAL attribution
├─ fund / AMC concentration observation
└─ Purpose dependency observation
        │
        ▼
PURPOSE STAGING
│
├─ reviewer-controlled levers
├─ capital / SIP conservation
├─ Achievability recalculation
└─ explicit COMMIT boundary
        │
        ▼
HISTORICAL SNAPSHOT
│
├─ authoritative data/
├─ structured annual evidence
└─ human Git persistence
        │
        ▼
CURRENT → TARGET
│
├─ source-derived economic CURRENT
├─ reviewed analytical TARGET
├─ transition comparison
├─ source-derived constraints
└─ human execution
```

> **We were not searching for a portfolio. We were building a road on which a portfolio could eventually be discovered.**
