# Lakshya Production Architecture

**Status:** Authoritative production architecture

**Release:** FINAL / Compromise Programming v1

**As of:** 2026-09-08

This document defines the architectural boundaries of Lakshya. Execution detail belongs in `docs/Lakshya_Pipeline_Sequence.md`; practical operation belongs in `docs/Lakshya_HowTo.md`.

---

# 1. Architectural statement

Lakshya is a **family-specific investment-engineering system**, not a generic optimizer. Its three bounded systems answer three different questions:

```text
LPS — Lakshya Position System
What capital do we actually have?

LFS — Lakshya Formation System
What investment formation should we have?

LTS — Lakshya Transition System
How do we move from CURRENT to TARGET?
```

The governing principles are:

> **LPS observes. LFS forms. LTS transitions.**

> **Information should be introduced at the layer that genuinely earns the need for it.**

> **Compute once. Persist immediately. Reuse forever.**

The architecture separates factual observation, analytical formation, family review, historical memory, and transition planning. No later layer is allowed to quietly become an earlier layer's optimizer.

---

# 2. Bounded contexts and contracts

| System | Native question | Owns | Does not own |
|---|---|---|---|
| **LPS** | What capital do we actually have? | source evidence, Transactions, Positions, NAV/valuation, factual CURRENT | fund selection, Purpose inference, TARGET, transition decisions |
| **LFS** | What investment formation should we have? | FUND→TEAM→COMPOSITION→MISSION→FINAL→TARGET | CAS parsing, actual holdings, transition mechanics, execution |
| **LTS** | How do we move CURRENT→TARGET? | constrained comparison, feasibility, sequencing, transition plan | TARGET selection, new portfolio optimization, transaction execution |

The principal hand-offs are:

```text
LPS → CURRENT + factual history needed by transition
LFS → TARGET from reviewed formation decisions
```

LFS and LTS do not depend on parser-specific CAS schemas. LPS remains the source of factual holdings and transaction history.

---

# 3. LPS — Lakshya Position System

## 3.1 Native question

> **What capital do we actually have?**

LPS owns the family's factual investment world. It observes; it does not form the target architecture.

Its responsibilities are:

- ingest authoritative source evidence;
- parse, normalize, and validate actual Transactions;
- maintain historical transaction evidence;
- reconstruct first-class Positions;
- maintain NAV observations and valuation history;
- derive valuation at an observation date; and
- expose Economic CURRENT to downstream consumers.

## 3.2 Core data model

The LPS data model is deliberately a collection of **Transactions and Positions**:

```text
LPS
│
├── Transaction
├── Transaction
├── ...
│
└── Position
    ├── Position Identity
    │   ├── Investor
    │   ├── Folio
    │   └── ISIN
    ├── Units
    └── valuation observation when applied
        ├── NAV
        ├── NAV observation date
        ├── valuation as-of date
        └── Market Value
```

Position identity is:

```text
Investor + Folio + ISIN
```

Historical Transactions belong to the Position identified by that identity.

There is **no Portfolio dimension**. There is **no `CurrentState` domain object**. There is no separate derived `CanonicalTransaction` concept: at the LPS boundary, Transactions are the factual transaction records.

APIs or consumer views may use names such as CURRENT when useful, but those names do not create additional domain entities.

## 3.3 Purpose mapping

Purpose mapping is a human-maintained relationship over Positions:

```text
one Position → exactly one Purpose
one Purpose  → zero, one, or many Positions
```

LPS aggregates actual Position market values by Purpose when that view is requested. It does not infer or invent Purpose mapping, and it does not automatically trim an over-target Purpose.

Unmapped Positions remain visible and require human attention.

## 3.4 Temporal semantics

LPS keeps two boundaries explicit:

```text
transaction_through_date
valuation_as_of_date
```

They need not be the same date.

For example, a full-history CAS may end earlier than the intended valuation observation date. The transaction boundary remains factual; the valuation uses the applicable NAV observation for the requested as-of date.

NAV write semantics are sparse:

- store actual recorded observations;
- do not manufacture holiday/weekend observations;
- do not interpolate missing calendar days.

NAV read semantics are as-of semantics:

```text
NAV as of X
= latest recorded NAV observation on or before X
```

This convention is already native to Lakshya's historical timeline calculations and tests.

## 3.5 Conservative factual boundary

The current LPS factual Fund world deliberately retains only earned/consumed identity information:

```text
Fund identity / ISIN
Scheme Name
AMC
actual Transaction history
Position history
Units
NAV observations / history
Valuation
CURRENT view
```

Scheme Name and AMC remain useful factual/reference information. Generic scheme fields such as category or benchmark are not promoted merely because they exist in older models. A field earns elevation only when a downstream contract genuinely consumes it.

The family Fund scope source remains:

```text
data/fund/funds_in_scope.csv
```

---

# 4. LFS — Lakshya Formation System

## 4.1 Native question

> **What investment formation should we have?**

LFS consumes the factual Fund world and forms the reviewed target architecture through the established analytical stages:

```text
FUND → TEAM → COMPOSITION → MISSION → FINAL → TARGET
```

These are **stages inside LFS**, not separate bounded systems.

## 4.2 FUND

> **What kind of teammate is this fund?**

FUND establishes observed individual-fund behaviour from historical NAV evidence. Elevation and Protection are behavioural evidence families, not forecasts.

The explicit scope source is `data/fund/funds_in_scope.csv`. The 8-year lived-history rule applies to POTENTIAL/new-entry Funds; CURRENT Funds may be younger. CURRENT/POTENTIAL are admission concepts, not hidden downstream quality preferences. Regular versus Direct is not a Lakshya analytical distinction.

FUND does not know Purpose suitability, allocation, or FINAL decisions.

## 4.3 TEAM

> **What kind of collective do these teammates form?**

TEAM forms deterministic singleton, pair, and trio candidates, maximum size 3. Collective evidence is formed from constituent Fund histories rather than by averaging Fund scores first.

The declared comparator surface is:

```text
28 Elevation + 12 Protection = 40 dimensions
```

TEAM uses exact weak Pareto non-dominance:

```text
Elevation  → UP
Protection → DOWN
```

TEAM is elimination, not ranking. It must not import MISSION semantics merely to shrink its universe.

## 4.4 COMPOSITION

> **Where does capital sit within a collective?**

A Composition is **Team + complete weights**.

```text
singleton: 100%
pair:       19 allocations at 5% increments
trio:      171 allocations at 5% increments
```

Composition fingerprints are durable, reusable evidence containing identity, weights and behavioural evidence including NAV, Elevation and Protection. The global Composition frontier uses the same 40-D surface.

Composition checkpoints use the durable, narrow Completion Index. It is a Composition checkpoint mechanism, not a generic artifact store.

## 4.5 MISSION

> **Can this Composition serve this Purpose?**

MISSION is the first stage where Purpose semantics enter the analytical contract.

Supported analytical horizons are:

```text
3Y / 5Y / 7Y / 10Y
```

The longest supported horizon not beyond the Purpose horizon is selected. For example:

```text
4Y → 3Y    6Y → 5Y    8Y → 7Y
9Y → 7Y   12Y → 10Y  13Y → 10Y
```

The logical sequence is:

```text
Global Composition frontier
        ↓
Achievability, when a finite target exists
        ↓
Protection-only frontier
        ↓
MISSION survivors
        ↓
Trajectory observation
```

Open-ended Purposes still receive Elevation, Protection and Trajectory; only Achievability is absent when no finite target exists. Trajectory is descriptive and does not currently eliminate a MISSION survivor.

## 4.6 FINAL

> **Among already-qualified MISSION Compositions, which is the strongest practical compromise?**

FINAL is production ordering, not another admission stage.

For selected horizon `H`:

```text
7 Elevation(H) + 12 native Protection
```

Zero-variance spokes are removed deterministically. Retained spokes are equally weighted and converted to population-relative desirability coordinates in `[0,1]`, with higher always better. The Utopia Point is the best observed value on each retained spoke.

```text
d(i,j) = 1 - x(i,j)
L2(i) = sqrt(sum(d(i,j)^2))
```

The smallest unweighted L2 distance is the production winner. L-infinity remains a worst-spoke diagnostic and participates in a joint `(L2, L∞)` frontier; there is no arbitrary L-infinity kill threshold.

FINAL also records:

- Lp winner sweep from 1.00 to 10.00 in 0.25 increments;
- leave-one-spoke sensitivity; and
- 5,000 deterministic population bootstrap resamples by default.

Robustness evidence describes stability; it does not override the primary winner.

## 4.7 TARGET

TARGET is not a new optimization stage. It is the fund-level formation implied by the already-reviewed Purpose state and selected FINAL Composition decisions:

```text
authoritative Purpose state
        ↓
selected FINAL Composition per Purpose
        ↓
Composition fund weights
        ↓
fund-level TARGET architecture
```

TARGET must not introduce new selection criteria merely because existing holdings are inconvenient.

---

# 5. Post-FINAL family review layers

These layers sit after FINAL and before the annual historical persistence boundary. They are deliberately **not optimization stages**.

```text
FINAL
  ↓
FAMILY ARCHITECTURE VALIDATION
  ↓
PURPOSE STAGING
  ↓
HISTORICAL SNAPSHOT
```

## 5.1 Family Architecture Validation

Native question:

> **Given the independent Purpose-level decisions together, where does family capital depend on common Funds or investment organizations?**

This is **attribution, not optimization**.

The core contract is:

```text
Purpose current capital
        ×
FINAL Composition fund weight
        =
Attributed capital
```

It aggregates Fund and AMC/ecosystem exposure while retaining Purpose breadth/dependency.

Its annual structured outputs are:

```text
family_capital_attribution.csv
family_fund_concentration.csv
family_amc_concentration.csv
family_purpose_dependency.csv
family_attribution_manifest.json
```

The layer does not:

- impose maximum Fund or AMC concentration;
- penalize common dependencies;
- alter FINAL winners;
- create substitute Compositions;
- optimize family allocation;
- declare a dependency safe/unsafe; or
- introduce transition-cost assumptions.

A discovered dependency is an observation. Whether the family should tolerate it is a later analytical question.

Integrity is fail-closed: malformed Purpose capital, duplicate/missing Fund metadata, malformed or non-100% Composition weights, unknown Fund ISINs, manifest mismatches, hash mismatches, and Purpose-level attribution non-reconciliation are errors.

## 5.2 Purpose Staging

Purpose Staging is a deliberately small **human-in-the-loop reconciliation workspace**. It does not alter FUND, TEAM, COMPOSITION, MISSION, FINAL, or the selected FINAL Composition.

The reviewer controls:

- `value` — current capital;
- `monthly_plan` — monthly contribution;
- `desired` — target;
- `due` / `analytical_horizon_years` — horizon;
- `capital_acquire_pct`; and
- `sip_acquire_pct`.

The accounting contract is:

```text
Purpose reduction → common pool
pool acquisition  → another Purpose
```

Acquisition percentages use the same pool base at the start of the acquisition phase for that turn; they are not applied sequentially to a shrinking pool.

The reviewer cannot silently create capital or SIP by increasing `value` or `monthly_plan`. Changes to `desired` or horizon change the analytical requirement; they do not manufacture a cash release.

The authoritative `data/purpose/purposes.csv` remains unchanged until explicit COMMIT. COMMIT requires reviewer satisfaction and both pools equal to zero; the authoritative file is backed up before promotion.

---

# 6. Historical Snapshot

Historical Snapshot is a **human-controlled Git persistence boundary**, not an automatic snapshot engine.

After Purpose Staging COMMIT, the reviewer inspects intended annual changes and commits the reviewed state.

The durable record is primarily:

```text
data/fund/
data/purpose/
data/reviews/<as-of>/
```

Generated runtime output and forensic logs remain disposable/Git-ignored where configured.

Historical Snapshot is memory. It is not a transaction ledger and does not prove what the family currently owns.

---

# 7. Economic CURRENT and analytical CURRENT

Lakshya uses the word CURRENT in two different but explicitly separated contexts.

### Analytical CURRENT

What the reviewed Lakshya architecture currently says — Purpose decisions and selected FINAL formation. It is not evidence of actual units, folios, acquisition history, cost basis, or transaction constraints.

### Economic CURRENT

What the family actually owns at a chosen observation date, derived from LPS source evidence and valuation.

They must never be conflated.

```text
LPS → Economic CURRENT
LFS → TARGET
LTS → CURRENT vs TARGET transition analysis
```

CURRENT is a temporal valuation view. It is not a third domain object between Position and Transaction.

---

# 8. LTS — Lakshya Transition System

## 8.1 Native question

> **How do we move from CURRENT to TARGET?**

LTS begins after the reviewed annual snapshot and receives:

```text
LPS → Economic CURRENT + factual history
LFS → TARGET
```

Its intended reasoning is:

```text
CURRENT actual holdings
        +
TARGET desired architecture
        ↓
what matches?
what can remain?
what differs?
what must change?
what constraints apply?
what sequence is feasible?
        ↓
human transition plan
```

## 8.2 Source archaeology first

The first LTS task is **source archaeology, not schema design**. The actual portfolio/account material, including the identified Geojit material, must be inspected before a production CURRENT contract is defined.

The archaeology must establish what the source actually provides for:

- holding identity;
- units and current value;
- observation date;
- account/folio representation;
- acquisition/transaction information;
- cost information and granularity;
- source-authoritative versus presentation fields; and
- facts the source does not provide.

Missing facts remain missing. Lakshya must not manufacture cost basis, acquisition dates, tax lots, exit costs, account semantics, or transaction constraints.

## 8.3 Transition constraints

Where genuinely evidenced, LTS may eventually reason about:

- ELSS lock-in;
- acquisition-date tax consequences;
- STCG/LTCG implications;
- exit loads;
- transaction costs;
- liquidity;
- minimum transaction constraints;
- SIP/STP/SWP sequencing; and
- retain/exit/stage/switch/redeem/invest alternatives.

The source must earn each constraint. Absence of evidence is not permission to invent a value.

## 8.4 Human execution boundary

LTS may calculate a feasible transition analysis and present a plan. Final redemption, purchase, switch, or reinvestment actions remain human-controlled.

LTS must not:

- reopen FUND admission;
- redefine TEAM formation;
- alter Composition weights because of existing holdings;
- rerun MISSION merely because transition is inconvenient;
- replace a FINAL winner with a newly optimized fund;
- encode hidden Purpose priorities;
- equate analytical CURRENT with Economic CURRENT;
- invent missing tax/cost/transaction facts; or
- execute transactions automatically.

No production transition optimizer, tax engine, or transaction executor is authorized until source archaeology earns the need.

---

# 9. Shared event vocabulary

Lakshya uses a shared factual event vocabulary across observation and transition planning. The distinction is temporal, not linguistic: LPS records events that actually appear in authoritative evidence; LTS reasons about events that may occur until they become observed evidence.

The shared vocabulary includes:

```text
Purchase
Systematic Investment
Redemption
Switch In
Switch Out
Systematic Investment Rejection
STP-related
SWP-related
Stamp Duty
STT Paid
```

This gives Lakshya a common language between planning and observation without requiring LPS to know future events or LTS to own source parsing.

---

# 10. Production invariants

1. **Observed is not inferred.**
2. **Unknown is not zero.**
3. A Purpose horizon is not a demand for equivalent lived Fund history.
4. A calculation does not automatically become a downstream input.
5. Persisted evidence is reused rather than silently recomputed.
6. A higher stage consumes only information whose semantic need it has earned.
7. Experimental exploration may discover a rule; production codifies the rule explicitly.
8. A production rule changes only through a deliberate versioned release.
9. Rich evidence may be compressed for a higher-order boundary, but compression must not erase meaning.
10. A later-stage failure does not invalidate valid upstream evidence.
11. Family-level observation does not retroactively change an upstream winner.
12. Human Purpose priority is expressed through review inputs, not hidden system ranking.
13. Historical persistence records reviewed state; it is not an automatic transaction ledger.
14. Economic CURRENT is source-derived and must never be inferred from analytical outputs.
15. Transition planning must not become a second portfolio optimizer.
16. Domain concepts are not invented for implementation convenience.

Preferred lifecycle:

```text
compute → persist → validate → consume
```

---

# 11. What the architecture deliberately rejects

The current architecture does not promote the following into domain concepts without a separately earned need:

- Portfolio as a separate dimension;
- `CurrentState` as a Position wrapper;
- `CanonicalTransaction` as a second Transaction concept;
- generic Fund category/benchmark fields merely because they exist in legacy models;
- automatic Purpose trimming or residual redistribution;
- hidden Purpose priority rankings;
- Composition regions or clustering;
- subjective Purpose-specific spoke weighting;
- arbitrary L-infinity kill thresholds;
- future-return forecasts; or
- automatic transaction execution.

This is deliberate conservatism, not missing functionality.

---

# 12. Versioning and release discipline

The current production FINAL contract is:

```text
FINAL_CONTRACT_VERSION = 1
```

Changes to the decision rule, Purpose-facing surface, percentile semantics, primary norm, spoke weighting, L-infinity treatment, bootstrap semantics, p sweep, tie-breaking, or winner meaning require a deliberate production version change with updated tests and documentation.

The domain model is a first-class architectural artifact. Implementation convenience must not silently change it.
