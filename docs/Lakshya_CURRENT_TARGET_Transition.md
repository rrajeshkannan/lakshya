# Lakshya — CURRENT → TARGET Transition Architecture

**Status:** Architectural boundary established; source archaeology pending

**Stage:** Separate post-Historical-Snapshot architecture

**As of:** 2026-09-07

This document establishes the boundary and responsibilities of the next Lakshya stage. It deliberately does **not** define the CURRENT data schema, transition optimizer, tax model, redemption engine, or transaction execution workflow. Those must be earned from the actual portfolio/account-source material before implementation.

The authoritative analytical architecture remains:

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
  ↓
FAMILY ARCHITECTURE VALIDATION
  ↓
PURPOSE STAGING
  ↓
HISTORICAL SNAPSHOT
```

The next stage begins separately:

```text
ACTUAL CURRENT HOLDINGS
        +
ALREADY-DECIDED TARGET ARCHITECTURE
        ↓
CURRENT → TARGET TRANSITION ANALYSIS
        ↓
HUMAN EXECUTION PLAN
```

---

## 1. Why this is a separate architecture

The analytical pipeline has already answered the investment-selection question for the annual review.

FINAL has selected the strongest practical compromise for each Purpose from the qualified Composition population. Purpose Staging may subsequently change Purpose requirements and funding inputs under explicit human control.

Neither stage answers:

> **What does the family actually own today, and how should that existing state be changed to reach the reviewed target state?**

That is a different question because actual ownership carries information that the analytical pipeline deliberately does not need:

- actual scheme/fund holdings;
- units and current value;
- account / folio context where relevant;
- acquisition information where available;
- source-specific holding identity;
- economic constraints attached to changing an existing holding.

This information must therefore enter at the transition boundary rather than being imported backward into FUND, TEAM, COMPOSITION, MISSION, or FINAL.

> **Information should be introduced at the layer that genuinely earns the need for it.**

---

## 2. The three states must remain distinct

### 2.1 Analytical CURRENT

The annual Lakshya review may contain a current analytical architecture: the Purpose decisions and their selected FINAL Compositions.

This is evidence of **what Lakshya currently recommends as the reviewed architecture**.

It is not proof of what the family currently owns.

### 2.2 Economic CURRENT

Economic CURRENT is the observed real-world portfolio state derived from actual portfolio/account records.

It answers:

> **What does the family actually own at the chosen observation date?**

This state must be source-derived. Lakshya must not infer actual units, values, folios, cost basis, or other holding facts from analytical outputs.

### 2.3 TARGET

TARGET is the post-review architecture implied by the already-completed Lakshya decision.

At the highest level:

```text
Purpose state
      ↓
selected FINAL Composition
      ↓
fund-level target weights
      ↓
TARGET holding architecture
```

TARGET is therefore a **consequence of an existing Lakshya decision**, not a new optimization problem.

---

## 3. Core transition relationship

The transition layer should reason from:

```text
CURRENT actual holdings
        +
TARGET desired architecture
        ↓
what already matches?
what can remain?
what differs?
what must change?
what constraints apply?
what sequence is feasible?
```

It must **not** become:

```text
CURRENT holdings
      ↓
new optimizer
      ↓
new portfolio decision
```

The latter would reopen a decision that FINAL has already earned and would blur the boundary between analytical selection and transaction planning.

---

## 4. Minimum responsibilities of the transition layer

The future transition architecture may legitimately answer:

1. **What do we own?**
2. **What target state has the reviewed Lakshya architecture specified?**
3. **Where do CURRENT and TARGET agree?**
4. **Where do they differ?**
5. **Which existing holdings can remain without changing the target architecture?**
6. **Which holdings require change?**
7. **What source-derived economic constraints affect those changes?**
8. **What transition sequence is feasible for human execution?**

The exact fields required to answer these questions are intentionally not fixed here.

---

## 5. Source archaeology comes first

Before defining a production CURRENT contract, inspect the actual portfolio/account material available to the family, especially the Geojit material already identified as a likely primary source.

The archaeology must determine, from the source itself:

- which holding identity fields are present;
- whether units are available;
- whether current value is available;
- whether transaction/acquisition information is available;
- whether cost information is available and at what granularity;
- whether account/folio identifiers are present and necessary;
- what observation date is represented;
- how multiple accounts or folios are represented;
- which fields are authoritative versus merely presentation fields;
- which required transition facts are **not** available from the source.

Only after that inspection should the **minimum sufficient CURRENT data contract** be written.

> **Do not design the schema from imagination when the source can tell us what it actually contains.**

---

## 6. Minimum sufficient means minimum

The first CURRENT contract should contain only information that is demonstrably needed by the transition questions.

It should not become a general-purpose personal-finance schema merely because the source contains additional fields.

Likewise, missing source information must remain explicitly missing. The transition layer must not silently manufacture:

- cost basis;
- acquisition dates;
- tax lots;
- exit costs;
- account semantics; or
- transaction constraints.

If a later transition question genuinely requires information not present in the primary source, that missing requirement should be surfaced explicitly and a second source can be introduced deliberately.

---

## 7. Target construction boundary

TARGET should be derived only after the source-derived CURRENT contract is understood.

The initial target construction should follow the already-established annual decision path:

```text
authoritative Purpose state
        ↓
FINAL selected Composition per Purpose
        ↓
Composition fund weights
        ↓
TARGET fund-level architecture
```

Any family-level aggregation needed for transition planning must preserve Purpose identity and fund identity rather than collapsing the target into an opaque score.

The transition layer must not invent new fund-selection criteria merely because CURRENT contains inconvenient holdings.

---

## 8. Economic constraints belong here — when actually evidenced

Redemption, cost, tax, exit, and sequencing constraints are transition concerns **only when the underlying facts are available and applicable**.

The architecture therefore permits future transition analysis to consider:

```text
CURRENT holdings
      ↓
source-derived constraints
      ↓
feasible transition actions
      ↓
TARGET
```

But the existence of a conceptual category does not justify inventing fields or assumptions for it.

For example, if a source does not contain reliable acquisition information, the system must not fabricate a cost basis merely to make a transition calculation appear complete.

---

## 9. Human execution boundary

Lakshya may calculate and present a transition analysis, but the final transaction decision remains outside automatic execution.

The intended boundary is:

```text
Lakshya
  ↓
CURRENT observation
  ↓
TARGET consequence
  ↓
transition analysis
  ↓
human review / execution
```

Lakshya does not automatically redeem, purchase, switch, or otherwise transact on the family's behalf.

This preserves the same architectural principle already established at the annual-review boundary:

> **The reviewer controls the terrain; Lakshya calculates the consequences.**

---

## 10. Explicit non-responsibilities

The CURRENT → TARGET stage does not:

- reopen FUND admission;
- redefine TEAM formation;
- alter Composition weights because of current holdings;
- rerun MISSION merely because a transition is inconvenient;
- replace a FINAL winner with a newly optimized fund;
- encode hidden Purpose priorities;
- assume that analytical CURRENT equals economic CURRENT;
- manufacture missing tax/cost/transaction information;
- execute transactions automatically; or
- become a generic portfolio optimizer.

---

## 11. Stage sequence

The intended next-stage sequence is deliberately small:

```text
HISTORICAL SNAPSHOT
        ↓
source archaeology
        ↓
minimum sufficient CURRENT contract
        ↓
source-derived CURRENT observation
        ↓
TARGET construction from existing reviewed decisions
        ↓
CURRENT vs TARGET comparison
        ↓
transition constraints / feasibility
        ↓
human transition plan
```

There is no optimizer in this sequence.

If evidence later demonstrates that an additional analytical layer is genuinely required, that layer must be introduced explicitly rather than hidden inside transition planning.

---

## 12. Current status

Completed before this stage:

- analytical production through FINAL;
- Family Architecture Validation;
- Purpose Staging architecture;
- Historical Snapshot boundary;
- separation of analytical decision from transaction execution.

Next task:

> **Inspect the actual portfolio/account-statement material and derive the minimum sufficient CURRENT data contract.**

No production CURRENT schema, TARGET optimizer, or transaction engine should be implemented before that archaeology is complete.
