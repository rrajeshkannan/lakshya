# Lakshya Production Architecture

**Status:** Authoritative production architecture

**Release:** FINAL / Compromise Programming v1

**As of:** 2026-09-06

This is the single architecture document for the current Lakshya system. It describes the analytical stages, the post-FINAL family-level observation layer, the human-controlled Purpose Staging layer, the annual historical snapshot boundary, evidence contracts, and production invariants.

The companion `docs/Lakshya_Pipeline_Sequence.md` describes **how the system executes**. This document describes **what the stages mean and what each stage is allowed to own and consume**.

The detailed `docs/Lakshya_Family_Architecture_Validation.md` and `docs/Lakshya_Purpose_Staging.md` remain companion implementation/operational guides. They are not separate competing architectures.

---

# 1. Architectural statement

Lakshya is a family-oriented investment analysis architecture whose job is to earn a portfolio decision through progressively higher-order evidence, then make the family-level consequence visible and provide a controlled human reconciliation workspace before the separate CURRENT → TARGET transition.

The analytical production architecture is:

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
CURRENT → TARGET TRANSITION   [separate next-stage architecture]
```

Each analytical stage asks a different question:

| Stage | Question | Nature |
|---|---|---|
| FUND | What kind of teammate is this fund? | individual behavioural evidence |
| TEAM | What kind of collective do these teammates form? | structural collective evidence |
| COMPOSITION | Where does capital sit within a collective? | allocation geometry |
| MISSION | Can this Composition serve this Purpose? | Purpose-specific qualification |
| FINAL | Among qualified Compositions, which is the strongest practical compromise? | production ordering |
| FAMILY ARCHITECTURE VALIDATION | What family-level concentration/dependency consequence follows from the independently derived Purpose decisions? | attribution / observation |
| PURPOSE STAGING | What happens if the reviewer changes Purpose levers and redistributes released capital/SIP? | human-in-loop reconciliation |
| HISTORICAL SNAPSHOT | What should become durable annual memory? | versioned persistence |

The architecture deliberately separates **evidence construction**, **eligibility/elimination**, **ordering**, **family-level observation**, and **human-controlled reconciliation**.

> **Information should be introduced at the layer that genuinely earns the need for it.**

For expensive evidence:

> **Compute once. Persist immediately. Reuse forever.**

The final transaction transition is deliberately outside this architecture's automatic decision path. Lakshya does not automatically execute redemption or reinvestment.

---

# 2. Cross-stage evidence discipline

Lakshya follows these production invariants:

1. **Observed is not inferred.**
2. **Unknown is not zero.**
3. A Purpose horizon is not a demand for equivalent lived fund history.
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

The preferred lifecycle is:

```text
compute → persist → validate → consume
```

---

# 3. FUND — individual behavioural entity

## 3.1 FUND responsibility

FUND understands an individual Fund as a **behavioural entity**, not merely a collection of return and risk statistics.

Its question is:

> **What kind of teammate is this fund?**

The Fund stage is descriptive, not prescriptive. It establishes the individual behavioural evidence from which later collective reasoning may consume selected information.

The principal Fund evidence families are:

```text
Elevation
Protection
Resilience
```

Evidence quality is a guardrail around interpretation, not a fourth behavioural dimension.

## 3.2 Fund admission

The explicit family source is:

```text
data/fund/funds_in_scope.csv
```

The 8-year lived-history admission rule applies to **POTENTIAL/new-entry** Funds. CURRENT Funds may be younger and remain valid.

`CURRENT` and `POTENTIAL` are admission-stage concepts. Once a Fund is admitted, they do not become hidden downstream behavioural preferences.

Regular versus Direct is not a Lakshya analytical distinction.

## 3.3 Fund evidence foundation

The Fund evidence foundation follows:

```text
Fund admission
      ↓
canonical NAV evidence
      ↓
rolling windows / drawdown episodes
      ↓
Fund evidence
      ↓
Fund Behavioural Fingerprint
```

The preferred analytical direction is:

```text
DAILY OBSERVATIONS
       ↓
ROLLING WINDOWS / EPISODES
       ↓
DISTRIBUTIONS / SUMMARIES
       ↓
FUND COMPASS
```

rather than:

```text
DAILY OBSERVATIONS
       ↓
ONE SCORE
       ↓
DECISION
```

Fund fingerprints are version-linked to their NAV evidence. A fingerprint state ahead of its source NAV evidence is invalid lineage. Historical analytical states are preserved rather than silently overwritten.

The current fingerprint implementation recalculates from the complete persisted NAV history for each analytical snapshot; it is not an incremental/delta fingerprint calculation.

## 3.4 Fund Compass

### Elevation

Question:

> **How has this fund participated in prosperity across different investment horizons?**

Elevation is observed through rolling-return distributions across available horizons:

```text
3Y / 5Y / 7Y / 10Y
```

The core rolling measures used downstream are:

```text
minimum
P25
median
P75
maximum
mean
positive-period frequency
```

The richer Fund evidence may also preserve standard deviation, negative-period frequency and latest observed rolling return where available.

Elevation describes historical prosperity terrain. It is not a forecast and is not proof of future superiority or suitability.

### Protection

Question:

> **How severe is the adversity when it happens?**

Protection measures drawdown severity relative to the Fund's own previous high-water mark.

The native Protection surface contains:

**Severity distribution**

```text
median severity
P75
P90
P95
P99
maximum severity
```

**Terrain frequency**

```text
% observations at or beyond 5%
% observations at or beyond 10%
% observations at or beyond 15%
% observations at or beyond 20%
% observations at or beyond 25%
% observations at or beyond 30%
```

These are behavioural landmarks, not universal definitions of acceptable adversity.

Protection describes severity terrain. It does not describe the recovery journey.

### Resilience

Question:

> **What happens to the capital after adversity begins?**

Resilience is observed through individual drawdown episodes:

```text
high-water mark
       ↓
     decline
       ↓
     trough
       ↓
    recovery
       ↓
high-water mark restored
```

Episode evidence distinguishes:

- decline duration;
- recovery duration when actually observed;
- underwater duration;
- episode state (`recovered` / `ongoing`); and
- episode-level depth and timing.

An ongoing episode has unknown recovery duration; unknown is not zero and is not estimated.

Resilience therefore remains analytically distinct from Protection.

## 3.5 Supporting Fund evidence

Supporting evidence may deepen interpretation without automatically becoming a new Compass dimension. Examples include downside RMS and individual episode records.

Optional narrower lenses such as benchmark-relative capture, Sortino or Calmar do not redefine intrinsic Fund behaviour.

> **A benchmark is an analytical lens, not an intrinsic property of the fund.**

## 3.6 FUND boundary

FUND owns:

- Fund admission;
- canonical NAV evidence;
- Fund behavioural calculations;
- Fund Behavioural Fingerprint construction;
- fingerprint version and lineage;
- evidence persistence; and
- Fund-level Compass views.

FUND does not own:

- Team formation;
- collective judgement;
- Purpose suitability;
- portfolio composition;
- allocation per Purpose;
- MISSION decisions; or
- FINAL optimization.

A calculated Fund metric does not automatically cross the boundary.

---

# 4. TEAM — collective behavioural entity

## 4.1 TEAM responsibility

TEAM asks:

> **What kind of collective do these teammates form?**

TEAM is descriptive, not prescriptive. It establishes non-dominated collective structures under its own declared behavioural gate; it does not determine what the family should own or how a Purpose should be funded.

## 4.2 Team formation

The current Team universe contains:

- singleton Teams;
- pair Teams; and
- trio Teams.

Maximum Team size is **3 members**.

Candidate generation is deterministic.

The combinatorial universe belongs to TEAM. Higher-order MISSION semantics must not be imported merely to make TEAM smaller.

## 4.3 Collective evidence

A Team is not defined by combining already-compressed Fund scores.

The intended flow is:

```text
admitted Fund histories
        ↓
Team candidate
        ↓
collective NAV
        ↓
collective behavioural evidence
        ↓
Team Behavioural Fingerprint
```

The collective evidence preserves enough resolution to support both summary interpretation and deeper audit.

## 4.4 TEAM comparator surface

TEAM's declared comparative surface contains **40 dimensions**:

```text
28 Elevation
12 Protection
----------------
40 total
```

Elevation consists of:

```text
4 rolling horizons × 7 rolling measures
```

with horizons:

```text
3Y / 5Y / 7Y / 10Y
```

and measures:

```text
minimum
P25
median
P75
maximum
mean
positive-period frequency
```

Protection contributes the same native 12-dimensional severity/frequency surface described at FUND.

Protection is horizon-free in the native model.

## 4.5 Resilience boundary discovery

Fund-level Resilience exists, but it is **not currently part of the TEAM comparator gate**.

That exclusion is deliberate and architectural:

> **A lower-stage calculation does not automatically become a higher-stage input.**

TEAM has not earned a requirement to use Fund Resilience for its collective frontier. The underlying Fund evidence remains meaningful and available for later interpretation.

## 4.6 TEAM frontier

TEAM uses weak exact Pareto non-dominance over the complete declared 40-dimensional surface.

A candidate is removed only when another candidate is at least as good in every declared dimension and strictly better in at least one, using the declared directional semantics:

```text
Elevation  → UP
Protection → DOWN
```

This is an elimination rule, not a weighted ranking.

A Team can remain because of a genuine trade-off between dimensions.

The current implementation uses a streaming frontier approach for memory-conscious processing of potentially large candidate universes without changing the dominance semantics.

## 4.7 TEAM boundary

TEAM owns:

- Team candidate formation;
- collective behavioural evidence construction;
- Team Behavioural Fingerprint construction;
- the declared 40-D comparator surface;
- explicit unavailable-evidence handling;
- exact non-dominated frontier calculation; and
- TEAM orchestration.

TEAM does not own:

- Fund Admission;
- family Purpose;
- goal suitability;
- portfolio allocation;
- MISSION decisions; or
- FINAL optimization.

The key architectural boundary is:

> **TEAM must not decide what MISSION wants.**

---

# 5. COMPOSITION — capital allocation inside a collective

## 5.1 COMPOSITION responsibility

COMPOSITION asks:

> **Where does capital sit within a Team?**

A Composition is:

> **Team + complete weights.**

## 5.2 Candidate grid

The current positive weight grid is:

```text
singleton: 100%
pair:       19 allocations at 5% increments
trio:      171 allocations at 5% increments
```

The Composition universe therefore preserves allocation geometry rather than reducing a Team to a single fixed recipe.

## 5.3 Composition fingerprint

Composition fingerprints are durable, reusable evidence.

The fingerprint contains the complete Composition identity, members, weights and downstream evidence including NAV, Elevation and Protection.

The fingerprint store provides:

- stable identity-based paths;
- schema and kind validation;
- atomic writes;
- `fsync` before replacement; and
- lossless rehydration.

A downstream algorithm change must not trigger recomputation merely because the consumer changed.

## 5.4 Global Composition frontier

The global Composition frontier uses the same 40-dimensional Elevation + Protection surface and weak Pareto non-dominance.

A second identical 40-dimensional Pareto frontier over the global survivor subset is mathematically redundant. Purpose-specific reduction therefore begins from Purpose requirements rather than repeating the same gate merely to force another reduction.

## 5.5 COMPOSITION boundary

COMPOSITION owns:

- complete Team weight allocations;
- Composition identity;
- Composition behavioural evidence;
- Composition fingerprint persistence; and
- the global Composition frontier.

COMPOSITION does not decide Purpose suitability.

---

# 6. MISSION — Purpose-specific qualification

## 6.1 MISSION responsibility

MISSION asks:

> **Can this Composition serve this Purpose?**

MISSION is the first stage where Purpose semantics enter the analytical contract.

There is only the model entity **Purpose**; there is no separate “protected purpose” category.

## 6.2 Purpose types

A Purpose may have:

- a finite target and horizon; or
- no finite target/deadline but an explicit analytical horizon for open-ended analysis.

Open-ended Purposes still receive Elevation, Protection and Trajectory analysis. Only Achievability is skipped when there is no finite target requirement.

## 6.3 Purpose horizon

The supported analytical horizon ladder is:

```text
3Y / 5Y / 7Y / 10Y
```

The canonical rule is:

> **Use the longest supported analytical horizon not beyond the Purpose horizon.**

Examples:

```text
4Y  → 3Y
6Y  → 5Y
8Y  → 7Y
9Y  → 7Y
12Y → 10Y
13Y → 10Y
```

The Purpose horizon never becomes a requirement for equivalent lived history from every Fund or Composition.

## 6.4 MISSION sequence

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

Achievability is purpose-specific. The Protection frontier is intentionally Protection-only and weakly non-dominated after the Purpose qualification step.

## 6.5 Trajectory

Trajectory is descriptive and does not remove a MISSION survivor in the current architecture.

The observation convention is:

```text
latest observed NAV = end
requested target start = end - requested years
actual start = latest observation on/before target start
preserve all observations through latest
normalize relative to actual start NAV
```

The output preserves:

- Purpose horizon;
- nominal analytical horizon;
- actual selected observation horizon; and
- status.

A nominal horizon that cannot be supported by the available lived history may fall back to the next lower supported analytical horizon. The shorter observation must not be presented as if it equals the Purpose horizon.

## 6.6 MISSION boundary

MISSION owns Purpose qualification and Purpose-facing interpretation of eligible Compositions.

MISSION does not silently redefine the global Composition evidence contract.

---

# 7. FINAL — production ordering

## 7.1 FINAL responsibility

FINAL asks:

> **Among already-qualified MISSION Compositions, which is the strongest practical compromise against the best evidence the surviving population can actually attain?**

FINAL is an **ordering stage**, not another admission stage.

It does not reopen FUND, TEAM, COMPOSITION or MISSION eligibility.

## 7.2 Purpose-facing surface

For each Purpose, FINAL constructs a common comparison surface from the Purpose's MISSION survivor population:

```text
7 Elevation dimensions at the Purpose-selected horizon
+
12 native Protection dimensions
```

All retained individual spokes are equally weighted.

Protection receives no artificial horizon.

A spoke is excluded from FINAL **only when it has zero variance across the current comparison population**.

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

If a future population varies on that spoke, it returns automatically.

## 7.3 Population-relative radial coordinates

For every retained spoke, raw values are converted to a population-relative percentile coordinate in `[0,1]`.

Higher coordinate always means better evidence:

- Elevation retains its percentile direction;
- Protection reverses its percentile direction because lower severity/frequency is better.

No second normalization is performed.

## 7.4 Utopia Point and distance shape

For each retained spoke:

\[
U_j=1
\]

The Utopia Point is the unattainable combination formed by the best observed value on every retained evidence spoke.

For Composition `i`:

\[
d_{ij}=1-x_{ij}
\]

The vector `d_i` is the Composition's distance-shape from the population-relative attainable best.

## 7.5 Primary compromise ordering

FINAL uses unweighted Euclidean distance:

\[
L_2(i)=\sqrt{\sum_j d_{ij}^{2}}
\]

The smallest L2 distance is the production winner.

Equal spoke weighting is intentional.

L2 is not exponential. Squaring makes larger regrets disproportionately influential, but remains a polynomial norm.

## 7.6 L-infinity diagnostic

The worst-spoke distance is:

\[
L_\infty(i)=\max_j d_{ij}
\]

L-infinity is retained because catastrophic weakness in one evidence dimension matters analytically.

However, FINAL does not impose an arbitrary threshold.

The production rule is:

> **Inspect the worst dimension; promote L-infinity to elimination only when the population itself provides a defensible, reproducible boundary. Otherwise retain it as a diagnostic and joint-objective view.**

The current 245 population did not provide such a natural boundary.

## 7.7 Joint L2/L-infinity frontier

FINAL also computes the non-dominated set when minimizing:

```text
(L2, L-infinity)
```

This preserves the trade-off between total compromise distance and worst single-spoke weakness.

## 7.8 Lp robustness

FINAL sweeps:

```text
p = 1.00, 1.25, 1.50, …, 10.00
```

and records the winner at each p.

The purpose is sensitivity analysis: whether the primary L2 winner occupies a broad compromise regime or exists only under a narrow formulation.

## 7.9 Leave-one-spoke sensitivity

Each informative spoke is removed once and the L2 ordering is recomputed.

This identifies dependence on any single evidence dimension without silently changing the production surface.

## 7.10 Population bootstrap

By default FINAL performs:

- sampling with replacement;
- population size equal to the current survivor population;
- deterministic seeded resampling;
- 5,000 resamples.

Each resample rebuilds the population-relative coordinate system and rescales the original candidate set in that bootstrap population before rescoring.

Bootstrap measures **ordering stability**, not future returns and not causal fund synergy.

The seed and resample count are persisted.

## 7.11 FINAL production rule

The production winner is the minimum-L2 Composition in the Purpose's current MISSION survivor population.

Robustness outputs do not override the primary definition. They describe stability around it.

Any future change to the FINAL decision rule requires a deliberate production contract version.

---

# 8. FAMILY ARCHITECTURE VALIDATION — family-level observation

Family Architecture Validation runs **after FINAL has been archived**. It exists because independently derived Purpose-level FINAL decisions can create a common family dependency. The layer makes that consequence visible without changing any upstream decision.

Its question is:

> **Given those Purpose-level decisions together, where does family capital depend on common funds or investment organizations?**

This is **attribution, not optimization**.

## 8.1 Inputs

The layer consumes only already-earned production information:

```text
data/purpose/purposes.csv
        ↓
Purpose current capital (`value`)


data/reviews/<as_of>/<Purpose>_summary.csv
        ↓
archived FINAL primary winner


data/reviews/<as_of>/review_manifest.json
        ↓
archive integrity and lineage verification


data/fund/funds_in_scope_metadata.csv
        ↓
fund and AMC identity
```

The dated FINAL archive is authoritative for the selected Composition. Family validation does not recompute FINAL and does not consume candidate populations.

## 8.2 Attribution contract

For each Purpose:

```text
Purpose current capital
        ×
FINAL Composition fund weight
        =
Attributed capital
```

Across the family:

```text
Fund attributed capital
        ↓
Fund concentration

Fund attributed capital
        ↓
AMC aggregation
        ↓
AMC / ecosystem concentration
```

Purpose breadth is retained alongside capital concentration so a common dependency can be seen both by amount and by number of Purposes affected.

## 8.3 Outputs

Each review produces under `data/reviews/<as_of>/`:

```text
family_capital_attribution.csv
family_fund_concentration.csv
family_amc_concentration.csv
family_purpose_dependency.csv
family_attribution_manifest.json
family_attribution.log
```

The structured CSV/manifest outputs are canonical review artifacts. `family_attribution.log` is a forensic execution log and is Git-ignored.

## 8.4 Deliberate non-responsibilities

Family Architecture Validation v1 does **not**:

- impose a maximum fund concentration;
- impose a maximum AMC concentration;
- penalize common dependencies;
- alter FINAL winners;
- create substitute Compositions;
- optimize family-level allocations;
- declare a concentration safe or unsafe; or
- introduce transition-cost assumptions.

A discovered dependency is an observation. Whether the family should tolerate it is a subsequent analytical question.

## 8.5 Integrity contract

The implementation fails closed when:

1. Purpose capital is missing, duplicated, negative, or non-positive in aggregate;
2. fund metadata has missing required identity fields or duplicate ISINs;
3. a FINAL Composition identity is malformed or does not sum to 100%;
4. a FINAL winner references an unknown fund ISIN;
5. the archived FINAL manifest does not match the requested Purpose set;
6. an archived FINAL summary hash does not match its manifest; or
7. Purpose-level attributed capital does not reconcile to the Purpose capital.

The output writes are atomic.

Family validation is independently rerunnable without recomputing the analytical chain.

---

# 9. PURPOSE STAGING — human-in-the-loop reconciliation

Purpose Staging begins only after the family-level observation has been reviewed. It is a human-in-the-loop reconciliation workspace, not an optimizer.

Its question is:

> **Given what the family has just observed, what happens to Purpose Achievability if the reviewer changes Purpose levers and redistributes released capital or SIP?**

Purpose Staging does **not** alter FUND, TEAM, COMPOSITION, MISSION, FINAL, or the selected FINAL Composition.

## 9.1 Reviewer controls

The staged Purpose retains the four Purpose controls already present in `purposes.csv`:

- `value` — current capital;
- `monthly_plan` — monthly contribution;
- `desired` — target;
- `due` / `analytical_horizon_years` — Purpose horizon.

A turn may also contain:

- `capital_acquire_pct` — percentage of the currently available capital pool to acquire for that Purpose;
- `sip_acquire_pct` — percentage of the currently available monthly-SIP pool to acquire for that Purpose.

Acquisition percentages are reviewer instructions for that turn. They are not stored as family priorities and do not teach Lakshya any Purpose ranking.

## 9.2 Conservation contract

The staged accounting follows:

```text
Purpose value reduction  → capital pool
Purpose SIP reduction    → SIP pool
pool acquisition         → another Purpose
```

A reviewer may not silently create capital or SIP by increasing `value` or `monthly_plan`. Increases are funded through the common-pool acquisition instruction.

Changes to `desired` or horizon alter the Purpose requirement and therefore its Achievability result. They do not by themselves manufacture a cash release.

Acquisition percentages apply to the **same pool available at the start of the acquisition phase** for that turn. They are not applied sequentially to a shrinking pool.

Any unallocated pool remains in the staging workspace for the next turn.

## 9.3 Lifecycle

The lifecycle is:

```text
authoritative purposes.csv
        ↓ INIT
staged purposes
        ↓ reviewer turn
release → pool → acquire
        ↓
Achievability + reconciliation
        ↓
reviewer pause
        ↓
repeat as required
        ↓
SATISFIED + pools zero
        ↓ COMMIT
updated authoritative purposes.csv
```

The authoritative Purpose file is untouched until explicit COMMIT.

## 9.4 Staging workspace

The review workspace is:

```text
data/reviews/<as-of>/purpose_staging/
```

with:

```text
purposes_staged.csv
reconciliation_ledger.csv
achievability_latest.csv
staging_state.json
staging.log
```

The structured staging state is retained as review evidence. `staging.log` is a forensic execution log and is Git-ignored.

## 9.5 Commit boundary

Commit is permitted only when:

- the reviewer is satisfied;
- `pool_capital = 0`; and
- `pool_monthly_sip = 0`.

Before promotion, the authoritative source is backed up as `purposes_before_commit.csv` in the staging workspace. The staged file is then promoted to `data/purpose/purposes.csv`.

Purpose Staging never selects the family's priority. The reviewer controls the terrain; Lakshya calculates the consequences.

---

# 10. HISTORICAL SNAPSHOT — annual persistence boundary

After Purpose Staging is explicitly committed, the annual review reaches its persistence boundary.

The durable annual record is the deliberate, non-gitignored state under `data/`, especially:

```text
data/fund/                  authoritative Fund scope/input

data/purpose/               authoritative Purpose input

data/reviews/<as-of>/      structured annual review artifacts
```

The runtime distinction is:

| Material | Persistence role |
|---|---|
| `data/fund/` authoritative inputs | durable, version-controlled |
| `data/purpose/` authoritative inputs | durable, version-controlled |
| `data/reviews/<as-of>/` structured annual artifacts | durable, version-controlled |
| `data/reviews/<as-of>/purpose_staging/` structured staging state | durable, version-controlled |
| `staging.log` | generated forensic log, Git-ignored |
| `family_attribution.log` | generated forensic log, Git-ignored |
| `output/` | disposable/regenerable runtime area |

The annual snapshot is a historical record, not a transaction ledger and not an automatic trading instruction.

## 10.1 Human persistence boundary

The reviewer deliberately inspects the annual changes before committing them:

```text
git status --short
        ↓
review intended data/ changes
        ↓
git add only intended annual-review changes
        ↓
git status --short
        ↓
git commit
        ↓
future annual review can recover prior state
```

Generated runtime logs and runtime output remain disposable.

This is the durable historical snapshot point for the annual cycle.

---

# 11. Why FINAL is not another Pareto stage

Pareto elimination asks:

> **Can this candidate be shown to be strictly inferior across all declared dimensions?**

FINAL asks:

> **Among candidates that remain genuinely trade-off-rich, which is closest to the best attainable balance?**

The current 245-composition 7Y population is a concrete example: pure Pareto comparison in the distance-space leaves all 245 non-dominated.

Therefore the architecture transitions legitimately from **elimination** to **ordering**.

---

# 12. Current analytical population checkpoint

The current experimental population relevant to the FINAL 7Y comparison is **245 unique Compositions**, not the broader historical 36,665 global survivor count.

Across the five current 245-Composition Purposes:

- the same 245 Composition identities are reused;
- Retirement selects a distinct subset of 36 Compositions;
- the other five current Purpose populations each contain the full 245.

The five full 245 populations are:

```text
Edu_B
Home_Loan
Kutti
Marriage
Stitch
```

Retirement is a 36-Composition subset in the current experiment.

This distinction matters because FINAL compares each Purpose's own survivor population. It must not silently widen that population to the historical global universe.

---

# 13. Production persistence and resume model

For durable evidence, the intended sequence is:

```text
load
  ↓
validate
  ↓
reuse valid evidence
  ↓
compute only missing/stale evidence
  ↓
atomic persist
  ↓
validate
  ↓
consume
```

A downstream algorithm change does not invalidate a valid upstream evidence artifact merely because a new consumer exists.

The architecture therefore supports future FINAL releases against the same valid MISSION/Composition evidence without unnecessary upstream reconstruction.

A downstream failure must not invalidate upstream evidence that remains valid.

---

# 14. Versioning and release discipline

The current production FINAL contract is:

```text
FINAL_CONTRACT_VERSION = 1
```

The following changes require a new deliberate production version:

- changing the Purpose-facing surface;
- changing percentile semantics;
- changing the primary norm;
- introducing subjective spoke weights;
- introducing an L-infinity elimination threshold;
- changing bootstrap semantics;
- changing the p sweep;
- changing tie-breaking; or
- changing the meaning of the winner.

Adding a diagnostic that does not change the decision rule may not require a contract-version change, but must still be documented and tested.

---

# 15. Deliberately parked concepts

Production v1 deliberately does not depend on:

- Composition regions;
- clustering;
- arbitrary k-neighbour connectivity;
- subjective Purpose scores;
- Purpose-specific spoke weights;
- synthetic “maximum Elevation + maximum Protection” targets;
- arbitrary L-infinity kill thresholds;
- fund-house narrative as an optimization input;
- future-return forecasting; or
- causal claims about why a Composition wins.

These remain experiments unless future evidence earns them and a new production version explicitly adopts them.

---

# 16. Current production architecture in one page

```text
FUND
│
├─ admission
├─ NAV evidence
├─ Elevation
├─ Protection
└─ Resilience
        │
        │ selected evidence crosses only when earned
        ▼
TEAM
│
├─ singleton / pair / trio
├─ collective NAV / evidence
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
├─ Purpose
├─ Achievability when finite target exists
├─ Protection-only frontier
└─ Trajectory observation
        │
        ▼
FINAL
│
├─ 7 Elevation(H) + 12 Protection
├─ remove zero-variance spokes only
├─ population-relative radial coordinates
├─ Utopia / distance-shape
├─ L2 primary winner
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
├─ reviewer-controlled Purpose levers
├─ capital / SIP conservation
├─ Achievability recalculation
└─ explicit COMMIT boundary
        │
        ▼
HISTORICAL SNAPSHOT
│
├─ authoritative data/
├─ structured annual review artifacts
└─ Git persistence
        │
        ▼
CURRENT → TARGET TRANSITION
[separate next-stage architecture]
```

The architectural journey is therefore:

> **We were not searching for a portfolio. We were building a road on which a portfolio could eventually be discovered.**
