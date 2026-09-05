# Lakshya

Lakshya is a family-oriented investment analysis architecture for understanding, constructing and evolving a portfolio over a lifetime and beyond.

## Production Architecture

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL
```

The stages deliberately earn information from below rather than importing higher-order semantics prematurely.

> **Information should be introduced at the layer that genuinely earns the need for it.**

For expensive analytical evidence:

> **Compute once. Persist immediately. Reuse forever.**

The production system values analytical richness, correctness, reproducibility, interpretability and resilience ahead of raw speed.

---

# FUND

### What kind of teammate is this fund?

FUND establishes observed individual-fund behaviour across:

- Elevation;
- Protection;
- Resilience.

FUND is descriptive, not prescriptive.

The explicit source of scope is `data/fund/funds_in_scope.csv`. The 8-year lived-history admission rule applies only to POTENTIAL/new-entry funds; CURRENT funds may be younger. Regular versus Direct is not a Lakshya analytical distinction.

FUND does not know Purpose, allocation or FINAL optimization.

Detailed specification: `docs/Lakshya_Fund_Behavioural_Fingerprint.md`

---

# TEAM

### What kind of collective do these teammates form?

TEAM forms singleton, pair and trio structures, with maximum Team size 3.

The declared TEAM gate surface is 40 dimensions:

- 28 Elevation = 4 horizons × 7 rolling measures;
- 12 Protection dimensions.

Supported Elevation horizons are 3Y / 5Y / 7Y / 10Y. Protection is native and horizon-free.

TEAM uses weak exact Pareto non-dominance and does not import MISSION semantics merely to reduce its universe.

Detailed specification: `docs/Lakshya_Team_Behavioural_Fingerprint.md`

---

# COMPOSITION

### Where does capital sit within a collective?

A Composition is **Team + complete weights**.

The positive grid is:

- singleton: 100%;
- pair: 19 allocations on a 5% grid;
- trio: 171 allocations on a 5% grid.

Composition fingerprints are durable evidence containing identity, weights, NAV, Elevation and Protection evidence. They are schema-versioned, atomically persisted and losslessly rehydratable.

The global Composition frontier is the weak Pareto frontier over the 40-dimensional Elevation + Protection surface.

---

# MISSION

### What must this collective accomplish for the family?

MISSION introduces Purpose semantics.

A Purpose may have a finite target/horizon or may be open-ended with an analytical horizon. Open-ended Purposes still receive Elevation, Protection and Trajectory analysis; only Achievability is absent when there is no finite target requirement.

The canonical analytical horizon ladder is:

```text
3Y / 5Y / 7Y / 10Y
```

For a Purpose, use the longest supported analytical horizon not beyond the Purpose horizon. Thus 4Y→3Y, 9Y→7Y, 12Y→10Y and 13Y→10Y.

MISSION sequence:

```text
Global Composition frontier
        ↓
Achievability, when applicable
        ↓
Protection-only frontier
        ↓
MISSION survivors
        ↓
Purpose Trajectory observation
```

Trajectory is descriptive and preserves actual observation horizon/status. It never silently equates shorter lived history with the Purpose horizon.

---

# FINAL

### Among qualified Compositions, which is the strongest practical compromise?

FINAL is the production ordering stage. It does not reopen MISSION eligibility.

For each Purpose:

```text
7 Elevation dimensions at selected horizon
+
12 native Protection dimensions
```

Every retained individual spoke is equally weighted. Zero-variance spokes are removed deterministically from the current comparison population; varying spokes remain unchanged.

Each spoke is converted to a population-relative desirability coordinate in `[0,1]`, with higher always better. The Utopia Point is the best observed value on every retained spoke.

Distance from Utopia is:

```text
d_ij = 1 - x_ij
```

The production winner is the Composition with minimum unweighted Euclidean distance:

```text
L2 = sqrt(sum(d_ij²))
```

L-infinity remains a worst-spoke diagnostic and participates in a joint L2/L-infinity non-dominated frontier. No arbitrary L-infinity kill threshold is used.

FINAL also records:

- Lp winner sweep from 1.00 to 10.00 in 0.25 increments;
- leave-one-spoke sensitivity;
- 5,000 deterministic population bootstrap resamples by default.

No subjective Purpose score, Purpose-specific spoke weighting, Composition regions, clustering or future-return forecast is part of FINAL v1.

Detailed production specification: `docs/Lakshya_Production_Architecture_v1.md`

Production sequence: `docs/Lakshya_Pipeline_Sequence.md`

Current architecture checkpoint: `docs/Lakshya_Current_Architecture_Checkpoint.md`

---

# Evidence philosophy

Lakshya preserves depth.

**30,000 feet ↔ 3 feet**

Observed is not inferred. Unknown is not zero. Compression may organize evidence, but must not erase meaning.

The implementation discipline is:

```text
PHILOSOPHY
    ↓
SPECIFICATION
    ↓
TESTS
    ↓
IMPLEMENTATION
    ↓
EVIDENCE
    ↓
INTERPRETATION
```

---

# Production release discipline

FINAL is explicitly versioned:

```text
FINAL_CONTRACT_VERSION = 1
```

A future change to the decision rule becomes a deliberate next production release with updated tests and documentation. Exploration can continue without silently changing production behaviour.

> **We were not searching for a portfolio. We were building a road on which a portfolio could eventually be discovered.**
