#!/usr/bin/env python3
"""Download Hyperliquid funding history from the official free API.

The official Hyperliquid API keeps no trade or candle history worth using,
but fundingHistory is the one deep free series: 500 rows per call, pageable,
BTC back to 12 May 2023. Funding settles hourly, so one call covers about
20 days.

Endpoint: POST https://api.hyperliquid.xyz/info, no key, no account.
Body: {"type": "fundingHistory", "coin": "BTC",
       "startTime": <ms>, "endTime": <ms>}
Response rows: {"coin", "fundingRate", "premium", "time"} where time is
Unix milliseconds and fundingRate is the hourly rate as a decimal string.

This script pages through the window 500 rows at a time and writes one
Parquet file per coin. It also pulls open interest from CryptoHFTData with
--oi, since the official API has no historical OI endpoint. OI files use
the same hourly layout as the trades script:
hyperliquid_futures/{YYYY-MM-DD}/{HH}/{SYMBOL}_open_interest.parquet

Needs: pip install requests pyarrow

Usage:
    python scripts/download_funding.py --symbols BTC ETH --start 2025-07-28 --end 2026-11-23
    python scripts/download_funding.py --symbols BTC --start 2026-11-20 --end 2026-11-23 --oi
    python scripts/download_funding.py --symbols BTC --start 2025-07-28 --end 2026-11-23 --dry-run

Output under --out (default ./data/funding):
    funding/{COIN}.parquet        fundingRate as float, time as ms int
    open_interest/{COIN}/{YYYY-MM-DD}/{HH}.parquet   (only with --oi)

Funding is the carry leg of the strategy: a backtest that trades funding
without this series is silently wrong. Load it into Nautilus as
FundingRateUpdate; see references/nautilus-api.md and verify the funding
settlement path against the installed package before trusting a carry
backtest.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    requests = None

API_URL = "https://api.hyperliquid.xyz/info"
PAGE_SIZE = 500
OI_BASE_URL = "https://api.cryptohftdata.com/download"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download Hyperliquid funding history from the official API."
    )
    parser.add_argument("--symbols", nargs="+", required=True,
                        help="Perp symbols, e.g. BTC ETH SOL")
    parser.add_argument("--start", required=True,
                        help="First UTC date, YYYY-MM-DD")
    parser.add_argument("--end", required=True,
                        help="Last UTC date, YYYY-MM-DD, inclusive")
    parser.add_argument("--out", default="./data/funding",
                        help="Output directory (default ./data/funding)")
    parser.add_argument("--oi", action="store_true",
                        help="Also pull CryptoHFTData hourly open interest files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan without downloading")
    return parser.parse_args()


def fetch_funding(session, coin, start_ms, end_ms):
    rows = []
    cursor = start_ms
    while True:
        resp = session.post(
            API_URL,
            json={"type": "fundingHistory", "coin": coin,
                  "startTime": cursor, "endTime": end_ms},
            timeout=60,
        )
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break
        rows.extend(page)
        last_time = page[-1]["time"]
        if len(page) < PAGE_SIZE or last_time >= end_ms:
            break
        cursor = last_time + 1
        time.sleep(0.05)
    return rows


def write_funding_parquet(rows, dest):
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.table({
        "time": pa.array([int(r["time"]) for r in rows], type=pa.int64()),
        "coin": pa.array([r["coin"] for r in rows], type=pa.string()),
        "fundingRate": pa.array([float(r["fundingRate"]) for r in rows],
                                type=pa.float64()),
        "premium": pa.array([float(r["premium"]) for r in rows],
                            type=pa.float64()),
    })
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    pq.write_table(table, dest)


def fetch_oi(session, symbol, start, end, out_dir):
    hours = 0
    missing = 0
    day = start
    while day <= end:
        for hh in range(24):
            rel = (f"hyperliquid_futures/{day.isoformat()}/{hh:02d}/"
                   f"{symbol}_open_interest.parquet")
            dest = os.path.join(out_dir, "open_interest", symbol,
                                day.isoformat(), f"{hh:02d}.parquet")
            if os.path.exists(dest):
                continue
            resp = session.get(OI_BASE_URL, params={"file": rel}, timeout=120)
            if resp.status_code == 200 and resp.content.startswith(b"PAR1"):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as fh:
                    fh.write(resp.content)
                hours += 1
            elif resp.status_code == 404:
                missing += 1
            else:
                print(f"{rel}: HTTP {resp.status_code}")
            time.sleep(1.0)
        day += dt.timedelta(days=1)
    return hours, missing


def main():
    args = parse_args()
    if requests is None:
        print("error: requests is not installed. Run: pip install requests",
              file=sys.stderr)
        return 2
    symbols = [s.upper() for s in args.symbols]
    try:
        start = dt.date.fromisoformat(args.start)
        end = dt.date.fromisoformat(args.end)
    except ValueError:
        print("error: --start and --end must be YYYY-MM-DD", file=sys.stderr)
        return 2
    if end < start:
        print("error: --end is before --start", file=sys.stderr)
        return 2

    start_ms = int(dt.datetime(start.year, start.month, start.day,
                               tzinfo=dt.timezone.utc).timestamp() * 1000)
    end_ms = int(dt.datetime(end.year, end.month, end.day, 23, 59, 59,
                             tzinfo=dt.timezone.utc).timestamp() * 1000)
    print(f"symbols: {', '.join(symbols)}")
    print(f"window: {start} to {end} ({start_ms} to {end_ms} ms)")
    if args.oi:
        print("open interest: also pulling CryptoHFTData hourly OI files")
    if args.dry_run:
        return 0

    session = requests.Session()
    for symbol in symbols:
        dest = os.path.join(args.out, "funding", f"{symbol}.parquet")
        print(f"{symbol}: fetching funding history...")
        try:
            rows = fetch_funding(session, symbol, start_ms, end_ms)
        except Exception as exc:
            print(f"{symbol}: funding fetch failed: {exc}", file=sys.stderr)
            continue
        if not rows:
            print(f"{symbol}: no funding rows in window")
            continue
        rows.sort(key=lambda r: r["time"])
        write_funding_parquet(rows, dest)
        first = dt.datetime.fromtimestamp(rows[0]["time"] / 1000,
                                          dt.timezone.utc)
        last = dt.datetime.fromtimestamp(rows[-1]["time"] / 1000,
                                         dt.timezone.utc)
        print(f"{symbol}: {len(rows)} hourly rows, {first} to {last} -> {dest}")
        if args.oi:
            hours, missing = fetch_oi(session, symbol, start, end, args.out)
            print(f"{symbol}: OI files downloaded {hours}, missing hours {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
