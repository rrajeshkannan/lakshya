# Lakshya — Fund Behavioural Fingerprint

## Purpose

The Fund stage understands an individual fund as a **behavioural entity**, not merely as a collection of return and risk statistics.

Its question is:

> **What kind of teammate is this fund?**

The Fund Behavioural Fingerprint describes observed historical behaviour across prosperity and adversity.

It is **descriptive, not prescriptive**. It does not determine whether Lakshya should own the fund.

---

---

# The Fund Compass in Three Questions

> **Elevation:** How has this fund participated in prosperity?

> **Protection:** How severe is the adversity when it happens?

> **Resilience:** What happens to the capital after adversity begins?

Together, they form the **Fund Behavioural Fingerprint**.

And beneath them:

> **Evidence quality tells us how confidently we are allowed to interpret the observed story.**

---

# The Fund Evidence Foundation

The Fund Compass is built from observed NAV history.

```text
NAV observations
       ↓
canonical NAV history
       ↓
Fund evidence
       ↓
Fund Behavioural Fingerprint
```

The underlying evidence remains available so that a summary can be investigated at greater depth.

The preferred direction is:

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

# The Fund Compass

The Fund Behavioural Fingerprint has three primary dimensions:

- **Elevation** — participation in prosperity
- **Protection** — severity of adversity
- **Resilience** — the journey after adversity begins

They remain analytically distinct.

```text
Elevation
    ↓
prosperity terrain

Protection
    ↓
adversity terrain

Resilience
    ↓
journey through adversity
```

Together they describe the Fund's behavioural character:

```text
prosperity / rising-return terrain
            ↓
        Elevation

adversity / falling-capital journey
            ↓
   Protection → Resilience
```

Elevation follows rolling-return behaviour across the available history.

Protection and Resilience follow the fund's drawdown journey from its own high-water marks.

---

# Elevation

## Question

> **How has this fund participated in prosperity across different investment horizons?**

Elevation describes the fund's observed prosperity terrain.

It does not forecast future returns.

## Primary evidence

Rolling-return distributions are observed across:

- 3 years
- 5 years
- 7 years
- 10 years

For each available horizon, the evidence preserves the observed distribution, including:

- minimum
- P25
- median
- P75
- maximum
- mean
- standard deviation
- positive-period frequency
- negative-period frequency
- latest observed rolling return

A horizon may be unavailable when the NAV history is insufficient.

> **Insufficient evidence is not zero evidence.**

## Reading the terrain

Elevation should preserve three aspects:

### Identified terrain

Where does the rolling-return distribution sit?

### Reality around the terrain

How frequently do observed outcomes occur across that distribution?

### Width of terrain

How widely do observed outcomes extend from lower to upper extremes?

These should remain visible rather than being compressed into one Elevation score.

## Continuity of Elevation

Elevation does not reset at any point in the NAV history.

Rolling-return observations are calculated continuously across the available NAV history.

## Guardrails

Elevation evidence is not:

- proof of future returns;
- proof of fund superiority;
- proof of safety;
- proof that adversity was absent; or
- evidence that a higher-return fund is necessarily more suitable.

In particular:

> **Positive long-horizon rolling returns do not imply absence of severe capital impairment.**

---

# Protection

## Question

> **How severe is the adversity when it happens?**

Protection describes the fund's historical **adversity terrain**.

Drawdowns are measured relative to the fund's **own previous high-water mark**.

At Fund stage, Lakshya asks:

> **If I continuously held this fund, what would my lived capital journey have looked like?**

No benchmark is required to establish intrinsic Protection evidence.

Benchmark-relative behaviour is a separate analytical lens.

---

## Protection evidence

### Severity distribution

The severity distribution describes the observed terrain through:

- median severity
- P75
- P90
- P95
- P99
- maximum known severity

This creates a **severity map**.

### Terrain frequency

The terrain frequency describes the proportion of observed NAV observations at or beyond common descriptive landmarks:

- ≥5%
- ≥10%
- ≥15%
- ≥20%
- ≥25%
- ≥30%

These are analytical landmarks, not universal declarations of what constitutes "bad".

They answer:

> **How often has this fund historically inhabited at least this much adversity?**

Terrain Frequency measures observed exposure to a severity level across NAV observations. It is not an episode count.

Both the descent into and recovery through a given severity contribute observations.

For example, if an episode passes through 15% drawdown on the way down and later passes through 15% again on the way back, both observations contribute to the ≥15% frequency.

An observation at 18% contributes to the ≥5%, ≥10% and ≥15% landmarks.

### Episode depth

Individual drawdown episodes retain their own depth.

This connects the distribution-level Protection picture to actual historical journeys.

### Maximum severity

Maximum severity is:

> **the deepest known point in the observed terrain.**

It is not treated as "the fund's risk".

## Guardrails

Protection evidence must not be interpreted as:

- maximum severity being typical behaviour;
- frequency being equivalent to severity;
- daily downside volatility being equivalent to Protection;
- Protection being equivalent to Resilience; or
- historical Protection being a guarantee of future Protection.

The distinction is fundamental:

> **Protection describes the severity terrain; it does not describe how the fund travels through that terrain or whether it emerges from it.**

---

# Resilience

## Question

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

## Resilience evidence

### Decline duration

> **How long did the descent from the episode's peak to trough take?**

A rapid decline and prolonged deterioration can reach the same depth while representing very different experiences.

### Recovery duration

> **How long did demonstrated recovery from the trough to the previous high-water mark take?**

Recovery duration exists only when recovery has actually been observed.

An ongoing episode has:

```text
recovery_duration = unknown
```

not zero and not estimated.

### Underwater duration

> **How long did the fund remain below its previous high-water mark?**

Underwater time is a genuine path property.

It remains distinct from:

- depth;
- decline duration; and
- recovery duration.

### Episode state

Every episode has an evidence state:

- `recovered`
- `ongoing`

This is an evidence-state distinction, not merely a display field.

### Episode-level evidence

Individual episodes are retained at full useful resolution.

They provide the **3-foot view**.

Summary statistics provide the **30,000-foot view**.

Both are necessary.

---

## Resilience summary evidence

The resilience summary describes the observed episode population through:

- episode count
- recovered count
- ongoing count
- median depth
- worst depth
- median decline duration among recovered episodes
- median recovery duration
- median underwater duration among recovered episodes
- median underwater duration among ongoing episodes
- individual episode records

Recovered and ongoing populations remain distinct when recovery-related statistics are calculated.

## Guardrails

Resilience evidence must not be interpreted as:

- deep drawdown = poor resilience;
- fast recovery = strong Protection;
- long recovery = permanently weak fund;
- one recovery episode = inherent resilience;
- historical recovery = future recovery; or
- ongoing episode = failed recovery.

Most importantly:

> **"Recovered" means that recovery was observed for that historical episode. It does not mean the fund is inherently resilient.**

And:

> **"Ongoing" means that the recovery story is not yet observable in the available history.**

---

# Supporting Evidence

Supporting evidence may deepen the Fund story without becoming another Compass dimension.

## Downside RMS

Downside RMS describes:

> **How violently have negative daily movements varied?**

It is supporting descriptive evidence.

It does not represent Protection.

Daily downside intensity and path-level drawdown terrain can differ materially.

## Individual episodes

Individual episode records remain underlying evidence rather than being reduced immediately to a compact metric.

They allow Lakshya to move:

> **30,000 feet → 3 feet**

when deeper investigation is warranted.

---

# Optional Analytical Lenses

The following may be useful for narrower questions but do not belong to the foundational Fund Compass:

- benchmark-relative upside capture
- benchmark-relative downside capture
- Sortino
- Calmar
- risk-free-rate-dependent measures
- benchmark comparisons
- category-specific benchmark mappings

These lenses must not redefine intrinsic fund behaviour.

> **A benchmark is an analytical lens, not an intrinsic property of the fund.**

---

# Evidence-State Principle

Evidence quality is not another behavioural dimension.

It is a **guardrail around what Lakshya is permitted to conclude**.

Lakshya distinguishes:

> **observed ≠ inferred**

and:

> **recovered ≠ ongoing**

Unknown quantities remain unknown.

The absence of evidence must not be manufactured into a numerical conclusion.

---

# Compression Principle

> **Compression can be useful. Compression cannot be allowed to erase meaning.**

Summaries may be derived from richer evidence.

The richer evidence remains available.

A Fund Behavioural Fingerprint therefore describes a fund without reducing its historical behaviour to a single score.

---

# Fund-Level Boundary

The Fund Behavioural Fingerprint answers:

> **What kind of teammate is this fund?**

It does not answer:

> **Should Lakshya own it?**

That requires interaction with other funds and with the family's goals.

The Fund stage therefore ends at:

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

The next architectural question is:

```text
FUND → TEAM
```

The Fund stage does not borrow assumptions from the later layers to alter its evidence.

---