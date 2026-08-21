# Lakshya

Lakshya is a family-oriented investment architecture for understanding,
constructing and evolving a portfolio over a lifetime and beyond.

## Fundamental Architecture

``` text
FUND → TEAM → MISSION → FUTURE ENVIRONMENT
```

Each stage consumes the understanding built below it and asks a
higher-order question.

> **Aggregation gives us the structural flow.\
> The questions give us the meaning of the flow.**

------------------------------------------------------------------------

## FUND

### What kind of teammate is this fund?

FUND establishes the observed behavioural character of an individual
fund.

Its behavioural fingerprint has three primary dimensions:

-   **Elevation** --- participation in prosperity
-   **Protection** --- severity of adversity
-   **Resilience** --- the journey after adversity begins

The Fund stage is descriptive, not prescriptive. It establishes
evidence; it does not decide whether Lakshya should own the fund.

### Fund-stage evidence flow

``` text
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

TEAM answers:

> **Who stands together?**

TEAM forms collective behavioural structures from Fund fingerprints.
Team formation is based on Fund-level behavioural evidence, not on
family goals, allocation, or suitability.

The established structural constraint is:

-   singleton
-   pair
-   trio

with a maximum of **3 members per Team**.

TEAM is descriptive rather than prescriptive.

The possible Team universe can become combinatorially large. TEAM
therefore performs the necessary abstraction-preserving bulk work to
pass only the necessary / eligible Teams onward to MISSION.

> **TEAM may determine which Teams are necessary to pass onward; TEAM
> must not decide what MISSION wants.**

This reduction must remain within the TEAM abstraction boundary. TEAM
must not import:

-   goal suitability;
-   goal-specific criteria;
-   composition percentages;
-   allocation;
-   portfolio-purpose decisions; or
-   higher-order MISSION entities

merely to reduce its own output.

Team evidence must preserve sufficient collective journey/form
information beneath any reduced representation so that MISSION receives
meaningful evidence rather than an over-compressed label.

------------------------------------------------------------------------

## MISSION

### What must this collective accomplish for the family?

MISSION connects the collective with the family's purpose, goals and
constraints.

MISSION is where purpose-driven interpretation enters, including:

-   goal-specific suitability;
-   composition percentages;
-   allocation per goal; and
-   other purpose/criterion-driven decisions.

MISSION consumes Team outputs rather than reaching backward into raw
Fund/NAV machinery.

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

Observed is not inferred.\
Unknown is not zero.

> **Compression can be useful. Compression cannot be allowed to erase
> meaning.**

A lower abstraction layer may reduce or organise information for the
next layer, but it must not import the next layer's semantics merely to
achieve that reduction.

------------------------------------------------------------------------

## Architecture and Implementation

Lakshya follows:

``` text
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
historical ledger.

------------------------------------------------------------------------

## Current FUND Implementation State

The FUND stage is implemented, tested and validated.

The Fund pipeline establishes a version-linked relationship between NAV
evidence and Fund fingerprints:

``` text
NAV artifact vN
      ↓
Fund fingerprint based on NAV artifact vN
```

Fingerprint lifecycle:

``` text
no fingerprint
      ↓
   created

older fingerprint
      ↓
   appended

current fingerprint
      ↓
   current
```

A partially stale state can therefore be reconciled without destroying
historical analytical state or unnecessarily rebuilding upstream
evidence.

The completed Fund-stage implementation has been validated by:

-   72 passing tests;
-   real processing of all 17 admissible Funds;
-   reconciliation of stale fingerprints;
-   a subsequent idempotent run in which all 17 Funds reported
    `fingerprint current`.

The completed FUND milestone is committed in Git.

## What Comes Next

> **FUND → TEAM**

Before implementation, TEAM's exact input/output contract and its
abstraction-preserving reduction boundary should be established from the
Fund outputs already earned.
