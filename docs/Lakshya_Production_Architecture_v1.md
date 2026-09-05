# Lakshya Production Architecture v1

**Status:** Production specification

**Release:** FINAL / Compromise Programming v1

**Purpose:** Freeze the current Lakshya architecture as an executable, testable production contract while preserving the ability to evolve it through a later versioned release.

---

## 1. Architectural statement

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
| FUND | What kind of teammate is this fund? | descriptive evidence |
| TEAM | What kind of collective do these teammates form? | structural evidence |
| COMPOSITION | Where does capital sit within a collective? | allocation evidence |
| MISSION | Is the Composition suitable for a Purpose? | purpose-specific qualification |
| FINAL | Among qualified Compositions, which is the strongest practical compromise? | production ordering |

The architecture deliberately separates **elimination** from **ordering**.

Earlier stages remove candidates only when the declared evidence establishes a valid non-dominance or Purpose gate. FINAL then orders the survivors rather than pretending that every trade-off can be eliminated by another Pareto pass.

> **The system earns the right to optimize only after the evidence system has earned the right to survive.**

---

## 2. Evidence discipline

Lakshya follows these production invariants:

1. Observed is not inferred.
2. Unknown is not zero.
3. A Purpose horizon is not a demand for equivalent lived fund history.
4. A calculation does not automatically become a downstream input.
5. Persisted evidence is reused rather than silently recomputed.
6. A higher stage consumes only information whose semantic need it has earned.
7. Experimental exploration may discover a rule; a production release must codify the rule explicitly.
8. A later release may change a production rule, but it must do so as a deliberate version change rather than by silent drift.

The implementation preference remains:

```text
compute → persist → validate → consume
```

---

# 3. FUND

## 3.1 Responsibility

FUND establishes the observed behavioural character of each individual fund.

The core behavioural families are:

- Elevation
- Protection
- Resilience

FUND is descriptive. It does not decide Purpose suitability and does not know how a fund will be allocated inside a Composition.

## 3.2 Admission

`data/fund/funds_in_scope.csv` is the explicit family source.

The 8-year lived-history admission rule applies to **POTENTIAL/new-entry** funds. It does not invalidate an existing CURRENT fund merely because the fund is younger.

Regular versus Direct is not a Lakshya analytical distinction.

## 3.3 Boundary

FUND must not import:

- Purpose semantics;
- target corpus;
- allocation percentages;
- MISSION decisions; or
- FINAL optimization.

FUND owns the evidence from which later stages may earn selected consumption.

---

# 4. TEAM

## 4.1 Responsibility

TEAM asks:

> **Who stands together?**

It constructs collective behavioural evidence from admitted Funds.

The Team universe permits singleton, pair and trio structures, with a maximum Team size of three.

## 4.2 Gate surface

TEAM's declared comparative gate surface is 40 dimensions:

- 28 Elevation dimensions = 4 rolling horizons × 7 rolling measures;
- 12 Protection dimensions = severity-distribution and threshold-frequency measures.

The seven rolling measures are:

```text
minimum
percentile_25
median
percentile_75
maximum
mean
positive_period_pct
```

Supported rolling horizons are:

```text
3Y, 5Y, 7Y, 10Y
```

Protection has no artificial horizon in the native model.

Resilience remains Fund-level evidence unless a later architecture explicitly earns it at TEAM.

## 4.3 Frontier rule

TEAM uses weak Pareto non-dominance under the declared direction of each metric.

A candidate is removed only when another candidate is at least as good on every declared TEAM gate dimension and strictly better on at least one.

TEAM does not use Purpose information to manufacture a smaller Team universe.

---

# 5. COMPOSITION

## 5.1 Responsibility

COMPOSITION asks:

> **Where does capital sit within a Team?**

A Composition is a Team plus complete weights.

The production candidate grid is:

- singleton: 100%;
- pair: 19 allocations on a 5% grid;
- trio: 171 allocations on a 5% grid.

Composition fingerprints are persisted because they are expensive, reusable evidence.

## 5.2 Fingerprint persistence

The production Composition fingerprint store provides:

- stable identity-based paths;
- schema and kind validation;
- atomic writes;
- `fsync` before replacement;
- lossless rehydration;
- explicit schema versioning.

The fingerprint contains the full Composition identity and the evidence needed downstream, including NAV, Elevation and Protection evidence.

A downstream change must not trigger recomputation merely because the consumer changed.

## 5.3 Global frontier

The global Composition frontier uses the same 40-dimensional Elevation + Protection surface and weak Pareto non-dominance.

A Purpose-specific repeat of the identical 40-dimensional frontier is mathematically redundant when it is applied only to global survivors. Purpose-specific reduction therefore begins with the Purpose gates rather than pretending that the same global frontier can prune again.

---

# 6. MISSION

## 6.1 Responsibility

MISSION asks:

> **What must this collective accomplish for a particular Purpose?**

MISSION is the first stage where Purpose semantics enter.

A Purpose may have:

- a finite target and horizon; or
- no finite target/deadline but an explicit analytical horizon for open-ended analysis.

Open-ended Purposes still receive Elevation, Protection and Trajectory analysis. Only Achievability is absent when there is no finite target requirement.

## 6.2 Purpose horizon

The supported analytical horizon ladder is:

```text
3Y, 5Y, 7Y, 10Y
```

The canonical rule is:

> **Use the longest supported analytical horizon not beyond the Purpose horizon.**

Examples:

| Purpose horizon | analytical horizon |
|---:|---:|
| 4Y | 3Y |
| 6Y | 5Y |
| 8Y | 7Y |
| 9Y | 7Y |
| 12Y | 10Y |
| 13Y | 10Y |

A Purpose horizon is never converted into a requirement that every Fund or Composition must have lived history of exactly that duration.

## 6.3 MISSION gates

The production MISSION sequence is:

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

Trajectory observation is descriptive and preserves the actual selected observation horizon and status.

The lower-level trajectory convention remains:

- latest observed NAV is the end;
- requested target start is end minus requested years;
- start is the latest observation on or before that target;
- all observations to the latest date are retained;
- normalized NAV is relative to the observed start NAV.

---

# 7. FINAL

## 7.1 Responsibility

FINAL answers:

> **Among already-qualified MISSION Compositions, which is the strongest practical compromise against the best evidence the surviving population can actually attain?**

FINAL does not reopen FUND, TEAM, COMPOSITION or MISSION eligibility.

It is an ordering stage, not a new admission stage.

## 7.2 Purpose-facing comparison surface

For each Purpose, FINAL constructs a common radial comparison surface from the MISSION survivor population.

The candidate surface is:

```text
7 Elevation dimensions at the Purpose-selected analytical horizon
+
12 native Protection dimensions
```

All individual spokes are treated equally. No subjective Purpose weight is applied.

Protection is not assigned an artificial horizon because the native Protection evidence has no horizon.

## 7.3 Zero-variance dimensions

A dimension is excluded from the FINAL spoke set **only when it has zero variance across the current comparison population**.

This is deterministic population hygiene, not result-driven pruning.

If a dimension differs across survivors, it remains in the comparison exactly as declared.

For the current five 245-Composition Purpose populations, one 7Y Elevation spoke is constant:

```text
elevation_7y_positive_period_pct
```

Therefore the current 7Y production comparison uses 18 informative spokes.

A future population may vary on that spoke; if so, the spoke automatically returns to the production surface.

## 7.4 Radial coordinate

For each informative spoke, raw values are converted to a population-relative percentile coordinate in [0,1].

Higher coordinate always means better evidence:

- upward Elevation metrics retain their percentile;
- downward Protection metrics reverse their percentile.

The dimensions are therefore dimensionless and directly comparable.

No second normalization is performed.

## 7.5 Utopia Point

For every retained spoke:

\[
U_j = \max_i x_{ij} = 1
\]

The Utopia Point is therefore the unattainable combination formed by the best observed value on every retained spoke.

It is a reference object, not a claimed investable Composition.

## 7.6 Distance shape

For Composition `i` and spoke `j`:

\[
d_{ij}=U_j-x_{ij}=1-x_{ij}
\]

This is the Composition's regret, or distance from the attainable population-relative best, on that spoke.

The complete vector `d_i` is the Composition's distance-shape.

## 7.7 Primary compromise ordering: L2

FINAL's primary ordering is unweighted Euclidean distance:

\[
L_2(i)=\sqrt{\sum_{j=1}^{m}d_{ij}^2}
\]

The smallest L2 distance is the production winner.

Equal spoke weighting is intentional. It means every retained evidence dimension contributes one equal vote to the compromise calculation.

L2 is not described as exponential. Squaring makes larger regrets disproportionately influential, but it is still a polynomial norm.

## 7.8 L-infinity diagnostic

The worst-spoke distance is:

\[
L_\infty(i)=\max_j d_{ij}
\]

L-infinity is retained because the Lakshya philosophy explicitly cares about catastrophic weakness in one dimension.

However, FINAL does **not** impose an arbitrary L-infinity kill threshold.

The production rule is:

> **Inspect the worst dimension; eliminate by L-infinity only if the population itself provides a defensible, reproducible boundary. Otherwise retain L-infinity as a diagnostic and joint-objective view.**

For the current 245 population, the observed L-infinity distribution did not provide such a natural boundary, so no arbitrary kill was promoted into production.

## 7.9 Joint L2/L-infinity frontier

FINAL also calculates the non-dominated frontier when minimizing the pair:

```text
(L2, L-infinity)
```

This preserves the mathematically meaningful trade-off between:

- total distance from the best attainable balance; and
- worst single-spoke weakness.

The joint frontier is evidence, not a subjective tie-breaker.

## 7.10 Lp robustness

FINAL sweeps a deterministic set of compromise norms:

```text
p = 1.00, 1.25, 1.50, ... , 10.00
```

and records the winner at each p.

The purpose is not to select a preferred p after seeing the answer. It is to test whether the primary L2 winner occupies a broad compromise regime or exists only under one narrow mathematical formulation.

## 7.11 Leave-one-spoke sensitivity

Each informative spoke is removed once and the L2 ordering is recomputed.

The output records:

- the removed spoke;
- the resulting winner;
- the primary winner's new rank.

This detects dependence on any single dimension without silently changing the production surface.

## 7.12 Population bootstrap

FINAL performs a deterministic population bootstrap with:

- sampling with replacement;
- the same population size as the MISSION survivor population;
- a fixed recorded seed;
- 5,000 resamples by default.

For every resample, the empirical population-relative coordinate system is rebuilt and the original candidate set is rescored.

The output records:

- win count;
- win percentage;
- median rank;
- mean rank;
- 5th and 95th percentile rank;
- resample count;
- seed.

This is a robustness test of the **analytical ordering**. It is not a forecast of future fund returns and does not establish causal fund synergy.

## 7.13 Production winner

The FINAL production winner is the minimum-L2 Composition in the Purpose's current MISSION survivor population.

Robustness outputs do not override the primary definition. They tell us how stable that definition is.

A later production release may change the primary objective only by changing the FINAL contract version and corresponding tests/documentation.

---

# 8. Why FINAL is not another Pareto stage

The earlier Pareto stages answer:

> **Can this candidate be shown to be strictly inferior across all declared dimensions?**

FINAL asks a different question:

> **Among candidates that remain genuinely trade-off-rich, which one is closest to the best attainable balance?**

The current 245-composition 7Y population demonstrates why this distinction matters: pure Pareto dominance leaves all 245 non-dominated in the distance-space.

The production system therefore moves from elimination to compromise ordering only after Pareto elimination has exhausted its legitimate authority.

---

# 9. Production artifact contract

For each Purpose, FINAL writes:

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

The summary is the compact production hand-off. The other artifacts preserve the 30,000-feet ↔ 3-feet audit trail.

All files are written atomically.

---

# 10. Versioning

The FINAL algorithm is explicitly versioned with:

```text
FINAL_CONTRACT_VERSION = 1
```

The following changes require a future contract version:

- changing the Purpose surface;
- changing percentile semantics;
- changing the primary norm;
- introducing subjective weights;
- introducing an L-infinity elimination threshold;
- changing bootstrap semantics;
- changing the supported p sweep;
- changing winner tie-breaking.

Adding a new diagnostic artifact without changing the production decision rule does not necessarily require a contract version change, but must be documented and tested.

---

# 11. What is deliberately not in v1

The following are explicitly parked:

- Composition regions;
- clustering;
- arbitrary k-neighbour connectivity;
- subjective Purpose scoring;
- Purpose-specific spoke weights;
- synthetic target shapes such as “maximum Elevation + maximum Protection”;
- arbitrary L-infinity kill thresholds;
- fund-house narrative as an optimization input;
- future-return forecasting;
- causal claims about why a winning Composition works.

These may be investigated in a later release only if evidence earns them.

---

# 12. Production philosophy

The Lakshya journey is intentionally staged:

```text
FUND
  ↓  observed individual behaviour
TEAM
  ↓  structural collective behaviour
COMPOSITION
  ↓  allocation geometry
MISSION
  ↓  Purpose qualification + lived trajectory
FINAL
  ↓  mathematically explicit compromise ordering
```

The final stage is therefore not an optimizer dropped onto an arbitrary portfolio universe.

It is the endpoint of a chain of earned evidence.

> **We were not searching for a portfolio. We were building a road on which a portfolio could eventually be discovered.**
