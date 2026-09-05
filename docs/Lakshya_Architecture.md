# Lakshya Production Architecture

**Status:** Authoritative production architecture

**Release:** FINAL / Compromise Programming v1

**As of:** 2026-09-06

This is the single architecture document for the current Lakshya system. It consolidates the earlier architecture checkpoints and the Fund/Team behavioural-fingerprint documentation into one durable description of the architecture, evidence boundaries, contracts, and production invariants.

The companion `docs/Lakshya_Pipeline_Sequence.md` describes **how the system executes**. This document describes **what the stages mean and what each stage is allowed to own and consume**.

---

# 1. Architectural statement

Lakshya is a family-oriented investment analysis architecture whose job is to earn a portfolio decision through progressively higher-order evidence.

The production architecture is:

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

Each stage asks a different question:

| Stage | Question | Nature |
|---|---|---|
| FUND | What kind of teammate is this fund? | individual behavioural evidence |
| TEAM | What kind of collective do these teammates form? | structural collective evidence |
| COMPOSITION | Where does capital sit within a collective? | allocation geometry |
| MISSION | Can this Composition serve this Purpose? | Purpose-specific qualification |
| FINAL | Among qualified Compositions, which is the strongest practical compromise? | production ordering |

The architecture deliberately separates **evidence construction**, **eligibility/elimination**, and **ordering**.

> **Information should be introduced at the layer that genuinely earns the need for it.**

For expensive evidence:

> **Compute once. Persist immediately. Reuse forever.**

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

# 8. Why FINAL is not another Pareto stage

Pareto elimination asks:

> **Can this candidate be shown to be strictly inferior across all declared dimensions?**

FINAL asks:

> **Among candidates that remain genuinely trade-off-rich, which is closest to the best attainable balance?**

The current 245-composition 7Y population is a concrete example: pure Pareto comparison in the distance-space leaves all 245 non-dominated.

Therefore the architecture transitions legitimately from **elimination** to **ordering**.

---

# 9. Current analytical population checkpoint

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

# 10. Production persistence and resume model

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

---

# 11. Versioning and release discipline

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
- changing tie-breaking;
- changing the meaning of the winner.

Adding a diagnostic that does not change the decision rule may not require a contract-version change, but must still be documented and tested.

---

# 12. Deliberately parked concepts

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

# 13. Current production architecture in one page

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
```

The architectural journey is therefore:

> **We were not searching for a portfolio. We were building a road on which a portfolio could eventually be discovered.**
