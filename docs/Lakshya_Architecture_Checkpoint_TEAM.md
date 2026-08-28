# Lakshya — Architecture Checkpoint: TEAM

## Purpose of This Checkpoint

This document records the architectural state reached after establishing
the TEAM foundation and before designing the TEAM → MISSION boundary.

It records **what has been earned**, what has been deliberately excluded,
and what remains unresolved.

It is an architectural ledger, not code documentation.

------------------------------------------------------------------------

# 1. Architectural Flow

Lakshya's fundamental architecture is:

```text
FUND → TEAM → MISSION → FUTURE ENVIRONMENT
```

The questions evolve upward:

```text
FUND
What kind of teammate is this fund?

        ↓

TEAM
What kind of collective do these teammates form?

        ↓

MISSION
What must this collective accomplish for the family?

        ↓

FUTURE ENVIRONMENT
How should the system remain suitable as the family and world evolve?
```

Each stage is therefore a distinct abstraction boundary rather than a
collection of increasingly complicated calculations.

------------------------------------------------------------------------

# 2. What FUND Has Earned

FUND establishes individual Fund behavioural evidence through the Fund
Compass:

- Elevation;
- Protection; and
- Resilience.

It is descriptive rather than prescriptive.

Fund Admission establishes the behavioural universe before downstream
collective reasoning begins.

The Fund stage has persisted NAV evidence and version-linked Fund
fingerprint state because those artefacts were established as part of the
Fund-stage analytical foundation.

------------------------------------------------------------------------

# 3. The First Boundary Discovery: Resilience

One of the important discoveries during TEAM construction was that FUND
Resilience does not need to be part of the current TEAM gate.

The resulting architecture is:

```text
FUND
 ├── Elevation
 ├── Protection
 └── Resilience
          │
          │ TEAM contract requires
          │ only selected evidence
          ▼
TEAM
 ├── Elevation
 └── Protection
```

TEAM's current comparator surface therefore does not include Resilience.

This establishes a general rule:

> **A lower-stage calculation does not automatically become a
> higher-stage input.**

Resilience remains meaningful Fund evidence. Its absence from the TEAM
surface does not imply that the evidence is wrong, useless, or necessarily
discarded.

It means only that TEAM has not earned a requirement for it.

------------------------------------------------------------------------

# 4. TEAM Has Now Been Established

TEAM currently forms:

- singleton Teams;
- pair Teams; and
- trio Teams.

It constructs collective behavioural evidence, Team fingerprints, a
40-dimensional comparator surface and an exact non-dominated frontier.

The TEAM analytical flow is:

```text
Admitted Funds
      ↓
Team candidates
      ↓
Collective evidence
      ↓
Team fingerprint
      ↓
TEAM comparator surface
      ↓
Exact streaming frontier
```

The public TEAM runner is intentionally thin. It provides the stage-level
orchestration boundary while delegating analytical responsibilities to the
existing TEAM components.

------------------------------------------------------------------------

# 5. What TEAM Has Earned

The current TEAM contract has earned the following concepts:

### Team candidate

A deterministic singleton, pair or trio formed from admitted Funds.

### Collective evidence

Evidence describing the behaviour of the Team as a collective rather than
merely combining individual Fund scores.

### Team Behavioural Fingerprint

A structured representation of the collective evidence required by the
TEAM behavioural surface.

### TEAM comparator surface

The current gate contains 40 dimensions:

```text
28 Elevation
12 Protection
----------------
40 total
```

### TEAM frontier

The exact non-dominated set under the declared directional semantics.

### Streaming frontier

A memory-conscious way to process the potentially large Team universe
without requiring the entire universe to be retained.

------------------------------------------------------------------------

# 6. What TEAM Has Deliberately Not Earned

TEAM does not currently own or consume:

- family purpose;
- family goals;
- goal suitability;
- composition percentages;
- allocation per goal;
- portfolio-purpose decisions; or
- Future Environment interpretation.

These belong to higher-order reasoning and must not be introduced into
TEAM merely to make TEAM's own computation easier.

In particular:

> **TEAM must not decide what MISSION wants.**

TEAM may determine non-dominance under its own declared behavioural gate.
It must not use a hidden purpose-based filter to manufacture a smaller
frontier.

------------------------------------------------------------------------

# 7. The TEAM → MISSION Question

The next architectural question is not yet:

> "How do we code MISSION?"

It is:

> **What genuinely needs to cross from TEAM into MISSION?**

That question must be answered before the MISSION input contract is
frozen.

For every candidate output or evidence artefact, Lakshya should ask:

1. Is it calculated?
2. Is it consumed by MISSION?
3. Is it needed for deeper interpretation or audit?
4. Does it deserve durable persistence?

A positive answer to one question does not automatically imply a positive
answer to the others.

------------------------------------------------------------------------

# 8. Persistence Is a Separate Architectural Decision

The current TEAM stage deliberately does not pre-commit the final
persistence model for its outputs.

This is intentional.

The real-data commissioning run is being postponed until MISSION has been
fully established and unit/integration tested.

The reason is architectural rather than computational:

> **We should not persist intermediate analytical state before knowing
> which information genuinely deserves to survive the abstraction
> boundary.**

The Fund stage already contains persisted NAV and fingerprint artefacts.
That does not establish that equivalent persistence is required for every
TEAM intermediate.

Likewise, a TEAM calculation being useful during analysis does not make it
a durable Lakshya state automatically.

------------------------------------------------------------------------

# 9. Real Data Is Deliberately Deferred

The current test suite validates the analytical machinery through unit
and integration tests.

The current checkpoint is:

> **159 passed, 1 skipped**

This is not yet the real-data commissioning result.

The complete chain:

```text
real Fund NAVs
      ↓
FUND
      ↓
TEAM
      ↓
MISSION
```

will be executed only after MISSION's architecture and evidence boundary
have been established sufficiently to know what should be observed,
retained and persisted.

This avoids generating a large body of provisional analytical artefacts
that may later prove to be unnecessary.

------------------------------------------------------------------------

# 10. Architectural Principle: Earned Abstraction

Lakshya deliberately prefers:

```text
requirement
    ↓
evidence
    ↓
architecture
    ↓
implementation
```

rather than:

```text
implementation
    ↓
assumed abstraction
    ↓
forced requirement
```

The TEAM experience has reinforced this principle.

We did not carry Resilience upward merely because FUND calculates it.
We did not inject MISSION semantics into TEAM merely because the TEAM
universe can become large.
We did not define persistence merely because intermediate results exist.

These exclusions are part of the architecture.

------------------------------------------------------------------------

# 11. Information Shedding

As Lakshya moves upward, the architecture may intentionally retain less
information at the next boundary while preserving enough underlying
evidence for meaningful interpretation.

This can be understood as **architectural compression**:

```text
FUND
rich individual evidence
        ↓
TEAM
necessary collective evidence
        ↓
MISSION
purpose-relevant collective evidence
```

The reduction is legitimate only when the higher-stage requirement is
known and the reduction does not erase meaning needed for that stage.

> **Compression can be useful. Compression cannot be allowed to erase
> meaning.**

------------------------------------------------------------------------

# 12. Current State and Next Step

The current state is:

```text
FUND
  │
  │ individual behavioural evidence
  ▼
TEAM
  │
  │ collective behavioural evidence
  │ non-dominated Team frontier
  ▼
MISSION
  │
  │ boundary not yet frozen
  ▼
FUTURE ENVIRONMENT
```

TEAM is now an established, tested architectural layer.

The next work is **TEAM → MISSION boundary discovery**.

The immediate objectives are:

- identify the minimum sufficient TEAM information MISSION needs;
- distinguish behavioural evidence from purpose-driven interpretation;
- identify what remains TEAM-internal or transient;
- determine what deserves persistence;
- avoid premature abstraction or generalisation; and
- only then establish the MISSION contract and implementation.

After MISSION is fully established and tested, Lakshya can perform the
real-data commissioning run with a much clearer understanding of which
outputs are genuinely durable.

------------------------------------------------------------------------

# Checkpoint Summary

> **TEAM foundation established.**

> **TEAM behavioural frontier established.**

> **TEAM public orchestration boundary established.**

> **159 tests passed, 1 skipped.**

> **Real-data commissioning deliberately deferred.**

> **TEAM → MISSION boundary remains the next architectural discovery.**
