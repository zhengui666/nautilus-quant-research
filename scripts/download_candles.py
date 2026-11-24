#!/usr/bin/env python3
"""Download daily candles from the official Hyperliquid API.

candleSnapshot caps at 5000 candles per call, so one call per coin covers
the whole window at daily resolution. Daily closes give the forward returns
needed to evaluate the funding-carry factor; minute bars come later from
CryptoHFTData trades.

Endpoint: POST https://api.hyperliquid.xyz/info, no key, no account.
Body: {"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "1d",
       "startTime": <ms>, "endTime": <ms>}}
Response rows: {"t", "T", "s", "i", "o", "c", "h", "l", "v", "n"}

Usage:
    python scripts/download_candles.py --symbols BTC ETH --start 2025-07-28 --end 2026-11-23
    python scripts/download_candles.py --symbols BTC --start 2025-07-28 --end 2026-11-23 --interval 1h

Output under --out (default ./data/candles):
    candles_1d/{COIN}.parquet     columns: time, open, high, low, close, volume, trades
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download Hyperliquid candles from the official API.")
    parser.add_argument("--symbols", nargs="+", required=True,
                        help="Perp symbols, e.g. BTC ETH SOL")
    parser.add_argument("--start", required=True,
                        help="First UTC date, YYYY-MM-DD")
    parser.add_argument("--end", required=True,
                        help="Last UTC date, YYYY-MM-DD, inclusive")
    parser.add_argument("--interval", default="1d",
                        help="Candle interval, e.g. 1d, 1h, 15m (default 1d)")
    parser.add_argument("--out", default="./data/candles",
                        help="Output directory (default ./data/candles)")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Seconds between API calls (default 0.5)")
    parser.add_argument("--retries", type=int, default=5,
                        help="Retries per call on 429/5xx (default 5)")
    parser.add_argument("--force", action="store_true",
                        help="Re-download coins whose file already exists")
    return parser.parse_args()


def fetch_candles(session, coin, interval, start_ms, end_ms, delay, retries):
    rows = []
    cursor = start_ms
    while True:
        page = None
        last_error = None
        for attempt in range(retries + 1):
            try:
                resp = session.post(
                    API_URL,
                    json={"type": "candleSnapshot",
                          "req": {"coin": coin, "interval": interval,
                                  "startTime": cursor, "endTime": end_ms}},
                    timeout=60,
                )
            except Exception as exc:
                last_error = str(exc)
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 200:
                page = resp.json()
                break
            if resp.status_code in (429, 500, 502, 503):
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                last_error = f"HTTP {resp.status_code}"
                print(f"{coin}: {last_error}, waiting {wait}s "
                      f"(attempt {attempt + 1}/{retries + 1})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        if page is None:
            raise RuntimeError(last_error or "candle fetch failed")
        if not page:
            break
        rows.extend(page)
        if len(page) < 5000:
            break
        cursor = int(page[-1]["T"]) + 1
        time.sleep(delay)
    return rows


def write_candles_parquet(rows, dest):
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.table({
        "time": pa.array([int(r["t"]) for r in rows], type=pa.int64()),
        "open": pa.array([float(r["o"]) for r in rows], type=pa.float64()),
        "high": pa.array([float(r["h"]) for r in rows], type=pa.float64()),
        "low": pa.array([float(r["l"]) for r in rows], type=pa.float64()),
        "close": pa.array([float(r["c"]) for r in rows], type=pa.float64()),
        "volume": pa.array([float(r["v"]) for r in rows], type=pa.float64()),
        "trades": pa.array([int(r["n"]) for r in rows], type=pa.int64()),
    })
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    pq.write_table(table, dest)


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
    start_ms = int(dt.datetime(start.year, start.month, start.day,
                               tzinfo=dt.timezone.utc).timestamp() * 1000)
    end_ms = int(dt.datetime(end.year, end.month, end.day, 23, 59, 59,
                             tzinfo=dt.timezone.utc).timestamp() * 1000)
    print(f"symbols: {', '.join(symbols)}")
    print(f"interval: {args.interval}, window: {start} to {end}")
    session = requests.Session()
    for symbol in symbols:
        dest = os.path.join(args.out, f"candles_{args.interval}",
                            f"{symbol}.parquet")
        if os.path.exists(dest) and not args.force:
            print(f"{symbol}: already downloaded, skipping")
            continue
        print(f"{symbol}: fetching {args.interval} candles...")
        try:
            rows = fetch_candles(session, symbol, args.interval,
                                 start_ms, end_ms, args.delay, args.retries)
        except Exception as exc:
            print(f"{symbol}: candle fetch failed: {exc}", file=sys.stderr)
            continue
        if not rows:
            print(f"{symbol}: no candles in window")
            continue
        rows.sort(key=lambda r: int(r["t"]))
        write_candles_parquet(rows, dest)
        first = dt.datetime.fromtimestamp(rows[0]["t"] / 1000,
                                          dt.timezone.utc)
        last = dt.datetime.fromtimestamp(rows[-1]["t"] / 1000,
                                         dt.timezone.utc)
        print(f"{symbol}: {len(rows)} candles, {first} to {last} -> {dest}")
        time.sleep(args.delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
