"""
Step 0/1/2 of the portfolio pipeline: fund universe metadata + historical NAV acquisition.

Reads:   data/funds_universe.csv   (isin, name, category, is_current_holding, notes)
Writes:  data/cache/{isin}_nav.json   (raw NAV API response, one file per fund, cached)
         data/cache/{isin}_meta.json  (raw metadata API response, one file per fund, cached)
         output/nav_panel.csv         (dates x funds NAV matrix, forward-filled)
         output/fund_metadata.csv     (flattened metadata: category, AUM, expense ratio, etc.)

Data source: mf.captnemo.in (free, no auth, ISIN-based; ultimately sourced from AMFI).
  - GET /nav/{isin}     -> {"ISIN", "name", "nav", "date", "historical_nav": [[date, nav], ...]}
  - GET /kuvera/{isin}  -> list with one dict of rich fund metadata (aum, expense_ratio, category, ...)

Usage:
    python fetch_data.py                      # fetch/refresh everything in funds_universe.csv
    python fetch_data.py --isin INF846K01K35   # fetch just one fund (useful for testing)
    python fetch_data.py --no-cache            # ignore cache, force re-download
    python fetch_data.py --max-age-days 7      # treat cache older than 7 days as stale

Notes / things to watch for once you run this:
  - This is an unofficial, best-effort free API. Verify a handful of NAVs against
    the AMC's own factsheet or AMFI before trusting the pipeline for real decisions.
  - Rate limiting: we sleep briefly between calls and retry with backoff. Be a good
    citizen of a free service — don't loop this in a tight schedule.
  - "historical_nav" arrays can have small gaps (fund closed on a trading holiday,
    or the source simply missing a day). The panel-building step forward-fills gaps
    up to a configurable limit rather than silently interpolating across long gaps.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_CSV = ROOT / "data" / "funds_universe.csv"
CACHE_DIR = ROOT / "data" / "cache"
OUTPUT_DIR = ROOT / "output"

NAV_URL = "https://mf.captnemo.in/nav/{isin}"
META_URL = "https://mf.captnemo.in/kuvera/{isin}"

REQUEST_TIMEOUT_SECS = 20
MAX_RETRIES = 3
RETRY_BACKOFF_SECS = 2.0
SLEEP_BETWEEN_CALLS_SECS = 0.5
MAX_FORWARD_FILL_DAYS = 5  # don't bridge gaps longer than this when building the panel


@dataclass
class FundEntry:
    isin: str
    name: str
    category: str
    is_current_holding: bool
    notes: str


def read_universe(path: Path = UNIVERSE_CSV) -> list[FundEntry]:
    if not path.exists():
        raise FileNotFoundError(
            f"Fund universe file not found at {path}. "
            "Create it with columns: isin,name,category,is_current_holding,notes"
        )
    funds = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            funds.append(
                FundEntry(
                    isin=row["isin"].strip(),
                    name=row["name"].strip(),
                    category=row["category"].strip(),
                    is_current_holding=row.get("is_current_holding", "").strip().lower() == "true",
                    notes=row.get("notes", "").strip(),
                )
            )
    return funds


def _get_with_retry(url: str) -> Optional[dict | list]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT_SECS)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                print(f"  [warn] 404 not found: {url}")
                return None
            last_error = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        wait = RETRY_BACKOFF_SECS * attempt
        print(f"  [retry {attempt}/{MAX_RETRIES}] {url} -> {last_error}; waiting {wait:.1f}s")
        time.sleep(wait)
    print(f"  [error] giving up on {url}: {last_error}")
    return None


def _cache_path(isin: str, kind: str) -> Path:
    return CACHE_DIR / f"{isin}_{kind}.json"


def _is_cache_fresh(path: Path, max_age_days: Optional[int]) -> bool:
    if not path.exists():
        return False
    if max_age_days is None:
        return True
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(days=max_age_days)


def fetch_fund(fund: FundEntry, use_cache: bool, max_age_days: Optional[int]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    nav_path = _cache_path(fund.isin, "nav")
    if use_cache and _is_cache_fresh(nav_path, max_age_days):
        print(f"[cache] {fund.isin} NAV ({fund.name})")
    else:
        print(f"[fetch] {fund.isin} NAV ({fund.name})")
        data = _get_with_retry(NAV_URL.format(isin=fund.isin))
        if data is not None:
            nav_path.write_text(json.dumps(data), encoding="utf-8")
        time.sleep(SLEEP_BETWEEN_CALLS_SECS)

    meta_path = _cache_path(fund.isin, "meta")
    if use_cache and _is_cache_fresh(meta_path, max_age_days):
        print(f"[cache] {fund.isin} metadata")
    else:
        print(f"[fetch] {fund.isin} metadata")
        data = _get_with_retry(META_URL.format(isin=fund.isin))
        if data is not None:
            meta_path.write_text(json.dumps(data), encoding="utf-8")
        time.sleep(SLEEP_BETWEEN_CALLS_SECS)


def build_metadata_table(funds: list[FundEntry]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "fund_metadata.csv"

    fieldnames = [
        "isin", "name", "category", "is_current_holding",
        "fund_house", "kuvera_category", "aum_cr", "expense_ratio_pct",
        "start_date", "lock_in_days", "return_1y", "return_3y", "return_5y",
        "volatility", "fund_manager",
    ]

    rows = []
    for fund in funds:
        meta_path = _cache_path(fund.isin, "meta")
        row = {
            "isin": fund.isin, "name": fund.name, "category": fund.category,
            "is_current_holding": fund.is_current_holding,
            "fund_house": "", "kuvera_category": "", "aum_cr": "", "expense_ratio_pct": "",
            "start_date": "", "lock_in_days": "", "return_1y": "", "return_3y": "",
            "return_5y": "", "volatility": "", "fund_manager": "",
        }
        if meta_path.exists():
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
                # kuvera endpoint returns a list with one entry
                entry = payload[0] if isinstance(payload, list) and payload else None
                if entry:
                    returns = entry.get("returns", {}) or {}
                    row.update({
                        "fund_house": entry.get("fund_house", ""),
                        "kuvera_category": entry.get("fund_category", ""),
                        "aum_cr": entry.get("aum", ""),
                        "expense_ratio_pct": entry.get("expense_ratio", ""),
                        "start_date": entry.get("start_date", ""),
                        "lock_in_days": entry.get("lock_in_period", ""),
                        "return_1y": returns.get("year_1", ""),
                        "return_3y": returns.get("year_3", ""),
                        "return_5y": returns.get("year_5", ""),
                        "volatility": entry.get("volatility", ""),
                        "fund_manager": entry.get("fund_manager", ""),
                    })
            except (json.JSONDecodeError, IndexError, KeyError) as exc:
                print(f"  [warn] could not parse metadata for {fund.isin}: {exc}")
        rows.append(row)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {out_path} ({len(rows)} funds)")
    return out_path


def build_nav_panel(funds: list[FundEntry]) -> Path:
    """
    Builds a dates x funds NAV matrix. Each fund's raw series is reindexed onto the
    UNION of all dates seen across funds, then forward-filled up to MAX_FORWARD_FILL_DAYS
    to bridge small gaps (holidays, missed data points) without pretending we have
    real data across genuinely long gaps.
    """
    series_by_isin: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()

    for fund in funds:
        nav_path = _cache_path(fund.isin, "nav")
        if not nav_path.exists():
            print(f"  [warn] no cached NAV data for {fund.isin}, skipping in panel")
            continue
        payload = json.loads(nav_path.read_text(encoding="utf-8"))
        hist = payload.get("historical_nav", [])
        series: dict[str, float] = {}
        for date_str, nav in hist:
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                # some sources use DD-MM-YYYY; try that as a fallback
                d = datetime.strptime(date_str, "%d-%m-%Y")
            iso = d.strftime("%Y-%m-%d")
            series[iso] = float(nav)
            all_dates.add(iso)
        series_by_isin[fund.isin] = series

    sorted_dates = sorted(all_dates)
    isins = list(series_by_isin.keys())

    # forward-fill per fund, tracking how many consecutive days we've been filling
    filled: dict[str, dict[str, str]] = {isin: {} for isin in isins}
    last_value: dict[str, float] = {}
    gap_len: dict[str, int] = {isin: 0 for isin in isins}

    for date in sorted_dates:
        for isin in isins:
            series = series_by_isin[isin]
            if date in series:
                last_value[isin] = series[date]
                gap_len[isin] = 0
                filled[isin][date] = f"{series[date]:.4f}"
            elif isin in last_value and gap_len[isin] < MAX_FORWARD_FILL_DAYS:
                gap_len[isin] += 1
                filled[isin][date] = f"{last_value[isin]:.4f}"
            else:
                filled[isin][date] = ""  # genuine gap, leave blank rather than fabricate

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "nav_panel.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date"] + isins)
        for date in sorted_dates:
            writer.writerow([date] + [filled[isin].get(date, "") for isin in isins])

    print(f"Wrote {out_path} ({len(sorted_dates)} dates x {len(isins)} funds)")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch NAV history + metadata for the fund universe.")
    parser.add_argument("--isin", help="Fetch just this one ISIN (for testing)")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cache, force re-download")
    parser.add_argument("--max-age-days", type=int, default=None,
                         help="Treat cached files older than N days as stale")
    args = parser.parse_args()

    funds = read_universe()
    if args.isin:
        funds = [f for f in funds if f.isin == args.isin]
        if not funds:
            print(f"ISIN {args.isin} not found in {UNIVERSE_CSV}")
            sys.exit(1)

    use_cache = not args.no_cache
    for fund in funds:
        fetch_fund(fund, use_cache=use_cache, max_age_days=args.max_age_days)

    build_metadata_table(read_universe())
    build_nav_panel(read_universe())


if __name__ == "__main__":
    main()
