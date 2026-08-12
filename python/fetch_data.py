"""
Step 0/1/2 of the portfolio pipeline: fund universe metadata + historical NAV acquisition.

Reads:   data/funds_universe.csv   (isin, name, category, is_current_holding, notes)
Writes:  data/cache/mfapi_scheme_list.json   (bulk scheme list, ~37k entries, cached)
         data/cache/{isin}_nav.json          (raw NAV history per fund, cached)
         data/cache/{isin}_meta.json         (raw metadata per fund, cached)
         output/nav_panel.csv                (dates x funds NAV matrix, forward-filled)
         output/fund_metadata.csv            (flattened metadata: category, AUM, expense ratio, etc.)

Data sources (hybrid — chosen deliberately, not arbitrarily):
  - NAV history: api.mfapi.in — actively documented, updates 6x/day, covers regular
    plans too. Doesn't support ISIN lookup directly, so we resolve ISIN -> scheme code
    via one cached bulk fetch of GET /mf (every scheme, with isinGrowth/isinDivReinvestment
    fields), then pull full history via GET /mf/{scheme_code}.
  - Metadata (AUM, expense ratio, fund manager): mf.captnemo.in's /kuvera/{isin} endpoint.
    mfapi.in's own metadata is thin (fund house/category/ISIN only, no AUM or expense
    ratio) — captnemo covers what mfapi.in doesn't, so both stay in the pipeline for
    different jobs rather than picking one "winner".

Usage:
    python fetch_data.py                      # fetch/refresh everything in funds_universe.csv
    python fetch_data.py --isin INF846K01K35   # fetch just one fund (useful for testing)
    python fetch_data.py --no-cache            # ignore cache, force re-download
    python fetch_data.py --max-age-days 7      # treat cache older than 7 days as stale

Notes / things to watch for once you run this:
  - Both are free, unofficial-in-the-legal-sense APIs (no SLA). Spot-check a NAV or two
    against the AMC factsheet before trusting the pipeline for real decisions.
  - The scheme-code resolution step prints which ISINs it couldn't match — a fund with
    no match usually means a very recently changed ISIN or a genuinely delisted scheme;
    check manually rather than assume the code is wrong.
  - Rate limiting: brief sleep between calls, retry with backoff. Don't loop this tightly.
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

MFAPI_LIST_URL = "https://api.mfapi.in/mf"
MFAPI_SCHEME_URL = "https://api.mfapi.in/mf/{scheme_code}"
CAPTNEMO_META_URL = "https://mf.captnemo.in/kuvera/{isin}"

SCHEME_LIST_CACHE = CACHE_DIR / "mfapi_scheme_list.json"
SCHEME_LIST_MAX_AGE_DAYS = 1  # the bulk list changes rarely; refresh daily at most

REQUEST_TIMEOUT_SECS = 20
LIST_REQUEST_TIMEOUT_SECS = 60  # the bulk /mf list is large
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


def _get_with_retry(url: str, timeout: int = REQUEST_TIMEOUT_SECS) -> Optional[dict | list]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=timeout)
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


# --- ISIN -> mfapi scheme code resolution -----------------------------------

def ensure_scheme_list(use_cache: bool, max_age_days: Optional[int]) -> list[dict]:
    """
    Downloads (or reuses the cached copy of) mfapi.in's full ~37k-scheme list.
    Each entry looks like: {"schemeCode": 125497, "schemeName": "...",
    "isinGrowth": "INF...", "isinDivReinvestment": "INF..." or null}.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    effective_max_age = max_age_days if max_age_days is not None else SCHEME_LIST_MAX_AGE_DAYS

    if use_cache and _is_cache_fresh(SCHEME_LIST_CACHE, effective_max_age):
        print("[cache] mfapi scheme list")
        return json.loads(SCHEME_LIST_CACHE.read_text(encoding="utf-8"))

    print("[fetch] mfapi scheme list (~37k schemes, one-time/occasional download)")
    data = _get_with_retry(MFAPI_LIST_URL, timeout=LIST_REQUEST_TIMEOUT_SECS)
    if data is None:
        if SCHEME_LIST_CACHE.exists():
            print("  [warn] using stale cached scheme list since fresh fetch failed")
            return json.loads(SCHEME_LIST_CACHE.read_text(encoding="utf-8"))
        raise RuntimeError("Could not fetch mfapi scheme list and no cache available.")
    SCHEME_LIST_CACHE.write_text(json.dumps(data), encoding="utf-8")
    return data


def build_isin_index(scheme_list: list[dict]) -> dict[str, int]:
    """Maps normalized ISIN -> schemeCode, checking both growth and IDCW-reinvestment ISINs."""
    index: dict[str, int] = {}
    for entry in scheme_list:
        code = entry.get("schemeCode")
        if code is None:
            continue
        for field in ("isinGrowth", "isinDivReinvestment", "isin_growth", "isin_div_reinvestment"):
            isin = entry.get(field)
            if isin:
                index[isin.strip().upper()] = code
    return index


# --- Per-fund fetch -----------------------------------------------------------

def fetch_fund(fund: FundEntry, isin_index: dict[str, int], use_cache: bool, max_age_days: Optional[int]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # NAV history via mfapi.in
    nav_path = _cache_path(fund.isin, "nav")
    if use_cache and _is_cache_fresh(nav_path, max_age_days):
        print(f"[cache] {fund.isin} NAV ({fund.name})")
    else:
        scheme_code = isin_index.get(fund.isin.strip().upper())
        if scheme_code is None:
            print(f"  [warn] {fund.isin} ({fund.name}): not found in mfapi scheme list, skipping NAV fetch")
        else:
            print(f"[fetch] {fund.isin} NAV via mfapi scheme {scheme_code} ({fund.name})")
            data = _get_with_retry(MFAPI_SCHEME_URL.format(scheme_code=scheme_code))
            if data is not None:
                nav_path.write_text(json.dumps(data), encoding="utf-8")
            time.sleep(SLEEP_BETWEEN_CALLS_SECS)

    # Metadata (AUM, expense ratio, fund manager) via captnemo — unchanged
    meta_path = _cache_path(fund.isin, "meta")
    if use_cache and _is_cache_fresh(meta_path, max_age_days):
        print(f"[cache] {fund.isin} metadata")
    else:
        print(f"[fetch] {fund.isin} metadata")
        data = _get_with_retry(CAPTNEMO_META_URL.format(isin=fund.isin))
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
            "is_current_holding": str(fund.is_current_holding).lower(),
            "fund_house": "", "kuvera_category": "", "aum_cr": "", "expense_ratio_pct": "",
            "start_date": "", "lock_in_days": "", "return_1y": "", "return_3y": "",
            "return_5y": "", "volatility": "", "fund_manager": "",
        }
        if meta_path.exists():
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
                # captnemo's kuvera endpoint returns a list with one entry
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

    mfapi.in's per-scheme response shape: {"meta": {...}, "data": [{"date": "DD-MM-YYYY",
    "nav": "123.4500"}, ...], "status": "SUCCESS"} — newest-first, unlike the panel's
    ascending-date convention, so we sort explicitly rather than assume order.
    """
    series_by_isin: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()

    for fund in funds:
        nav_path = _cache_path(fund.isin, "nav")
        if not nav_path.exists():
            print(f"  [warn] no cached NAV data for {fund.isin}, skipping in panel")
            continue
        payload = json.loads(nav_path.read_text(encoding="utf-8"))
        entries = payload.get("data", [])
        series: dict[str, float] = {}
        for entry in entries:
            date_str = entry.get("date")
            nav_str = entry.get("nav")
            if not date_str or not nav_str:
                continue
            d = datetime.strptime(date_str.strip(), "%d-%m-%Y")
            iso = d.strftime("%Y-%m-%d")
            series[iso] = float(nav_str)
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
    parser = argparse.ArgumentParser(description="Fetch NAV history (mfapi.in) + metadata (captnemo) for the fund universe.")
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
    scheme_list = ensure_scheme_list(use_cache=use_cache, max_age_days=args.max_age_days)
    isin_index = build_isin_index(scheme_list)
    print(f"Resolved scheme-code index: {len(isin_index)} ISINs known to mfapi.in\n")

    unresolved = [f for f in funds if f.isin.strip().upper() not in isin_index]
    if unresolved:
        print("[warn] ISINs not found in mfapi.in scheme list (NAV fetch will be skipped for these):")
        for f in unresolved:
            print(f"    {f.isin}  {f.name}")
        print()

    for fund in funds:
        fetch_fund(fund, isin_index, use_cache=use_cache, max_age_days=args.max_age_days)

    build_metadata_table(read_universe())
    build_nav_panel(read_universe())


if __name__ == "__main__":
    main()
