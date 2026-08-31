# Lakshya Pipeline Sequence

## Purpose

This document records the current stage-to-stage execution sequence so that future investigations can follow the architecture from persisted inputs to MISSION survivors without rediscovering existing plumbing.

This is an architectural navigation document, not a specification of every metric.

## High-level sequence

```text
Persisted FUND inputs
    |
    v
FUND admission / admissible universe
    |
    v
Persisted FUND NAV evidence (JSON, one artifact per ISIN)
    |
    v
Canonical NAV-history normalization
    |
    v
TEAM candidate generation (singleton / pair / trio)
    |
    v
Collective TEAM NAV trajectory
    |
    v
TEAM behavioural fingerprint
    |
    v
TEAM comparator surface / frontier
    |
    v
Admitted TEAMs (passed in memory to next stage)
    |
    v
COMPOSITION generation (existing simplex/grid)
    |
    v
Weighted Composite-NAV trajectory
    |
    v
COMPOSITION behavioural fingerprint
    |
    v
MISSION: global composite frontier
    |
    v
MISSION: purpose / achievability gate
    |
    v
MISSION: protection frontier
    |
    v
Surviving Compositions
    |
    v
Purpose-specific trajectory observation
    |
    v
Local experimental output/
```

## Current persisted inputs

```text
data/fund/funds_in_scope.csv
    -> family's explicit FUND universe

data/fund/funds_in_scope_metadata.csv
    -> auto-fetched FUND metadata

data/fund/funds_admissible.csv
    -> derived authoritative admitted FUND universe

data/nav/<ISIN>.json
    -> persistent historical NAV evidence, one artifact per ISIN
data/purpose/purposes.csv
    -> family Purpose inputs
```

The current Purpose source-of-truth schema is intentionally small:

```text
name,due,value,desired,monthly_plan
```

`due` is the persisted event date; horizon is derived from it where a Purpose-specific calculation requires a horizon. Purposes with `due=NA` are ongoing / not applicable to finite-horizon MISSION validation.

## Current code ownership

| Stage / object | Current implementation seam |
|---|---|
| Fund admission | `python/fund_analysis/fund_admission.py` |
| Admissible Fund loader | `python/fund_analysis/admissible_funds.py` |
| NAV source adapter | `python/fund_analysis/nav_source.py` |
| Persistent NAV evidence | `python/fund_analysis/nav_evidence.py` |
| Canonical NAV normalization | `python/lakshya_core/nav_history.py` |
| TEAM candidate generation | `python/team_analysis/candidate_generator.py` |
| Collective TEAM NAV | `python/team_analysis/collective_timeline.py` |
| TEAM orchestration | `python/team_analysis/run_team_pipeline.py` |
| TEAM fingerprint | `python/team_analysis/team_fingerprint.py` |
| TEAM frontier | `python/team_analysis/frontier_pipeline.py` |
| Composition model/generation | `python/team_analysis/composition.py`, `generate_compositions.py` |
| Composition pipeline | `python/team_analysis/composition_pipeline.py` |
| Composition fingerprint | `python/team_analysis/composition_fingerprint.py` |
| Composition frontier | `python/team_analysis/composition_frontier.py` |
| MISSION trajectory experiment | `python/mission/survivor_trajectory_experiment.py` |

## Important architectural invariants

### Raw collective trajectory first

The collective/Composite NAV is constructed before behavioural metrics are interpreted. Metrics are not combined across constituents as a substitute for constructing the underlying collective trajectory.

For TEAMs, `build_collective_nav()` derives a collective NAV from member FUND histories using each member's latest observation as of each collective observation date. The behavioural engine then operates on that collective trajectory.

For Compositions, the weighted Composite-NAV is likewise the underlying object from which the Composition fingerprint is independently calculated.

### Stage boundaries are primarily in-memory

The public TEAM runner returns the non-dominated Team frontier as Python objects; this is not currently a canonical persisted CSV hand-off. The Composition pipeline consumes those admitted Teams directly.

Likewise, the existing stage primitives are composed in memory. Persistence is therefore a property of selected source/evidence artifacts, not an automatic requirement for every stage boundary.

### Experimental persistence is separate

For the current trajectory investigation, selected intermediate and observation results may be written under `output/` for inspection and shared experimentation. These outputs are experimental evidence, not new canonical Lakshya domain artifacts and must not leak experimental semantics into the mainline stage implementations.

During this exploration period, `output/` may be temporarily tracked in GitHub so that the evidence can be inspected collaboratively. The experimental outputs are expected to be removed completely when the investigation concludes.

## Current MISSION gate sequence for this investigation

The working three-gate sequence being investigated is:

1. **Global composite frontier** — weak dominance pruning of truly dominated Compositions.
2. **Purpose / achievability frontier** — Purpose-horizon-driven qualification against supported elevation evidence, removing true outliers relative to the Purpose's target-growth requirement.
3. **Protection-only frontier** — weak dominance pruning of truly dominated Compositions on the protection surface.

The trajectory experiment is deliberately downstream of these earned gates. It searches for Purpose-relevant discriminators among otherwise surviving Compositions rather than redefining the earlier gates.

## Purpose input boundary

The persisted Purpose data supplies the existing achievability calculation's external objective inputs (`value`, `desired`, `monthly_plan`) and the event date (`due`). The trajectory experiment itself should consume only the Purpose horizon once the survivor population has been faithfully produced by the upstream MISSION path.

This separation prevents the experimental trajectory observation from accidentally changing the semantics of the existing Purpose gate.

## Why this document exists

The repository already contains the individual primitives and stage runners. The common failure mode during later exploration is therefore not absence of code but loss of the map connecting the pieces. This document is intended to provide that map.

## Documentation follow-up

At an appropriate architecture checkpoint, review each public module/function for sufficient docstrings and add stage-level documentation where the execution contract is currently implicit. The review should cover:

1. inputs and persisted artifacts consumed;
2. output object/artifact produced;
3. whether the function constructs raw trajectory evidence or derives metrics;
4. ownership of each frontier/gate;
5. whether the operation is production architecture or an experiment;
6. the boundary between FUND, TEAM, COMPOSITION and MISSION.

A later diagram can split this high-level sequence into FUND, TEAM/COMPOSITION and MISSION stage diagrams if the single sequence becomes too dense.
