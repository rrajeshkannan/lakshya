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
    funds_universe.csv     <- master list: ISIN, name, category, current-holding flag
    cache/                 <- raw API responses, one JSON per fund (gitignore this)
  output/
    fund_metadata.csv      <- flattened metadata: category, AUM, expense ratio, returns
    nav_panel.csv           <- dates x funds NAV matrix (forward-filled small gaps)
    ...                     <- later steps will add metrics.csv, frontier.csv, etc.
  python/
    requirements.txt
    fetch_data.py           <- Module 1: data acquisition (done, this message)
  csharp/
    MfToolkit.csproj
    Program.cs, Models.cs, NavClient.cs, CsvHelper.cs   <- Module 1: data acquisition (done)
```

## Module 1 (this delivery): fund universe + historical NAV acquisition

**What it does:** for every ISIN in `data/funds_universe.csv`, fetches historical NAV
series and fund metadata (category, AUM, expense ratio, trailing returns) from
`mf.captnemo.in` (free, no auth, ISIN-based — confirmed working endpoint pattern:
`/nav/{isin}` and `/kuvera/{isin}`), caches the raw responses, and builds two
combined tables: `output/fund_metadata.csv` and `output/nav_panel.csv`.

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

**Important — I could not test-run either of these** (this sandbox has no internet
access and no .NET SDK installed). Please run the `--isin` single-fund test first on
each, check that `output/fund_metadata.csv` and `output/nav_panel.csv` look sane, and
tell me what breaks — API response shape mismatches are the most likely failure mode
since I built the parsers from the documented sample responses, not a live call.

**Things to check once you run it:**
- Spot-check 2-3 NAVs in `nav_panel.csv` against the AMC factsheet or Value Research —
  this is an unofficial free API, worth a trust-but-verify pass before Step 4 onward
  builds on top of it.
- `expense_ratio_pct` and `aum_cr` come from the Kuvera-sourced metadata endpoint and
  may lag by a few months (see `expense_ratio_date` if you want to add that field).
- The forward-fill only bridges gaps up to 5 trading days — a genuinely missing chunk
  of history will show up as blank cells in `nav_panel.csv` rather than a guessed value.
  Worth eyeballing for any fund with a long blank stretch before trusting its rolling
  returns later.

## Roadmap for the remaining steps (not yet built)

| Step | Module | Notes |
|---|---|---|
| 2 | Cleaning/alignment | Mostly folded into Module 1's panel-building already; may need a pass for direct-vs-regular plan disambiguation if you add regular-plan ISINs to the universe later. |
| 3 | Category filtering | Min track record (5-7yr), AUM floor, direct-plan-only — filters `fund_metadata.csv`. |
| 4 | Metrics engine | Rolling CAGR (3/5/7/10Y), max drawdown + recovery time, downside deviation, upside/downside capture vs a benchmark index, Sortino. Needs a benchmark NAV/index series added to the universe (e.g. Nifty 500 TRI, Nifty Smallcap 250 TRI) — will add that to `funds_universe.csv` schema or a separate `benchmarks.csv`. |
| 5 | Correlation/covariance matrix | Input to the frontier; will likely use a shrinkage estimator (Ledoit-Wolf) rather than raw sample covariance given ~5-10yr history. |
| 6 | Efficient frontier | Python: `scipy.optimize` or `PyPortfolioOpt`. C#: `MathNet.Numerics` (only external dependency this whole toolkit will need) or a custom quadratic solver. Will include a resampled/bootstrapped frontier, not just a single point estimate. |
| 7 | Portfolio selection | Sharpe-max plus 2-3 candidate points (conservative/moderate/aggressive) for goal-mapping. |
| 8 | Goal-mapping overlay | Assigns each goal (Retirement/Edu-B/Marriage-HomeLoan/Stitch-Kutti) to a frontier point by horizon. |
| 9 | Transition layer | Tax-aware sell/buy list — formalizes the FIFO cost-basis + LTCG/STCG estimate we did by hand for the current 06_Wealth_Transition sheet. |
| 10 | Annual re-run + drift test | Candidate vs Challenger vs Watch Universe, made programmatic, with a drift threshold to avoid over-trading on noise. |

Say the word when you've test-run Module 1 and want to move to Step 3/4 (filtering +
metrics engine) — that's the next natural chunk, and it's where "acceptable downside,
quick recovery" actually gets defined in code instead of by eye.
