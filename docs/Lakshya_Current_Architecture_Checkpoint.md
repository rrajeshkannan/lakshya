# Lakshya — Current Production Architecture Checkpoint

**Status:** Authoritative production architectural handoff

**Release:** FINAL / Compromise Programming v1

**As of:** 2026-09-06

This document supersedes older exploratory checkpoints where they conflict with the production contract below. Older checkpoints remain historical context.

---

## 1. Fundamental architecture

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

The governing principle is:

> **Information should be introduced at the layer that genuinely earns the need for it.**

For expensive evidence:

> **Compute once. Persist immediately. Reuse forever.**

The production system prioritizes analytical correctness, richness, reproducibility, interpretability and resilience over speed.

---

# 2. FUND

FUND establishes individual-fund behavioural evidence.

The principal evidence families are Elevation, Protection and Resilience.

The family source is:

```text
data/fund/funds_in_scope.csv
```

The 8-year lived-history admission rule applies only to POTENTIAL/new-entry funds. CURRENT funds may be younger and remain valid.

Regular versus Direct is not a Lakshya analytical distinction.

FUND does not know Purpose, allocation or FINAL optimization.

---

# 3. TEAM

TEAM asks:

> **What kind of collective do these teammates form?**

The current Team universe allows singleton, pair and trio structures, maximum size 3.

TEAM's declared comparative surface is:

- 28 Elevation dimensions = 4 horizons × 7 rolling measures;
- 12 Protection dimensions;
- 40 total.

Supported Elevation horizons:

```text
3Y / 5Y / 7Y / 10Y
```

Protection is native and horizon-free.

TEAM uses weak exact Pareto non-dominance. It removes only candidates dominated across the complete declared gate surface.

TEAM must not import Purpose or MISSION semantics merely to reduce its own output.

---

# 4. COMPOSITION

A Composition is:

> **Team + complete weights.**

Current positive grid:

- singleton: 100%;
- pair: 19 allocations on a 5% grid;
- trio: 171 allocations on a 5% grid.

Composition fingerprints are durable evidence containing complete Composition identity, members, weights, NAV, Elevation and Protection evidence.

The store is schema-versioned and validates identity/kind/schema. Writes are atomic and flushed before replacement.

The global Composition frontier is the weak Pareto frontier over the 40-dimensional Elevation + Protection surface.

A second identical E+P Pareto frontier over the global survivor subset is mathematically redundant and is not used as a Purpose reduction mechanism.

---

# 5. MISSION

MISSION asks:

> **Can this Composition serve this Purpose?**

Purpose is a model entity. There is no separate model category called “protected purpose”.

Open-ended Purposes can have an analytical horizon even when they have no finite target. They still receive Elevation, Protection and Trajectory analysis; only Achievability is skipped when no finite target requirement exists.

## 5.1 Purpose horizon

Canonical analytical horizons:

```text
3Y / 5Y / 7Y / 10Y
```

Rule:

> **Use the longest supported analytical horizon not beyond the Purpose horizon.**

Examples:

```text
4Y → 3Y
6Y → 5Y
8Y → 7Y
9Y → 7Y
12Y → 10Y
13Y → 10Y
```

Purpose horizon is not a demand for equivalent lived fund history.

## 5.2 MISSION gates

```text
Global Composition frontier
        ↓
Achievability when finite target exists
        ↓
Protection-only frontier
        ↓
MISSION survivors
        ↓
Purpose Trajectory observation
```

The Protection frontier is intentionally weak and operates on the native 12 Protection dimensions after Purpose qualification.

## 5.3 Trajectory

Trajectory is descriptive. It does not prune MISSION survivors.

The observation convention is:

- latest observed NAV = end;
- target start = end minus requested years;
- start = latest observation on or before target start;
- preserve the complete observed path to the latest NAV;
- normalize to the observed starting NAV.

Nominal horizon follows the canonical ladder. If a Composition lacks the nominal history, the observation layer may fall back to the next lower canonical horizon without removing the MISSION survivor or pretending that the shorter history equals the Purpose horizon.

Output preserves Purpose horizon, nominal lens, actual selected horizon and status.

---

# 6. FINAL

FINAL is the production ordering stage.

It asks:

> **Among already-qualified MISSION Compositions, which is the strongest practical compromise against the best evidence the surviving population can actually attain?**

FINAL does not reopen MISSION eligibility.

## 6.1 Purpose-facing surface

For a Purpose with selected analytical Elevation horizon `H`:

```text
7 Elevation(H) + 12 Protection
```

All retained individual spokes are equally weighted.

Protection is not assigned an artificial horizon.

If a spoke is constant across the current comparison population, it is excluded from the FINAL spoke set. If it varies, it remains.

This is deterministic population hygiene, not winner-driven pruning.

## 6.2 Current 245-population surface

The current five 245-Composition Purpose populations have:

```text
19 candidate spokes
− 1 zero-variance spoke
= 18 informative spokes
```

The zero-variance spoke is:

```text
elevation_7y_positive_period_pct
```

Retirement and future populations are evaluated independently. No Purpose inherits another Purpose's winner or spoke set.

## 6.3 Radial coordinates

Each retained native dimension is converted to a population-relative percentile coordinate in `[0,1]`.

Higher is always better:

- Elevation keeps its percentile;
- Protection reverses its percentile because lower raw severity/frequency is better.

No second normalization is performed.

## 6.4 Utopia and distance

For every retained spoke:

\[
U_j=1
\]

The Utopia Point is the unattainable combination of the best observed value on every evidence spoke.

Distance/regret is:

\[
d_{ij}=1-x_{ij}
\]

## 6.5 Primary ordering

Production winner:

\[
L_2(i)=\sqrt{\sum_j d_{ij}^2}
\]

The Composition with minimum L2 is the FINAL winner.

All retained spokes have equal weight. No subjective Purpose score is introduced.

## 6.6 Worst-spoke diagnostic

\[
L_\infty(i)=\max_j d_{ij}
\]

L-infinity is diagnostic and participates in the joint L2/L-infinity non-dominated frontier.

No arbitrary L-infinity kill threshold is used. The current 245 population did not show a defensible natural pathological boundary, so no threshold was promoted to production.

## 6.7 Robustness

FINAL records:

1. Lp sweep from 1.00 through 10.00 in 0.25 increments;
2. leave-one-spoke L2 sensitivity;
3. 5,000 deterministic population bootstrap resamples by default.

Bootstrap rebuilds the population-relative coordinate system for every resample and scores the original candidate set. It tests ordering stability, not future investment returns.

The bootstrap seed and resample count are persisted in the output.

## 6.8 Deliberately parked

Production v1 does not include:

- Composition regions;
- clustering;
- arbitrary k-neighbour connectivity;
- subjective Purpose scores;
- Purpose-specific spoke weights;
- synthetic “maximum Elevation + maximum Protection” targets;
- arbitrary L-infinity kill thresholds;
- fund-house narrative as an optimization input;
- future-return forecasting;
- causal synergy claims.

---

# 7. Production FINAL artifacts

For each Purpose:

```text
output/final_<Purpose>_axes.csv
output/final_<Purpose>_signatures.csv
output/final_<Purpose>_distances.csv
output/final_<Purpose>_results.csv
output/final_<Purpose>_lnorm_sweep.csv
output/final_<Purpose>_leave_one_spoke.csv
output/final_<Purpose>_bootstrap.csv
output/final_<Purpose>_joint_l2_linf_frontier.csv
output/final_<Purpose>_summary.csv
```

The summary is the compact hand-off; the remaining files preserve the full audit trail.

---

# 8. Versioning and release discipline

The FINAL contract is:

```text
FINAL_CONTRACT_VERSION = 1
```

A future change to the Purpose surface, percentile semantics, primary norm, weighting, L-infinity elimination, bootstrap semantics or tie-breaking requires a deliberate production version change and corresponding tests/documentation.

Exploration may continue. Production behaviour changes only through an explicit next release.

---

# 9. Production execution invariant

Every stage follows:

```text
compute → persist → validate → consume
```

A downstream FINAL change does not invalidate upstream Composition fingerprints unless the upstream evidence contract itself changes.

The architecture therefore supports agile evolution without sacrificing reproducibility.
