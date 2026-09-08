# Lakshya Domain Model

**Status:** Authoritative domain model

**As of:** 2026-09-08

This document records the bounded-context boundaries, ubiquitous language, ownership rules, and cross-context contracts established during the Lakshya architecture elicitation. It is complementary to `docs/Lakshya_Architecture.md`: this document defines the domain boundaries; the Architecture document describes the wider production architecture and analytical stages.

---

# 1. Domain map

Lakshya has three bounded contexts.

```text
                         HUMAN
                           │
                           ▼
                          LPS
                   Lakshya Position System
                   "What capital do we actually have?"
                       │              │
                       │              │
                       ▼              ▼
                      LFS            LTS
             Lakshya Formation   Lakshya Transition
                  System              System
          "What formation should   "How do we move from
               we have?"             one to the other?"
                       │              ▲
                       └──────────────┘
```

The flow is deliberately not a serial pipeline. LPS is the factual upstream system. LFS consumes LPS formation evidence. LTS consumes both LPS transition evidence and LFS formation intent.

The governing principles are:

> **LPS observes. LFS forms. LTS transitions.**

> **Information is introduced at the layer that genuinely earns the need for it.**

> **A bounded context exposes what its consumer needs, not everything its producer happens to have.**

---

# 2. Bounded contexts

## 2.1 LPS — Lakshya Position System

**Native question:**

> **What capital do we actually have?**

LPS is the authoritative factual home for the family's investment world.

LPS owns:

- authoritative source evidence;
- normalized Transactions;
- historical transaction evidence;
- first-class Positions;
- NAV observations and valuation history;
- Position valuation at an observation date; and
- human-maintained Position → Purpose attribution.

LPS does not own:

- fund selection;
- behavioural Fund analysis;
- TEAM, COMPOSITION, MISSION, FINAL, or TARGET formation;
- transition decisions; or
- transaction execution.

### Position identity

An established Position is identified by:

```text
Investor + Folio + ISIN
```

A Position has exactly one Purpose attribution once accepted into LPS.

A Purpose may have zero, one, or many Positions.

Therefore:

```text
Purpose with zero Positions  → valid
Position with zero Purpose   → not valid as an accepted LPS attribution
```

### Purpose

Purpose is a family domain concept. The family defines its identity and desired state. LPS records the accepted relationship between a Position and a Purpose and can derive Purpose capital from Position valuations.

LPS does not infer Purpose attribution from fund identity, folio identity, transaction type, or target formation.

---

## 2.2 LFS — Lakshya Formation System

**Native question:**

> **What investment formation should we have?**

LFS is the analytical formation bounded context.

Its internal stages are:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL → TARGET
```

These are stages inside LFS, not separate bounded contexts.

LFS owns:

- behavioural Fund evidence;
- Fund Fingerprints;
- Fund-level pruning between FUND and TEAM;
- TEAM formation;
- COMPOSITION formation and fingerprints;
- MISSION suitability analysis;
- FINAL compromise selection; and
- TARGET formation implied by reviewed Purpose decisions and selected FINAL Compositions.

LFS does not own:

- CAS/source parsing;
- actual family Positions;
- transaction history as a factual source;
- tax/transition mechanics;
- folio creation;
- transaction execution; or
- Position-level transition instructions.

Fund Fingerprint is an LFS analytical intermediate. It is not an LPS fact and is not a cross-context contract.

---

## 2.3 LTS — Lakshya Transition System

**Native question:**

> **Given what LPS tells us actually exists, and what LFS says we should have, how can we move from one to the other?**

LTS is the constrained transition bounded context.

LTS owns:

- comparison of factual Positions against formation intent;
- transition feasibility analysis;
- transition simulations;
- sequencing analysis;
- transition proposals; and
- reconciliation support for proposals after execution.

LTS does not own:

- TARGET selection;
- a second portfolio optimizer;
- factual Position state;
- Purpose policy;
- source parsing;
- automatic transaction execution; or
- authority to manufacture missing transaction, tax, cost, or folio facts.

Where genuinely evidenced, LTS may reason about constraints such as lock-ins, acquisition-date tax consequences, exit loads, transaction costs, liquidity, minimum transaction constraints, and SIP/STP/SWP sequencing. Each such constraint must be earned by source evidence.

---

# 3. The five cross-context contracts

These contracts are the primary architectural boundaries between the three systems and the human/external-world boundary.

## Contract 1 — Formation Evidence

**LPS → LFS**

LPS supplies a purpose-built formation evidence projection:

```text
Formation Evidence
├── Funds represented by Positions
└── NAV observations / history
```

A reviewer may separately supply `potential_funds_in_scope` for funds not represented by existing Positions. This is reviewer input, not an LPS factual assertion.

The contract does not expose Transactions, Position → Purpose attribution, transition information, or LTS mechanics.

LFS performs its own Fund Fingerprint construction and Fund-level Pareto pruning inside the LFS boundary.

---

## Contract 2 — Transition Evidence

**LPS → LTS**

```text
Transition Evidence
├── Positions
│   ├── Investor
│   ├── Folio
│   ├── ISIN
│   ├── Units
│   └── valuation observation
├── Transactions
│   └── relevant historical transaction evidence
├── Position → Purpose attribution
└── transition-relevant Fund metadata
```

Transactions themselves are the acquisition/history evidence. No separate acquisition-evidence domain object is introduced unless implementation later earns one.

Fund metadata crossing this boundary is limited by actual LTS consumption. Broader LPS metadata remains technical debt until LTS is fully implemented and its dependencies can be reviewed.

The contract does not expose Fund Fingerprints, TEAM, COMPOSITION, MISSION, FINAL, TARGET, tax calculations, transition recommendations, or transaction instructions.

---

## Contract 3 — Formation Intent

**LFS → LTS**

LFS supplies the selected Composition for each Purpose:

```text
Formation Intent
├── Purpose A → Composition A
├── Purpose B → Composition A
├── Purpose C → Composition A
├── Purpose D → Composition A
├── Purpose E → Composition A
└── Purpose F → Composition B
```

The Purpose-level mapping is preserved even when several Purposes select the same Composition.

A Composition contains its Team and fund weights. Contract 3 does not assign Investor, Folio, Position IDs, tax treatment, or transaction actions.

---

## Contract 4 — Transition Proposal

**LTS → Human / Staging**

LTS produces one or more candidate transition simulations. Each contains:

```text
Transition Proposal
├── proposed Position transformation
└── proposed Purpose-attribution transformation
```

A proposed Position may use:

```text
Investor + ISIN + Folio: NEW
```

`NEW` is a proposal marker, not a factual identity and not a fabricated folio number.

The proposal is non-authoritative. It does not mutate LPS and does not execute transactions.

Multiple simulations may coexist. The reviewer selects which proposal, if any, to effect.

LTS does not introduce an `Action` abstraction merely for implementation convenience. Such an abstraction requires a separately demonstrated need.

---

## Contract 5 — Reconciliation / Promotion

**Human + new source evidence → LPS**

After the reviewer effects a selected transition, a subsequent MyCAMS import supplies new authoritative evidence. LPS reconstructs the resulting factual Positions.

The reconciliation workflow then:

1. automatically detects factual changes and candidate matches to the staged proposal;
2. identifies newly observed Positions, including real folios corresponding to proposal `NEW` markers;
3. presents the proposed Purpose attribution as a reviewer choice; and
4. records the reviewer-accepted Purpose attribution in LPS.

The division is deliberately:

> **Automatic reconciliation. Human attribution acceptance.**

Position facts become authoritative through external evidence and LPS observation.

Purpose attribution becomes authoritative through explicit human acceptance.

Therefore:

> **LTS proposes. External evidence establishes Positions. The human establishes Purpose attribution. LPS records the resulting factual state.**

---

# 4. Ubiquitous language

| Term | Meaning | Owner |
|---|---|---|
| **Transaction** | A factual investment event represented by authoritative source evidence | LPS |
| **Position** | Capital identified by Investor + Folio + ISIN and established from transactions | LPS |
| **Purpose** | Family-defined investment purpose | Family / represented in LPS |
| **Purpose Attribution** | Accepted relationship between a Position and a Purpose | LPS |
| **Fund Fingerprint** | LFS behavioural analytical intermediate for an individual Fund | LFS |
| **Team** | Singleton/pair/trio of Funds | LFS |
| **Composition** | Team + complete weights | LFS |
| **MISSION** | Purpose-facing analytical stage assessing whether a Composition can serve a Purpose | LFS |
| **FINAL** | Practical compromise selection among qualified MISSION Compositions | LFS |
| **TARGET** | Formation implied by reviewed Purpose decisions and selected FINAL Compositions | LFS |
| **Transition Evidence** | LPS projection consumed by LTS to understand factual Positions and relevant history | LPS → LTS |
| **Formation Intent** | Purpose → selected Composition mapping supplied by LFS | LFS → LTS |
| **Transition Proposal** | Non-authoritative candidate transformation produced by LTS | LTS |
| **NEW** | Proposal marker indicating that the real folio does not yet exist in the proposed Position identity | LTS |
| **Reconciliation** | Automatic matching of newly observed factual evidence against a transition proposal | LPS / workflow |
| **Promotion** | Human acceptance of Purpose attribution after reconciliation | LPS |

---

# 5. Non-negotiable domain invariants

1. **LPS observes. LFS forms. LTS transitions.**
2. Observed is not inferred.
3. Unknown is not zero.
4. One established Position maps to exactly one Purpose.
5. One Purpose may have zero, one, or many Positions.
6. A Purpose may exist before any Position is assigned to it.
7. Fund Fingerprints belong entirely inside LFS.
8. LTS never chooses the TARGET formation.
9. LTS never mutates factual LPS Positions during simulation.
10. `NEW` is never a factual folio identity.
11. External source evidence establishes Position facts.
12. Human acceptance establishes Purpose attribution.
13. LTS proposals are non-authoritative.
14. LPS remains the authoritative factual home of Transactions, Positions, and accepted Purpose attribution.
15. A downstream convenience must not silently alter an upstream analytical contract.
16. Domain concepts are not invented solely for implementation convenience.

---

# 6. Architectural consequence

The contracts are not merely data-transfer schemas. They are the points at which Lakshya's bounded contexts meet.

Each contract deliberately carries the smallest semantic surface needed by its consumer:

```text
LPS ── Formation Evidence ──► LFS
LPS ── Transition Evidence ─► LTS
LFS ── Formation Intent ────► LTS
LTS ── Transition Proposal ─► Human
Human + evidence ───────────► LPS
```

This is the defining domain boundary of Lakshya.

When a new requirement appears, the first question is not "where can we put this field?" It is:

> **Which bounded context genuinely owns this knowledge, and which contract earns the need for it?**

That question is the primary guard against domain leakage and accidental re-centralization.
