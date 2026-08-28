# Lakshya — Team Behavioural Fingerprint

## Purpose

The TEAM stage understands a group of admitted Funds as a **collective
behavioural entity**, rather than as a simple list of individual Fund
scores.

Its question is:

> **What kind of collective do these teammates form?**

TEAM is descriptive, not prescriptive. It establishes which collective
behavioural structures are non-dominated under the declared TEAM gate; it
does not determine what the family should own or how a goal should be
funded.

TEAM establishes collective behavioural evidence that MISSION may
consume.

------------------------------------------------------------------------

# TEAM and the Fund Boundary

TEAM begins with Funds that have already earned admission to the
behavioural universe.

```text
Admitted Funds
      ↓
Team candidates
      ↓
Collective evidence
      ↓
Team Behavioural Fingerprint
```

Fund Admission is therefore not reinterpreted inside TEAM.

`CURRENT` and `POTENTIAL` are Fund Admission concepts. Once a Fund is
admitted, those labels do not become collective behavioural semantics.

TEAM also does not reach backward into raw Fund/NAV machinery merely to
make a Team decision. It consumes the Fund-level evidence required by its
own contract.

------------------------------------------------------------------------

# Team Formation

The established TEAM universe currently contains:

- singleton Teams;
- pair Teams; and
- trio Teams.

The maximum Team size is therefore **3 members**.

Candidate generation is deterministic. The combinatorial size of the
candidate universe is expected to grow rapidly with the number of
admitted Funds.

TEAM therefore uses a streaming frontier approach so that the analytical
process need not retain the complete Team universe merely to identify
non-dominated candidates.

The combinatorial universe belongs to TEAM. Higher-order MISSION
semantics must not be imported into candidate generation merely to reduce
its size.

------------------------------------------------------------------------

# Collective Evidence

A Team is not defined by combining already-compressed Fund scores.

TEAM constructs collective evidence from the members' underlying
behavioural histories available to the TEAM contract.

The intended evidence flow is:

```text
Fund histories / admitted Funds
          ↓
     Team candidate
          ↓
    collective NAV
          ↓
 collective behavioural evidence
          ↓
  Team Behavioural Fingerprint
```

This preserves the distinction between an individual Fund's behaviour and
the behaviour of the collective formed by the Team.

Collective evidence must remain sufficiently rich to support movement
between:

> **30,000 feet ↔ 3 feet**

A frontier membership is therefore not a replacement for the underlying
collective behavioural evidence.

------------------------------------------------------------------------

# The TEAM Behavioural Surface

TEAM currently uses the shared FUND/TEAM directional comparator surface.
The declared gate contains **40 dimensions**.

## Elevation

Elevation contributes **28 upward dimensions**:

```text
4 rolling horizons
×
7 observed rolling-return measures
=
28 dimensions
```

The horizons are:

- 3 years
- 5 years
- 7 years
- 10 years

For each available horizon the current surface preserves:

- minimum
- P25
- median
- P75
- maximum
- mean
- positive-period frequency

Higher values are better for these Elevation dimensions.

A horizon can be unavailable when the underlying history is insufficient.
Unavailable evidence remains unavailable; it is not manufactured as zero.

## Protection

Protection contributes **12 downward dimensions**:

### Severity distribution

- median severity
- P75 severity
- P90 severity
- P95 severity
- P99 severity
- maximum severity

### Terrain frequency

The proportion of observations at or beyond:

- 5%
- 10%
- 15%
- 20%
- 25%
- 30%

Lower values are better for these Protection dimensions.

These are descriptive behavioural landmarks, not universal declarations
of what constitutes acceptable adversity.

------------------------------------------------------------------------

# Why Resilience Is Not Currently in the TEAM Gate

FUND contains a Resilience dimension describing the journey through and
out of drawdown episodes.

TEAM does **not currently use Resilience in its declared comparator
surface**.

This does not make Resilience meaningless or incorrect at FUND stage. It
means that the current TEAM contract has not established a need for that
Fund-level dimension in the collective gate.

The principle is:

> **A calculated lower-level metric does not automatically become a
> downstream input.**

This is an architectural boundary decision, not a claim that the
underlying evidence should be destroyed.

Future stages must independently earn the need for any information they
consume.

------------------------------------------------------------------------

# Evidence-State Principle

TEAM preserves the distinction between observed evidence and unavailable
evidence.

In particular:

> **Unknown is not zero.**

When a collective fingerprint lacks a particular Elevation horizon, the
corresponding comparator values remain explicitly unavailable while the
declared comparator surface remains structurally stable.

The comparator surface and its declared gate dimensions must remain in
exact agreement.

TEAM therefore distinguishes:

```text
available evidence
       ≠
zero evidence
```

and:

```text
not part of the TEAM gate
       ≠
invalid or unimportant evidence
```

------------------------------------------------------------------------

# TEAM Frontier

The TEAM frontier contains candidate Teams for which no other candidate
is at least as good in every declared dimension and strictly better in at
least one dimension, under the declared directional semantics.

The current dimensions are directional:

```text
Elevation  → UP
Protection → DOWN
```

The frontier is therefore an exact **non-dominated frontier**, not a
weighted ranking and not a single composite score.

The streaming implementation preserves the same dominance semantics while
avoiding the need to retain the complete candidate universe.

### Frontier principle

A Team can remain on the frontier because of a genuine trade-off between
dimensions.

A candidate that is dominated across the complete declared surface is
removed from the frontier.

No arbitrary weighting is introduced merely to force a total ranking.

------------------------------------------------------------------------

# Compression Principle

TEAM is a stage of abstraction, not a stage of arbitrary information
loss.

> **Compression can be useful. Compression cannot be allowed to erase
> meaning.**

The Team frontier is a compressed representation of the non-dominated
collective universe. It is not the complete historical evidence itself.

TEAM may reduce the candidate universe according to its own declared
behavioural gate, but it must preserve enough evidence beneath the
reduction for meaningful interpretation by the next stage.

TEAM must not use MISSION semantics to justify its own compression.

------------------------------------------------------------------------

# TEAM → MISSION Boundary

The TEAM stage ends with a behavioural understanding of collective
structures.

It answers:

> **Which collective behavioural structures are non-dominated under the
> TEAM gate?**

It does not answer:

> **Which collective should the family use for a particular purpose?**

That is a MISSION question.

The following are deliberately outside the TEAM boundary:

- family purpose;
- goal suitability;
- goal-specific constraints;
- composition percentages;
- allocation per goal;
- portfolio-purpose decisions; and
- higher-order MISSION entities.

The exact durable TEAM → MISSION output contract is **not yet frozen**.
It must be established from MISSION's requirements rather than assumed in
advance.

------------------------------------------------------------------------

# Calculation, Consumption and Persistence

Lakshya distinguishes three separate questions at every boundary:

1. **What can this stage calculate?**
2. **What does the next stage actually consume?**
3. **What deserves durable persistence?**

These questions must not be collapsed into one.

A value may be calculated for a TEAM analysis without becoming part of the
MISSION input. A value may be useful to MISSION without requiring its own
independent persisted artifact. A richer underlying evidence set may
remain available for audit or interpretation without being promoted to a
new architectural dimension.

Therefore the TEAM stage does not pre-commit the final persistence model
for TEAM outputs before MISSION has established what it genuinely needs.

------------------------------------------------------------------------

# TEAM Implementation Boundary

The TEAM stage owns:

- Team candidate formation;
- collective behavioural evidence construction;
- Team fingerprint construction;
- the declared TEAM comparator surface;
- explicit unavailable-evidence handling;
- exact non-dominated frontier calculation; and
- TEAM-stage orchestration.

The TEAM stage does not own:

- Fund Admission;
- family goals;
- goal suitability;
- portfolio allocation;
- MISSION decisions; or
- Future Environment interpretation.

The public TEAM runner is an orchestration boundary. It delegates
candidate generation, collective evidence construction, fingerprinting,
comparator mapping and frontier calculation to their respective
components. It is not a second analytical implementation.

------------------------------------------------------------------------

# Current TEAM Architectural State

The TEAM foundation is implemented and unit/integration tested.

The current validated components include:

```text
Team candidates
      ↓
Collective evidence
      ↓
Team fingerprint
      ↓
40-D comparator surface
      ↓
Exact streaming frontier
      ↓
Public TEAM runner
```

The current automated checkpoint is:

> **159 passed, 1 skipped**

This establishes implementation behaviour through tests. It is **not yet
the real-data commissioning result**.

The complete real-data FUND → TEAM → MISSION run is deliberately
postponed until the MISSION architecture is fully established and tested.

------------------------------------------------------------------------

# TEAM Question

TEAM exists to answer one architectural question:

> **What kind of collective do these teammates form?**

The answer is behavioural and evidence-based.

It is not a recommendation.

It is not an allocation.

It is not a goal decision.

TEAM therefore forms the structural bridge between individual Fund
behaviour and the purpose-driven reasoning that belongs to MISSION.
