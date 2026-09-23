# Lakshya — Current Implementation Status

**As of:** 2026-09-23  
**Branch:** `main`  
**Status:** LTS transition foundation implemented; integration and reconciliation hardening remain before production transition use.

This document is the current implementation-status companion to the design documents. It records what exists, what has been validated, and what must remain explicitly unresolved. It is not a second architecture or an execution authorization.

---

## 1. System boundary

Lakshya remains a deliberately separated three-system design:

```text
LPS — observe Economic CURRENT from authoritative evidence
LFS — form reviewed analytical intent and TARGET inputs
LTS — analyze the transition from CURRENT to TARGET
```

LTS does not re-run portfolio formation and does not silently change FINAL decisions. Its responsibility is to make the transition evidence explicit, traceable, constrained, and reviewable.

The states remain distinct:

- **Analytical CURRENT:** what the reviewed Lakshya architecture says should be owned.
- **Economic CURRENT:** what the family actually owns at the selected observation date.
- **TARGET:** what the committed Purpose state and selected FINAL decisions imply should be owned.

## 2. Implemented LTS foundation

The current codebase contains a transition foundation covering:

- source-derived position and lot bridging;
- holding-level availability and lock classification;
- purpose transition mapping;
- reconciliation reports at Purpose and holding boundaries;
- explicit handling of locked holdings;
- selected-fund evidence used to derive transition intent; and
- a slice-materialization module intended to turn transition decisions into reviewable materialized slices.

The validated intermediate evidence has included:

- 696 lots across 34 position summaries;
- 602 available lots and 94 locked lots;
- no negative lot balances in the validated run;
- six balanced Purpose reports; and
- consistent Purpose-level reconciliation within numerical tolerance.

These validations establish internal consistency for the examined run. They do not yet establish that the complete transition artifact is safe for execution.

## 3. Design invariants

The following invariants remain mandatory:

1. A Position is identified by **Investor + Folio + ISIN**.
2. Ownership and Purpose mapping must remain explicit; a Position must not be silently assigned to multiple Purposes.
3. `transaction_through_date` and `valuation_as_of_date` are separate facts.
4. Source evidence must be preserved separately from analytical interpretation and transition decisions.
5. Locked holdings must be represented explicitly, not treated as freely redeemable availability.
6. Reconciliation must be performed at each boundary: lots → positions, positions → Purposes, and Purpose totals → transition outputs.
7. Duplicate or contradictory source rows must not be silently deduplicated. They require evidence review and an explicit decision.
8. Unknown source facts must remain unknown; the system must not invent tax basis, acquisition semantics, transaction costs, or execution constraints.
9. Materialization is a review artifact, not permission to execute transactions automatically.

## 4. Known gaps before production transition use

### 4.1 Materialization integration

The slice-materialization implementation exists, but its complete integration into the transition runner and persisted artifact set is not yet established. The workflow must not claim that a complete, durable materialized transition package exists until the runner, artifact paths, and validation checkpoints are connected and tested together.

### 4.2 Retention of all selected funds

The current evidence shows that not every LFS-selected fund is retained in the transition result. The intended behavior is data-driven: selected funds must be evaluated and retained or transitioned according to explicit evidence and policy, not by an accidental omission or hard-coded fund-specific behavior.

In the examined run, selected-fund value and reported retained value differ materially. This remains an implementation defect to be resolved and reconciled before the output can be treated as a reliable transition plan.

### 4.3 Valuation and duplicate-source anomaly

The examined run contains a discrepancy between lot-availability value and the manifest/Purpose-current value of approximately **₹27,420.24**. The source also contains exact duplicate transaction rows for one investor/folio/ISIN combination. The extra duplicated rows represent approximately **1,597.327 units** and **₹144,604.26** in recorded value.

The system must not silently remove these rows. The next step is to establish whether the duplication is a source duplication, a parsing/reconstruction issue, or a legitimate repeated event, then make the resolution explicit and auditable.

## 5. Required completion sequence

Before calling LTS production-ready for transition planning:

```text
source anomaly classification
        ↓
selected-fund retention correction
        ↓
materialization runner integration
        ↓
artifact persistence and naming contract
        ↓
end-to-end reconciliation
        ↓
repeatable validation run
        ↓
human review checkpoint
```

No stage may conceal an unresolved discrepancy from the next stage. A failed reconciliation blocks promotion.

## 6. Reviewer's interpretation rule

The current LTS outputs are **engineering evidence and diagnostic material**, not execution instructions. Until the known gaps are resolved, reviewers should use them to inspect boundaries and failure modes, not to place transactions.

The design rationale is intentional:

- preserve the distinction between observation, formation, and transition;
- introduce information only at the layer that genuinely consumes it;
- prefer explicit unresolved evidence over fabricated certainty; and
- keep the human review and execution decision outside the analytical engine.

For practical operation, see `docs/Lakshya_HowTo.md`. For the wider contracts and sequence, see `docs/Lakshya_Architecture.md` and `docs/Lakshya_Pipeline_Sequence.md`.
