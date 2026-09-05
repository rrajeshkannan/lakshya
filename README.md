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

---

# TEAM

### What kind of collective do these teammates form?

TEAM forms singleton, pair and trio structures, with maximum Team size 3.

The declared TEAM gate surface is 40 dimensions:

- 28 Elevation = 4 horizons × 7 rolling measures;
- 12 Protection dimensions.

Supported Elevation horizons are 3Y / 5Y / 7Y / 10Y. Protection is native and horizon-free.

TEAM uses weak exact Pareto non-dominance and does not import MISSION semantics merely to reduce its universe.

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

---

# Running Lakshya

## First run / annual review — end to end

The canonical production entry point is:

```bash
python python/run_production.py --as-of YYYY-MM-DD
```

For example:

```bash
python python/run_production.py --as-of 2026-09-06
```

Run this command from the repository root.

It runs the complete production chain:

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

More precisely, the runner invokes the resilient upstream MISSION pipeline and then executes FINAL for each requested Purpose. FINAL consumes the persisted MISSION survivor checkpoints; it does not rebuild upstream evidence merely because FINAL is being run.

### What happens on a first run?

The pipeline loads the explicit Fund scope, builds/reuses the upstream persisted evidence and checkpoints, generates the Team and Composition universes, applies the global and Purpose-specific MISSION gates, observes Purpose trajectories, and finally performs FINAL compromise ordering and robustness analysis.

Expensive evidence follows:

```text
compute → persist → validate → consume
```

The run therefore creates or reuses the necessary persisted artifacts under `data/` and `output/`.

### What happens on an annual review / rerun?

Use the same command with the new review date:

```bash
python python/run_production.py --as-of YYYY-MM-DD
```

The production pipeline is checkpoint-aware. Valid upstream evidence is reused where the current contracts permit it; missing or invalid stages are reconstructed by the stage that owns them. A downstream FINAL change does not by itself invalidate valid Composition fingerprints.

FINAL also records a checkpoint tied to the MISSION survivor file, FINAL contract version, bootstrap resample count and bootstrap seed. A valid FINAL checkpoint can therefore be reused rather than recomputed.

### Resume options

If an upstream run was interrupted, the production runner supports:

```bash
python python/run_production.py --as-of YYYY-MM-DD --resume-from global
```

or:

```bash
python python/run_production.py --as-of YYYY-MM-DD --resume-from mission
```

Use these only when you intentionally want the upstream resilient pipeline to resume from its corresponding persisted checkpoint. The runner then continues into FINAL automatically.

### Run selected Purposes only

```bash
python python/run_production.py --as-of YYYY-MM-DD --purposes Retirement Edu_B
```

The same selected Purposes are passed through MISSION and FINAL.

### FINAL-only execution

If MISSION has already been successfully completed and you only want to rerun FINAL, the lower-level FINAL runner is available as a Python API through `run_final_stage()` in `python/run_production.py`. The normal production command is preferred because it verifies/runs the upstream MISSION stage before FINAL.

To force FINAL recomputation despite a valid FINAL checkpoint:

```bash
python python/run_production.py --as-of YYYY-MM-DD --no-final-reuse
```

### After the run

The compact production hand-off for each Purpose is:

```text
output/final_<Purpose>_summary.csv
```

The remaining FINAL artifacts preserve the audit trail:

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

For the full architectural explanation, see `docs/Lakshya_Architecture.md`.

For the execution sequence, persistence boundaries and resume semantics, see `docs/Lakshya_Pipeline_Sequence.md`.

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
