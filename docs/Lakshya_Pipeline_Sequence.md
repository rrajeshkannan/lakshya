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
FUND NAV histories
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
Admitted TEAMs
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
```

## Current code ownership

| Stage / object | Current implementation seam |
|---|---|
| Fund admission | `python/fund_analysis/fund_admission.py` |
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

## Important architectural invariant

The collective/Composite NAV is constructed before behavioural metrics are interpreted. Metrics are not combined across constituents as a substitute for constructing the underlying collective trajectory.

For TEAMs, `build_collective_nav()` derives a collective NAV from member FUND histories using each member's latest observation as of each collective observation date. The behavioural engine then operates on that collective trajectory.

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
