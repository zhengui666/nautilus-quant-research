#!/usr/bin/env python3
"""Download CryptoHFTData hourly Parquet files for Hyperliquid.

CryptoHFTData publishes free tick trades, L2 order books, mark price /
funding context, and open interest for Hyperliquid as one Parquet file per
symbol per UTC hour. No paid plan exists. Without an account you may
download 60 files per minute per IP; a free account key removes the limit.

Sources:
  https://www.cryptohftdata.com/datasets/hyperliquid-trades-data
  https://www.cryptohftdata.com/datasets/hyperliquid-orderbook-data
  https://www.cryptohftdata.com/llms.txt

File layout on the server:
  {exchange}/{YYYY-MM-DD}/{HH}/{SYMBOL}_{data_type}.parquet
Download endpoint:
  https://api.cryptohftdata.com/download?file=<path above>

Coverage for Hyperliquid Futures (exchange id hyperliquid_futures):
trades and order book from 2025-09-29, 467 perp symbols. Spot uses
hyperliquid_spot. Files land about 15 minutes after each hour.

Data types and their file suffixes:
  trades        {SYMBOL}_trades.parquet
  orderbook     {SYMBOL}_orderbook.parquet
  mark_price    {SYMBOL}_mark_price.parquet (mark price, index price, funding)
  open_interest {SYMBOL}_open_interest.parquet

Trades schema: received_time (ns), event_time, symbol, trade_id, price and
quantity as strings, trade_time, is_buyer_maker, order_type. One row per
public trade. Deduplicate on (symbol, trade_id) if you re-pull history,
because trades replayed after a reconnect can reappear in a later hour.

Order book schema: received_time (ns), event_time, transaction_time,
symbol, event_type (snapshot or update), sequence ids, side, price,
quantity, order_count. L2 price-level depth only; no L3, no queue position.
Hour files can start with a checkpoint snapshot at the hour boundary.

Needs: pip install requests

Usage:
    python scripts/download_cryptohftdata.py --symbols BTC ETH --start 2025-09-29 --end 2025-10-05
    python scripts/download_cryptohftdata.py --symbols BTC --start 2026-09-02 --end 2026-09-02 --data-types trades orderbook
    python scripts/download_cryptohftdata.py --symbols BTC --start 2025-09-29 --end 2025-09-30 --api-key $CRYPTOHFTDATA_API_KEY
    python scripts/download_cryptohftdata.py --symbols BTC --start 2025-09-29 --end 2025-09-30 --dry-run

Output mirrors the server layout under --out (default ./data/cryptohftdata):
  hyperliquid_futures/2026-09-02/12/BTC_trades.parquet

Existing files are skipped, so re-running resumes. Hours with no file
(symbol not listed yet, or a known ingestion gap) are logged as missing
and do not stop the run.
"""

import argparse
import datetime as dt
import os
import sys
import time

try:
    import requests
except ImportError:
    requests = None

BASE_URL = "https://api.cryptohftdata.com/download"
DATA_TYPES = ("trades", "orderbook", "mark_price", "open_interest")
PARQUET_MAGIC = b"PAR1"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download CryptoHFTData hourly files for Hyperliquid."
    )
    parser.add_argument("--symbols", nargs="+", required=True,
                        help="Symbols, e.g. BTC ETH SOL")
    parser.add_argument("--start", required=True,
                        help="First UTC date, YYYY-MM-DD")
    parser.add_argument("--end", required=True,
                        help="Last UTC date, YYYY-MM-DD, inclusive")
    parser.add_argument("--data-types", nargs="+", choices=DATA_TYPES,
                        default=["trades", "orderbook"],
                        help="Data types to pull (default trades orderbook)")
    parser.add_argument("--exchange", default="hyperliquid_futures",
                        choices=["hyperliquid_futures", "hyperliquid_spot"],
                        help="Exchange id (default hyperliquid_futures)")
    parser.add_argument("--out", default="./data/cryptohftdata",
                        help="Output directory (default ./data/cryptohftdata)")
    parser.add_argument("--api-key", default=os.environ.get("CRYPTOHFTDATA_API_KEY"),
                        help="Free API key; without one, 60 files/min/IP. "
                             "Also read from CRYPTOHFTDATA_API_KEY.")
    parser.add_argument("--rate-limit", type=float, default=1.0,
                        help="Seconds to wait between requests (default 1.0, "
                             "safe for the anonymous 60/min tier; use 0 with a key)")
    parser.add_argument("--retries", type=int, default=3,
                        help="Retries on 429/5xx (default 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List the files that would be pulled without downloading")
    return parser.parse_args()


def hour_range(start, end):
    current = dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc)
    stop = dt.datetime(end.year, end.month, end.day, 23, tzinfo=dt.timezone.utc)
    while current <= stop:
        yield current
        current += dt.timedelta(hours=1)


def download_one(session, url, params, dest, api_key, retries):
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, params=params, headers=headers, timeout=120)
        except Exception as exc:  # network error, retry
            last_error = str(exc)
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 200:
            if not resp.content.startswith(PARQUET_MAGIC):
                return False, "not a Parquet file"
            tmp = dest + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(resp.content)
            os.replace(tmp, dest)
            return True, f"{len(resp.content)} bytes"
        if resp.status_code == 404:
            return False, "missing (404)"
        if resp.status_code in (429, 500, 502, 503):
            wait = int(resp.headers.get("Retry-After", 2 ** attempt))
            last_error = f"HTTP {resp.status_code}"
            time.sleep(wait)
            continue
        return False, f"HTTP {resp.status_code}"
    return False, last_error or "failed"


def main():
    args = parse_args()
    if requests is None:
        print("error: requests is not installed. Run: pip install requests",
              file=sys.stderr)
        return 2
    # Preserve the case the caller gives: some coins are case-sensitive
    # on the API (kPEPE 500s as KPEPE).
    symbols = list(args.symbols)
    try:
        start = dt.date.fromisoformat(args.start)
        end = dt.date.fromisoformat(args.end)
    except ValueError:
        print("error: --start and --end must be YYYY-MM-DD", file=sys.stderr)
        return 2
    if end < start:
        print("error: --end is before --start", file=sys.stderr)
        return 2

    hours = list(hour_range(start, end))
    total = len(hours) * len(symbols) * len(args.data_types)
    print(f"symbols: {', '.join(symbols)}")
    print(f"hours: {len(hours)} ({hours[0]} to {hours[-1]} UTC)")
    print(f"data types: {', '.join(args.data_types)}")
    print(f"files to consider: {total}")
    if not args.api_key:
        print("anonymous tier: 60 files/min/IP, pacing "
              f"{args.rate_limit}s between requests")
    if args.dry_run:
        return 0

    downloaded, skipped, missing, failed = 0, 0, 0, 0
    session = requests.Session()
    for hour in hours:
        date = hour.strftime("%Y-%m-%d")
        hh = hour.strftime("%H")
        for symbol in symbols:
            for dtype in args.data_types:
                rel = f"{args.exchange}/{date}/{hh}/{symbol}_{dtype}.parquet"
                dest = os.path.join(args.out, rel)
                if os.path.exists(dest):
                    skipped += 1
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                ok, info = download_one(
                    session, BASE_URL, {"file": rel}, dest,
                    args.api_key, args.retries)
                if ok:
                    downloaded += 1
                elif info.startswith("missing"):
                    missing += 1
                else:
                    failed += 1
                    print(f"{rel}: {info}")
                if args.rate_limit:
                    time.sleep(args.rate_limit)
    print(f"done: downloaded {downloaded}, skipped existing {skipped}, "
          f"missing hours {missing}, failed {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
