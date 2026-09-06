# Lakshya Family Architecture Validation

**Status:** Post-FINAL observational layer

**Schema:** Family Attribution v1

**As of:** 2026-09-06

This layer exists because independently derived Purpose-level FINAL decisions can create a common family dependency. It makes that consequence visible without changing any upstream decision.

## 1. Architectural position

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
```

FINAL answers:

> Among qualified Compositions, which is the strongest practical compromise?

Family Architecture Validation answers a different question:

> Given those Purpose-level decisions together, where does family capital depend on common funds or investment organizations?

This is **attribution, not optimization**.

## 2. Inputs

The layer consumes only already-earned production information:

```text
data/purpose/purposes.csv
        ↓
Purpose current capital (`value`)


data/reviews/<as_of>/<Purpose>_summary.csv
        ↓
archived FINAL primary winner


data/reviews/<as_of>/review_manifest.json
        ↓
archive integrity and lineage verification


data/fund/funds_in_scope_metadata.csv
        ↓
fund and AMC identity
```

The dated FINAL archive is authoritative for the selected Composition. The layer does not recompute FINAL and does not consume candidate populations.

## 3. Attribution contract

For each Purpose:

```text
Purpose current capital
        ×
FINAL Composition fund weight
        =
Attributed capital
```

Across the family:

```text
Fund attributed capital
        ↓
Fund concentration

Fund attributed capital
        ↓
AMC aggregation
        ↓
AMC / ecosystem concentration
```

Purpose breadth is retained alongside capital concentration so a common dependency can be seen both by amount and by number of Purposes affected.

## 4. Outputs

Each review produces under `data/reviews/<as_of>/`:

```text
family_capital_attribution.csv
family_fund_concentration.csv
family_amc_concentration.csv
family_purpose_dependency.csv
family_attribution_manifest.json
family_attribution.log
```

### `family_capital_attribution.csv`

Detailed Purpose → Fund attribution, including Purpose capital, Composition weight, attributed capital, family percentage, and AMC identity.

### `family_fund_concentration.csv`

Family-level fund exposure, attributed capital, percentage of family Purpose capital, number of Purposes affected, and Purpose coverage.

### `family_amc_concentration.csv`

The same aggregation at AMC level. This is the primary view for an ecosystem/common-organization dependency question.

### `family_purpose_dependency.csv`

Purpose-level reconciliation showing that the attributed fund capital sums back to the Purpose's current capital and preserving the FINAL Composition identity.

### `family_attribution_manifest.json`

Records the attribution schema, input hashes, review date, and generated artifact list.

### `family_attribution.log`

Forensic execution log. It records source loading, archive verification, each FINAL winner consumed, artifact writes, and completion.

## 5. Deliberate non-responsibilities

Family Architecture Validation v1 does **not**:

- impose a maximum fund concentration;
- impose a maximum AMC concentration;
- penalize common dependencies;
- alter FINAL winners;
- create substitute Compositions;
- optimize family-level allocations;
- declare a concentration safe or unsafe; or
- introduce transition-cost assumptions.

A discovered dependency is an observation. Whether the family should tolerate it is a subsequent analytical question.

## 6. Integrity invariants

The implementation fails closed when:

1. Purpose capital is missing, duplicated, negative, or non-positive in aggregate;
2. fund metadata has missing required identity fields or duplicate ISINs;
3. a FINAL Composition identity is malformed or does not sum to 100%;
4. a FINAL winner references an unknown fund ISIN;
5. the archived FINAL manifest does not match the requested Purpose set;
6. an archived FINAL summary hash does not match its manifest; or
7. Purpose-level attributed capital does not reconcile to the Purpose capital.

The output writes are atomic.

## 7. Production usage

After the normal MISSION → FINAL production run and archival:

```text
python python/run_family_attribution.py --as-of 2026-09-06
```

The layer is intentionally runnable independently. This permits attribution to be validated and rerun without recomputing or modifying FUND, TEAM, COMPOSITION, MISSION, or FINAL evidence.

## 8. Future questions

The next questions are analytical, not yet rules:

> If a common dependency experiences a severe but plausible deterioration, how much of the family architecture is simultaneously affected?

and:

> How much common dependency is compatible with the family's required resilience?

Only evidence from those investigations can justify a future guardrail or a second family architecture.
