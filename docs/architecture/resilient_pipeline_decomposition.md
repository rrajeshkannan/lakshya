# `resilient_pipeline.py` Decomposition Map

## Purpose

This document records the source-archaeology baseline for the planned refactor of
`python/mission/resilient_pipeline.py`.

The immediate goal is **structural clarity without behavioral change**. The
refactor must preserve the existing analytical pipeline, checkpoint contracts,
`as_of` integrity, multiprocessing behavior, resume modes, public entry points,
and forensic logging.

## Current pipeline invariant

The resilient execution engine follows:

```text
compute → persist → validate → consume
```

Expensive Composition fingerprints and downstream stage CSVs are reusable only
when their relevant completion marker, content hash, `as_of` date, and input
provenance validate.

## Current responsibility map

### 1. Runtime and forensic infrastructure

Current functions:

- `_wall_timestamp`
- `_console`
- `_detail`
- `_log`
- `_event`
- `_write_manifest`
- `_manifest_update`
- `_as_of_string`
- `_input_hash`

Proposed destination: `pipeline_runtime.py`

Primary concern: `_RUN_MANIFEST` is module-global mutable state. It must not be
duplicated accidentally during extraction. Any move should preserve one coherent
manifest state or replace it with an explicit runtime context in a separately
reviewed change.

### 2. Input loading and normalization

Current functions:

- `_load_fund_histories`
- `_floor_years`
- `_load_purposes`

Proposed destination: `pipeline_inputs.py`

Responsibilities:

- load admitted-fund NAV evidence;
- apply the canonical `as_of` NAV cutoff at the input boundary;
- parse Purpose inputs;
- calculate Purpose horizons;
- preserve Purpose selection semantics.

The NAV cutoff must remain explicit and must never be deferred to later stages.

### 3. CSV and durable stage output

Current function:

- `_write_rows`

Proposed destination: `pipeline_outputs.py`

Responsibilities:

- ordinary atomic CSV output;
- durable stage-checkpoint output through the existing checkpoint writer;
- preservation of row counts and forensic logging.

This extraction must not change checkpoint metadata or validation semantics.

### 4. Composition candidate and evidence machinery

Current functions:

- `_write_composition_candidates`
- `_candidate_compositions`
- `_checkpoint_metadata`
- `_load_checkpoint_index`
- `_publish_checkpoint_index`
- `_scan_composition_checkpoints`
- `_persist_composition_evidence`

Proposed destination: `composition_evidence_stage.py`

Responsibilities:

- generate and enumerate Composition candidates;
- maintain the narrow checkpoint-index cache;
- use `has_fingerprint()` as the authoritative validation path on cache misses;
- compute only missing fingerprints;
- persist each completed fingerprint immediately;
- publish the index only after successful completion of missing work.

The distinction between the performance cache and authoritative checkpoint
validation is an invariant and must remain visible in tests.

### 5. Global Composition frontier and identity I/O

Current functions:

- `_load_global_pairs_for_frontier`
- `_global_inputs`
- `_load_global_identities`
- `_composition_from_identity`
- `_materialize_missing_mission_evidence`

Proposed destinations:

- `global_composition_stage.py` for global-frontier orchestration;
- possibly `composition_identity_io.py` for reusable identity reconstruction.

Responsibilities:

- load persisted Composition fingerprints;
- construct global-frontier input provenance;
- validate and load global survivor checkpoints;
- reconstruct `Composition` objects from stable identities;
- materialize compact MISSION evidence sidecars.

Identity reconstruction should be separated only after callers and invariants are
fully mapped.

### 6. MISSION stage

Current functions:

- `_run_one_purpose`
- `_mission_checkpoint_valid`
- `_run_mission_from_global`

Proposed destination: `mission_stage.py`

Responsibilities:

- assess achievability for each Purpose;
- apply the protection frontier;
- persist achievability and MISSION survivor checkpoints;
- validate and reuse MISSION outputs;
- execute independent Purpose jobs.

The worker function must remain importable and pickle-safe because it is submitted
to `ProcessPoolExecutor`.

### 7. Historical trajectory observation

Current functions:

- `_observe_one_purpose`
- `_trajectory_checkpoint_valid`
- `_observe_persisted_mission_outputs`

Proposed destination: `trajectory_stage.py`

Responsibilities:

- load persisted MISSION survivors;
- observe historical survivor trajectories;
- persist trajectory checkpoints;
- validate trajectory provenance and contract version;
- reuse valid trajectory outputs;
- execute independent Purpose jobs.

The trajectory checkpoint must continue to depend on the correct MISSION
checkpoint and `TRAJECTORY_CONTRACT_VERSION`.

### 8. Public orchestration and CLI

Current functions:

- `run`
- `main`

Proposed destination: retain `resilient_pipeline.py` as a thin orchestration
façade and CLI boundary.

The eventual orchestration should remain readable as:

```text
initialize run and manifest
    ↓
load inputs
    ↓
handle resume mode
    ↓
run TEAM
    ↓
run Composition evidence
    ↓
run global Composition frontier
    ↓
run MISSION
    ↓
run trajectory observation
    ↓
write summary and finalize manifest
```

## Cross-cutting invariants

Every extraction must preserve:

1. **As-of integrity** — historical NAV observations used by the pipeline must
   be limited to `date <= as_of`.
2. **Checkpoint provenance** — a checkpoint is reusable only when its stage,
   `as_of`, content hashes, and declared input provenance validate.
3. **Compute/persist/validate/consume ordering** — downstream stages must consume
   persisted evidence rather than silently reconstructing it.
4. **Resume behavior** — `resume_from="mission"` and `resume_from="global"` must
   retain their current meanings.
5. **Purpose selection** — explicit Purpose selection and unknown-Purpose errors
   must remain unchanged.
6. **Multiprocessing safety** — worker functions submitted to process pools must
   remain importable and serializable.
7. **Forensic observability** — existing manifest updates and detailed event logs
   must remain available and semantically consistent.
8. **Public compatibility** — the existing `run()` and CLI behavior must remain
   stable unless a separate, explicitly reviewed change says otherwise.

## Recommended extraction order

1. Add this decomposition map and establish the documentation baseline.
2. Extract pure or nearly pure helpers with limited coupling.
3. Extract input loading and normalization.
4. Extract ordinary output and checkpoint-index support where interfaces are
   explicit.
5. Extract the Composition evidence stage as one coherent unit.
6. Extract the global Composition stage and identity helpers.
7. Extract MISSION and trajectory stages, keeping process-pool workers local to
   their stage modules initially.
8. Reduce `resilient_pipeline.py` to orchestration and CLI code.
9. Run the full regression suite and inspect the final diff for behavioral drift.

## Explicit non-goals

This refactor is not intended to:

- redesign the analytical model;
- alter FUND, TEAM, COMPOSITION, MISSION, or FINAL logic;
- change checkpoint schemas;
- replace the current persistence protocol;
- mix the FUND Pareto-gate work into the first structural extraction;
- introduce a framework or broad abstraction layer;
- remove compatibility names without checking callers and tests.

## First code-extraction candidate

The first production extraction should target **input loading and normalization**
only after its current callers and tests have been identified. It is relatively
isolated and directly reinforces the canonical `as_of` NAV boundary.

No code extraction should begin until the documentation baseline is reviewed and
accepted.
