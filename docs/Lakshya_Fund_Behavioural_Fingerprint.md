# Lakshya — Fund Behavioural Fingerprint

## Fund-stage philosophy and analytical specification

> **Purpose:** Define how Lakshya understands an individual fund before any portfolio-level decision is made.

---

## 1. Purpose

Lakshya evaluates a fund as a **behavioural entity**, not merely as a collection of return and risk statistics.

The purpose of the Fund Behavioural Fingerprint is to answer:

> **What kind of teammate is this fund?**

The fingerprint describes the fund's observed historical behaviour across prosperity and adversity.

It is **descriptive, not prescriptive**.

It does not determine whether Lakshya should own the fund. That decision belongs to a later portfolio-level layer.

---

# 2. The Fund Compass

The Fund Behavioural Fingerprint has three primary dimensions:

- **Elevation** — participation in prosperity
- **Protection** — severity of adversity
- **Resilience** — journey after adversity begins

### Elevation

> **How has this fund participated in prosperity across different investment horizons?**

### Protection

> **How severe is the adversity when it happens?**

### Resilience

> **What happens to the capital after adversity begins?**

These dimensions must remain analytically distinct.

---

# 3. Elevation

## 3.1 Question

> **How has this fund participated in prosperity across different investment horizons?**

Elevation describes the fund's observed prosperity terrain.

It does not attempt to predict future returns.

## 3.2 Primary evidence

Rolling-return distributions across:

- 3 years
- 5 years
- 7 years
- 10 years

For each horizon, retain:

- minimum
- P25
- median
- P75
- maximum
- mean
- dispersion
- positive-period frequency
- negative-period frequency
- latest observed rolling return

Full-period CAGR is retained as an **anchor**, not as a substitute for the rolling-return terrain.

## 3.3 Three aspects of Elevation

### Identified terrain

Where does the rolling-return distribution sit?

### Reality clustered around the terrain

How frequently do observed outcomes occur around that terrain?

### Width of terrain

How widely do observed outcomes extend from lower to upper extremes?

These aspects should remain visible rather than being compressed into one Elevation score.

## 3.4 Guardrails

Elevation evidence must not be interpreted as:

- proof of future returns
- proof of fund superiority
- proof of safety
- absence of adversity
- evidence that a higher-return fund is necessarily more suitable

In particular:

> **Positive long-horizon rolling returns do not imply absence of severe capital impairment.**

---

# 4. Protection

## 4.1 Question

> **How severe is the adversity when it happens?**

Protection describes the fund's historical **adversity terrain**.

Drawdowns are measured relative to the fund's **own previous high-water mark**.

This is deliberate.

At Fund stage, Lakshya asks:

> **If I continuously held this fund, what would my lived capital journey have looked like?**

It therefore does not require a benchmark to define whether the fund itself has experienced capital impairment.

Benchmark-relative behaviour is a separate analytical lens.

---

# 5. Protection evidence

## 5.1 Severity distribution

For every observed day, measure the fund's distance below its own high-water mark.

Retain:

- median severity
- P75
- P90
- P95
- P99
- maximum known severity

This creates a **severity map**.

## 5.2 Terrain frequency

Retain the proportion of observed days at or beyond descriptive landmarks:

- ≥5%
- ≥10%
- ≥15%
- ≥20%
- ≥25%
- ≥30%

These thresholds are **analytical landmarks**, not universal declarations of what constitutes "bad."

They answer:

> **How often has this fund historically inhabited at least this much adversity?**

## 5.3 Episode depth

Individual drawdown episodes retain their own depth.

This connects the distribution-level Protection picture to actual historical journeys.

## 5.4 Maximum severity

Maximum severity is retained as:

> **the deepest known point in the observed terrain.**

It is not treated as "the fund's risk."

---

# 6. Protection guardrails

Protection evidence must not be interpreted as:

- maximum severity being typical behaviour
- frequency being equivalent to severity
- daily downside volatility being equivalent to Protection
- Protection being equivalent to Resilience
- historical Protection being a guarantee of future Protection

The distinction is fundamental:

> **Protection describes the severity terrain; it does not describe how the fund travels through that terrain or whether it emerges from it.**

---

# 7. Resilience

## 7.1 Question

> **What happens to the capital after adversity begins?**

Resilience is observed through individual drawdown episodes.

Each episode represents a path:

```text
high-water mark
       ↓
     decline
       ↓
     trough
       ↓
    recovery
       ↓
high-water mark restored
```

---

# 8. Resilience evidence

## 8.1 Decline duration

> How long did the descent from the episode's peak to trough take?

Retain it independently.

A rapid decline and prolonged deterioration can reach the same depth while representing very different experiences.

## 8.2 Recovery duration

> How long did demonstrated recovery from the trough to the previous high-water mark take?

Recovery duration exists **only when recovery has actually been observed**.

An ongoing episode has:

```text
recovery_duration = unknown
```

not zero, not estimated.

## 8.3 Underwater duration

> How long did the fund remain below its previous high-water mark?

Underwater time is a genuine **path property**.

It must remain distinct from:

- depth
- decline duration
- recovery duration

## 8.4 Episode state

Every episode has an evidence state:

- `recovered`
- `ongoing`

This is an evidence-quality guardrail, not merely a display field.

## 8.5 Episode-level evidence

Individual episodes are retained at full useful resolution.

They provide the **3-foot view**.

Summary statistics provide the **30,000-foot view**.

Both are necessary.

---

# 9. Resilience summary evidence

Retain:

- episode count
- recovered count
- ongoing count
- median decline duration among recovered episodes
- median recovery duration
- median underwater duration among recovered episodes
- median underwater duration among ongoing episodes
- episode depth
- individual episode records

Recovered and ongoing populations must not be silently mixed when calculating recovery-related statistics.

---

# 10. Resilience guardrails

Resilience evidence must not be interpreted as:

- deep drawdown = poor resilience
- fast recovery = strong Protection
- long recovery = permanently weak fund
- one recovery episode = inherent resilience
- historical recovery = future recovery
- ongoing episode = failed recovery

Most importantly:

> **"Recovered" means that recovery was observed for that historical episode. It does not mean the fund is inherently resilient.**

And:

> **"Ongoing" means that the recovery story is not yet observable in the available history.**

---

# 11. Supporting evidence

## Downside RMS

Measures:

> **How violently have negative daily movements varied?**

It is retained as supporting descriptive evidence.

It does **not** represent Protection.

Daily downside intensity and path-level drawdown terrain can differ materially.

## Individual episode records

These are retained as underlying evidence rather than being treated as a compact compass metric.

They allow Lakshya to move from:

> **30,000 feet → 3 feet**

when deeper investigation is warranted.

---

# 12. Optional analytical lenses

The following remain available but do not belong to the foundational Fund Compass:

- benchmark-relative upside capture
- benchmark-relative downside capture
- Sortino
- Calmar
- risk-free-rate-dependent measures
- benchmark comparisons
- category-specific benchmark mappings

These answer narrower analytical questions.

They must not be allowed to redefine intrinsic fund behaviour.

In particular:

> **A benchmark is an analytical lens, not an intrinsic property of the fund.**

---

# 13. Compression principle

Lakshya adopts the following principle:

> **Compression can be useful. Compression cannot be allowed to erase meaning.**

Therefore:

> **Do not collapse multidimensional behaviour into one number prematurely.**

Where useful, summaries may be derived from richer underlying evidence.

But the underlying evidence must remain available.

The preferred information flow is:

```text
DAILY OBSERVATIONS
       ↓
ROLLING WINDOWS / EPISODES
       ↓
DISTRIBUTIONS / SUMMARIES
       ↓
FUND COMPASS
```

rather than:

```text
DAILY OBSERVATIONS
       ↓
ONE SCORE
       ↓
DECISION
```

---

# 14. Evidence-state principle

Evidence quality is not another behavioural dimension.

It is a **guardrail around what Lakshya is permitted to conclude**.

The system must distinguish:

> **observed ≠ inferred**

and:

> **recovered ≠ ongoing**

Unknown quantities remain unknown.

The engine must not manufacture completeness for the sake of numerical convenience.

---

# 15. Fund-level boundary

The Fund Behavioural Fingerprint answers:

> **What kind of teammate is this fund?**

It does **not** answer:

> **Should Lakshya own it?**

That requires interaction with other funds and with the family's goals.

Therefore:

```text
FUND
  │
  ├── Elevation
  ├── Protection
  └── Resilience
          │
          ↓
"What kind of teammate is this?"
```

Only later:

```text
FUND → TEAM → MISSION → FUTURE ENVIRONMENT
```

Fund-level evidence must not be contaminated by assumptions that belong to those later layers.

---

# 16. The Fundamental Fund Compass

The entire Fund stage can be stated in three sentences:

> **Elevation:** How has this fund participated in prosperity?

> **Protection:** How severe is the adversity when it happens?

> **Resilience:** What happens to the capital after adversity begins?

And underneath them:

> **Evidence quality tells us how confidently we are allowed to interpret the observed story.**

That is the **Fund Behavioural Fingerprint**.

---

# 17. Implementation philosophy

The production code should preserve the reasoning behind the architecture, not merely implement calculations.

Comments should explain **why** a non-obvious design choice exists, especially where a seemingly simpler alternative would change the meaning of the evidence.

Important architectural decisions to preserve in comments include:

- why drawdowns use the fund's own high-water mark
- why daily observations are retained
- why episodes are preserved rather than reduced immediately to summary statistics
- why recovered and ongoing episodes are separated
- why benchmark-relative measures remain optional lenses
- why multidimensional evidence is not collapsed into a single score
- why unknown evidence remains unknown

The intended hierarchy is:

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

The codebase should remain understandable decades after its original construction.

---

## Fund-stage completion criterion

The Fund stage is complete when the implementation can:

1. preserve the underlying historical evidence;
2. calculate the defined Fund Behavioural Fingerprint consistently;
3. distinguish observed evidence from inference;
4. preserve the distinction between Elevation, Protection and Resilience;
5. retain enough underlying detail to investigate a summary result;
6. pass tests that encode the philosophical guardrails; and
7. describe funds without prematurely deciding which funds belong in the portfolio.

Only then should the architecture cross the boundary from:

> **FUND → TEAM**
