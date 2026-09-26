# Technical debt backlog

**Status:** Cleared on 2026-09-26.

The validated command sequence is unchanged:

```text
python -m cas_import_poc.runner … --as-of YYYY-MM-DD
python python/run_production.py --as-of YYYY-MM-DD
python python/run_purpose_staging.py … --as-of YYYY-MM-DD
python -m lts.runner
```

## Removed

These entry points were not part of that sequence, and nothing in the live path imported them:

- `python/lps/run_nav.py` — NAV refresh CLI. CAS import already acquires NAV through `lps.nav_pipeline`. Scope checks now live only in `fund_analysis.funds_in_scope`.
- `python/mission/run_survivor_trajectory_pipeline.py` — alias that ran the LFS engine and stopped before FINAL was archived.
- `python/run_purpose_review.py` — CLI wrapper. The review surface remains in `family.review_surface`.
- `python/run_purpose_simulation.py` — CLI wrapper. Staging remains `python/run_purpose_staging.py`. History helpers remain in `family.staging_history`.
- `python/lakshya_core/parked/capture_runner.py` — parked script. The parked capture library was not part of this deletion.
- The direct command on `python/mission/resilient_pipeline.py`. The module stays, because `python/run_production.py` calls it. It can no longer be started on its own and stop before FINAL.

## Kept on purpose

- `python/mission/resilient_pipeline.py` is the live LFS engine, not a spare runner.
- `python/team_analysis/run_team_pipeline.py` is the live FUND/TEAM function production calls. The filename looks like a command. It is not one, and renaming it would only move imports.

Live runners stay on the paths above. Moving them into new stage folders would change the sequence that just reconciled.
