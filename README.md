# MF Portfolio Toolkit

Systematic pipeline for the two workflows discussed:
1. **First-time build / reshuffle** — full run through all steps below.
2. **Annual review** — re-run steps 1-7 on fresh data, diff the result against current
   holdings (Candidate set), and only act if the drift is meaningful (Step 10).

Python and C# are **independent, parallel implementations** of the same logic, sharing
the same input/output file formats so you can run both and diff the outputs as a
cross-check on correctness.

## Repo layout

```
mf-portfolio-toolkit/
  data/
    funds_universe.csv           <- master list: ISIN, name, category, current-holding flag
    benchmark_universe.csv       <- category -> required TRI index name (documentation only now)
    benchmarks_consolidated.csv  <- you maintain this by hand (see below); analytics reads it directly
    cache/                       <- raw API responses, one JSON per fund + the mfapi scheme list (gitignore this)
  output/
    fund_metadata.csv            <- flattened metadata: category, AUM, expense ratio, returns
    nav_panel.csv                <- dates x funds NAV matrix (forward-filled small gaps)
    ...                          <- later steps will add metrics.csv, frontier.csv, etc.
  python/
    requirements.txt
    fetch_data.py                <- Module 1: fund NAV + metadata acquisition
  csharp/
    MfToolkit.csproj
    Program.cs, Models.cs, NavClient.cs, CsvHelper.cs   <- Module 1: fund NAV + metadata acquisition
```

## Benchmarks — no code needed, manually extracted

Maintaining `data/benchmarks_consolidated.csv` by hand from
niftyindices.com downloads. Annual review = append that year's
rows to this one file, no script involved. `data/benchmark_universe.csv` stays as the
category -> index-name reference the Step 4 metrics engine will read from.
Source: https://www.niftyindices.com/reports/historical-data
Select "Historical Index Data" as the context, then choose rest of dropdown field values.
Period - one year at a time only is allowed. For appending, that much is enough.

## Module 1: fund NAV + metadata acquisition (updated — source swap)

**Data sources — now a hybrid, on your request to move NAV history to mfapi.in:**
- **NAV history**: `api.mfapi.in`. It doesn't support ISIN lookup directly, so the
  pipeline does a one-time (cached, refreshed at most daily) bulk fetch of `GET /mf`
  (~37k schemes, includes `isinGrowth`/`isinDivReinvestment`), builds an ISIN -> scheme
  code index locally, then pulls full history via `GET /mf/{scheme_code}`. Covers
  regular plans too, updates 6x/day.
- **Metadata** (AUM, expense ratio, fund manager): kept on `mf.captnemo.in`'s
  `/kuvera/{isin}` endpoint — mfapi.in's own metadata doesn't include these fields, so
  there was no single source that covered everything; each API does the job the other
  can't.

**⚠️ Before you rerun this: clear your old NAV cache.** Your previous run cached
`data/cache/{isin}_nav.json` in the old captnemo response shape (`historical_nav: [[date,
nav], ...]`). The new code expects mfapi.in's shape (`data: [{date, nav}, ...]`) and
won't error on a shape mismatch — it'll just silently treat the file as having zero NAV
rows, since caching means it won't refetch unless the file's missing or stale. Delete
the `*_nav.json` files (metadata cache `*_meta.json` is unaffected and fine to keep), or
just run with `--no-cache` once:

```bash
# from data/cache/
rm *_nav.json
```

**Run it (Python):**
```bash
cd python
pip install -r requirements.txt
python fetch_data.py                       # full universe
python fetch_data.py --isin INF846K01K35   # just one fund, to sanity-check first
```

**Run it (C#, needs .NET 8 SDK):**
```bash
cd csharp
dotnet run                                  # full universe
dotnet run -- --isin INF846K01K35           # just one fund
```

**Still untested end-to-end on my side** — no internet access or .NET SDK in this
sandbox, same limitation as before. The scheme-code resolution step is new logic (not
just a URL swap), so please run the single-fund test first on both and check:
- The console shows `Resolved scheme-code index: N ISINs known to mfapi.in` with N in
  the tens of thousands, and no unexpected entries under `[warn] ISINs not found`.
- `nav_panel.csv` has sensible row counts per fund again (same shape as before, just a
  different source).

**Things to check once you run it:**
- Spot-check 2-3 NAVs against the AMC factsheet — different source now, worth
  re-verifying rather than assuming the old spot-check still holds.
- `expense_ratio_pct` / `aum_cr` are unchanged (still captnemo/Kuvera-sourced).
- Forward-fill still caps at 5 trading days — genuinely missing chunks show as blanks,
  not guesses.

## Roadmap for the remaining steps (not yet built)

| Step | Module | Notes |
|---|---|---|
| 2 | Cleaning/alignment | Mostly folded into Module 1's panel-building already. |
| 3 | Category filtering | Min track record (5-7yr), AUM floor, direct-plan-only — filters `fund_metadata.csv`. |
| 4 | Metrics engine | Rolling CAGR (3/5/7/10Y), max drawdown + recovery time, downside deviation, upside/downside capture vs `benchmarks_consolidated.csv`, Sortino. This is next. |
| 5 | Correlation/covariance matrix | Input to the frontier; likely a shrinkage estimator (Ledoit-Wolf) rather than raw sample covariance given ~5-10yr history. |
| 6 | Efficient frontier | Python: `scipy.optimize` or `PyPortfolioOpt`. C#: `MathNet.Numerics` or a custom quadratic solver. Resampled/bootstrapped frontier, not a single point estimate. |
| 7 | Portfolio selection | Sharpe-max plus 2-3 candidate points (conservative/moderate/aggressive) for goal-mapping. |
| 8 | Goal-mapping overlay | Assigns each goal (Retirement/Edu-B/Marriage-HomeLoan/Stitch-Kutti) to a frontier point by horizon. |
| 9 | Transition layer | Tax-aware sell/buy list — formalizes the FIFO cost-basis + LTCG/STCG estimate we did by hand for the current 06_Wealth_Transition sheet. |
| 10 | Annual re-run + drift test | Candidate vs Challenger vs Watch Universe, made programmatic, with a drift threshold to avoid over-trading on noise. |

Once Module 1 is confirmed working against the new source, Step 4 (the metrics engine)
is next — everything it needs (fund NAVs, category benchmarks) is now in place.
