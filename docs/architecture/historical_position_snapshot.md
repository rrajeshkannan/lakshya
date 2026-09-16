# LFS Historical Position Snapshot

## Purpose

LFS formation is evaluated at one explicit `formation_as_of` boundary.  The
financial Position state consumed by Purpose-capital formation must represent
that same boundary rather than the latest persisted Position valuation.

## Contract

```text
formation_as_of = T
        |
        +-- Transactions with transaction_date <= T
        |       -> net units by Investor + Folio + ISIN
        |
        +-- LPS NAV evidence
        |       -> latest recorded NAV on or before T
        |
        +-- accepted Position Purpose attribution
        |
        v
Positions_AsOf(T)
        |
        v
Purpose.capital
        |
        v
MISSION Achievability
```

The historical adapter is an LFS input-formation concern. It does not teach
MISSION or Achievability how to value Positions.

## Persistence and resume

The single LFS runner forms the historical Position snapshot once at the input
boundary and persists it under `output/` as:

```text
positions_as_of_<YYYY-MM-DD>.csv
positions_as_of_<YYYY-MM-DD>.csv.complete.json
```

The completion marker binds the snapshot to its `as_of` date, output bytes,
and source-input hashes. A subsequent run can load the validated snapshot
instead of rebuilding it.

MISSION checkpoints additionally bind their completion markers to a hash of:

- `purposes.csv` intent; and
- the validated `Positions_AsOf(T)` snapshot.

Consequently, `resume_from="mission"` continues to reuse valid expensive
upstream evidence while recomputing MISSION when Purpose inputs have changed.
Trajectory checkpoints continue to depend on the resulting MISSION checkpoint.

## Attribution limitation

The current LPS Position state contains accepted Purpose attribution, but does
not yet persist effective-dated attribution history. The adapter therefore
carries the accepted attribution from the current Position state when forming
`Positions_AsOf(T)`. It does not invent historical attribution events. A future
LPS attribution-history contract can replace this input without changing the
MISSION Purpose model.

## Non-goals

- No persistent date/provenance fields are added to `Purpose` merely because
  `capital` is derived.
- `purposes.csv` remains intent-only.
- Achievability does not value Positions.
- Purpose Staging remains a separate current/review workflow.
- LFS does not acquire an independent valuation date separate from its
  formation boundary.
