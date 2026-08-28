# Lakshya

Lakshya is a family-oriented investment architecture for understanding,
constructing and evolving a portfolio over a lifetime and beyond.

## Fundamental Architecture

```text
FUND → TEAM → MISSION → FUTURE ENVIRONMENT
```

Each stage consumes the understanding earned below it and asks a
higher-order question.

> **Aggregation gives us the structural flow.
> The questions give us the meaning of the flow.**

Lakshya follows an important discipline across the stages:

> **A calculation does not automatically become a downstream input, and a
downstream input does not automatically become persisted state.**

Information crosses an abstraction boundary only when the higher stage
has earned the need for it.

------------------------------------------------------------------------

## FUND

### What kind of teammate is this fund?

FUND establishes the observed behavioural character of an individual
fund.

Its behavioural fingerprint has three primary dimensions:

- **Elevation** — participation in prosperity
- **Protection** — severity of adversity
- **Resilience** — the journey after adversity begins

The Fund stage is descriptive, not prescriptive. It establishes evidence;
it does not decide whether Lakshya should own the fund.

### Fund-stage evidence flow

```text
Fund Admission
      ↓
Admissible Funds
      ↓
NAV Evidence
      ↓
Fund Behavioural Fingerprint
      ↓
Fund Evidence / Compass views
```

Fund Admission establishes the behavioural universe. `CURRENT` /
`POTENTIAL` is an admission concern; once a Fund is admitted, that
distinction does not leak into later abstraction layers.

Detailed specification:

`docs/Lakshya_Fund_Behavioural_Fingerprint.md`

------------------------------------------------------------------------

## TEAM

### What kind of collective do these teammates form?

TEAM asks:

> **Who stands together?**

TEAM forms collective behavioural structures from admitted Fund-level
behavioural evidence. It remains descriptive rather than prescriptive.
TEAM does not decide what the family should own, how a goal should be
funded, or how capital should be allocated.

The established Team universe currently consists of:

- singleton
- pair
- trio

with a maximum of **3 members per Team**.

### TEAM evidence flow

```text
Admitted Funds
      ↓
Team candidates
      ↓
Collective NAV / evidence
      ↓
Team Behavioural Fingerprint
      ↓
TEAM comparator surface
      ↓
Non-dominated TEAM frontier
```

TEAM owns the collective behavioural calculation required to compare
candidate Teams. The current declared gate surface contains **40
comparative dimensions**:

- **28 Elevation dimensions**: 4 horizons × 7 rolling-return measures
- **12 Protection dimensions**: severity distribution and threshold-
  frequency measures

Resilience is not currently part of the TEAM gate surface. This is a
boundary decision, not an assertion that Resilience is unimportant at
FUND stage. TEAM consumes only the Fund evidence it actually needs.

The TEAM comparator preserves unavailable evidence explicitly rather than
manufacturing zeroes or silently changing the declared surface.

The frontier is an exact non-dominated frontier using the declared
upward/downward direction of each dimension. TEAM can stream candidates
through the frontier without retaining the full combinatorial universe.

### TEAM abstraction boundary

TEAM may determine which Teams are non-dominated under the **declared
TEAM behavioural gate**. It must not import MISSION semantics merely to
reduce its own output.

TEAM must not import:

- goal suitability;
- family goals or purpose;
- composition percentages;
- allocation;
- portfolio-purpose decisions; or
- higher-order MISSION entities

merely to reduce its own output.

The final durable TEAM → MISSION output and persistence surface is **not
yet frozen**. It will be established only after MISSION's requirements
are understood.

Detailed TEAM specification:

`docs/Lakshya_Team_Behavioural_Fingerprint.md`

------------------------------------------------------------------------

## MISSION

### What must this collective accomplish for the family?

MISSION connects collective behavioural evidence with the family's
purpose, goals and constraints.

MISSION is where purpose-driven interpretation enters, including:

- goal-specific suitability;
- composition percentages;
- allocation per goal; and
- other purpose/criterion-driven decisions.

MISSION should consume Team outputs rather than reaching backward into
raw Fund/NAV machinery.

The exact TEAM → MISSION contract is established through architectural
reasoning rather than assumed from lower-stage implementation details.

------------------------------------------------------------------------

## FUTURE ENVIRONMENT

### How should the system remain suitable as the family and world evolve?

FUTURE ENVIRONMENT considers continued suitability and evolution through
changing circumstances.

External reality is introduced at the layer where the architecture
genuinely earns the need for it rather than being prematurely injected
into FUND or TEAM.

------------------------------------------------------------------------

## Evidence Philosophy

Lakshya preserves depth.

**30,000 feet ↔ 3 feet**

The broad picture and the underlying evidence remain connected.

Observed is not inferred.
Unknown is not zero.

> **Compression can be useful. Compression cannot be allowed to erase
> meaning.**

A lower abstraction layer may reduce or organise information for the next
layer, but it must not import the next layer's semantics merely to
achieve that reduction.

### Calculation versus persistence

Lakshya distinguishes four different questions:

1. **What can a stage calculate?**
2. **What does the next stage actually consume?**
3. **What evidence must remain available for interpretation or audit?**
4. **What state deserves durable persistence?**

These questions are not interchangeable.

The distinction between FUND evidence and TEAM consumption is an example
of this discipline. Evidence can remain meaningful at its originating
stage without automatically becoming downstream state.

------------------------------------------------------------------------

## Architecture and Implementation

Lakshya follows:

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

The implementation exists to express the architecture, not replace it.

Versioned evidence is part of the architecture. Historical analytical
states are preserved rather than overwritten, with Git serving as the
historical ledger where durable analytical state has been deliberately
chosen.

------------------------------------------------------------------------

## Stage Specifications

The detailed architectural specifications currently include:

- `docs/Lakshya_Fund_Behavioural_Fingerprint.md`
- `docs/Lakshya_Team_Behavioural_Fingerprint.md`

Additional stage specifications will be introduced when the corresponding
architecture has been sufficiently established.
