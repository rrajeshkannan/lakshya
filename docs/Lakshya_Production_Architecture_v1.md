## CI hotfix

FINAL imported the canonical analytical-horizon helper with a package-relative import, but the helper itself lived only under `mission`. In an installed/test environment this made `final` import fail during test collection.

The production fix is intentionally narrow: FINAL now owns a tiny local copy of the horizon contract under `python/final/observation_horizon.py`. The canonical horizon values and selection rule remain identical (`3, 5, 7, 10Y`; greatest supported horizon not exceeding the Purpose horizon). This avoids a dependency from FINAL back into a MISSION implementation seam while preserving the established analytical contract.

The failure affected test collection only; the error occurred before any FINAL test executed. The implementation is therefore a packaging/import-boundary defect, not a mathematical failure of the compromise-programming algorithm.
