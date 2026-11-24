#!/usr/bin/env python3
"""Download Hydromancer Reservoir 1-second candles for Hyperliquid perps.

Reservoir publishes ready-made 1-second OHLCV candles for every Hyperliquid
perp market as daily Parquet files in a requester-pays S3 bucket. This script
pulls only the symbols and dates you ask for, one S3 read per day, and writes
one Parquet file per symbol per day.

Source: https://docs.hydromancer.xyz/reservoir/hyperliquid
Bucket: s3://hydromancer-reservoir, region ap-northeast-1, requester pays.
Candles path: by_dex/hyperliquid/candles/1s/date=YYYY-MM-DD/candles.parquet
Coverage: complete from 2025-07-28; candles backfilled before the Aug 2025
cutoff; updated daily, never includes today.

Cost: the vendor charges nothing. AWS egress from ap-northeast-1 is about
$0.114/GB, and the whole all-market 1s candle set is about 44 MB/day, so a
full ~16 month pull is roughly 21 GB, about $2.40, and $0 inside the AWS
100 GB/month free transfer allowance. Pulling a 20-50 symbol universe costs
far less because this script filters by coin in DuckDB before writing.

Requirements: an AWS account with credentials that can pay requester-pays
charges. Set them the usual way, for example AWS_ACCESS_KEY_ID and
AWS_SECRET_ACCESS_KEY, or pass --aws-profile. Without credentials the S3
read fails with a 403; that is expected, not a bug in this script.

Needs: pip install duckdb

Usage:
    python scripts/download_reservoir.py --symbols BTC ETH --start 2025-09-01 --end 2025-09-30
    python scripts/download_reservoir.py --symbols BTC --start 2026-11-01 --end 2026-11-23 --resample 1m
    python scripts/download_reservoir.py --symbols BTC --start 2025-09-01 --end 2025-09-30 --dry-run

Output layout under --out (default ./data/reservoir):
    candles_1s/<COIN>/<YYYY-MM-DD>.parquet
    candles_1m/<COIN>/<YYYY-MM-DD>.parquet   (only with --resample 1m)

Each file holds columns timestamp, coin, open, high, low, close, volume,
trade_count, sorted by timestamp ascending. Timestamps are exchange time.
Thin symbols have many empty seconds; this script keeps them empty rather
than forward-filling, so decide the fill rule deliberately in the backtest.
"""

import argparse
import datetime as dt
import os
import sys
from urllib.parse import urlparse, urlunparse


def sanitize_proxy_env():
    """Strip credentials from proxy env vars before DuckDB starts.

    DuckDB's httpfs parses http_proxy/https_proxy at load time and chokes
    on the userinfo part (http://user:pass@host:port). The host and port
    are kept, so proxied egress still works; only the embedded credentials
    are dropped. Harmless on machines without proxy env vars.
    """
    for var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        value = os.environ.get(var)
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.username or parsed.password:
            host = parsed.hostname or ""
            if parsed.port:
                host += f":{parsed.port}"
            os.environ[var] = urlunparse(
                (parsed.scheme, host, "", "", "", ""))

BUCKET = "s3://hydromancer-reservoir"
REGION = "ap-northeast-1"
CANDLES_PREFIX = "by_dex/hyperliquid/candles/1s/date={date}/candles.parquet"
CANDLE_COLUMNS = "timestamp, coin, open, high, low, close, volume, trade_count"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download Reservoir 1s candles for Hyperliquid perps."
    )
    parser.add_argument("--symbols", nargs="+", required=True,
                        help="Perp symbols, e.g. BTC ETH SOL")
    parser.add_argument("--start", required=True,
                        help="First UTC date, YYYY-MM-DD")
    parser.add_argument("--end", required=True,
                        help="Last UTC date, YYYY-MM-DD, inclusive")
    parser.add_argument("--out", default="./data/reservoir",
                        help="Output directory (default ./data/reservoir)")
    parser.add_argument("--resample", choices=["none", "1m"], default="none",
                        help="Also write 1-minute bars aggregated from the 1s candles")
    parser.add_argument("--aws-profile", default=None,
                        help="AWS profile name for requester-pays charges")
    parser.add_argument("--dry-run", action="store_true",
                        help="List what would be pulled without downloading")
    return parser.parse_args()


def date_range(start, end):
    day = start
    while day <= end:
        yield day
        day += dt.timedelta(days=1)


def main():
    args = parse_args()
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

    days = list(date_range(start, end))
    print(f"symbols: {', '.join(symbols)}")
    print(f"days: {len(days)} ({start} to {end})")
    print(f"files to write: {len(days) * len(symbols)}"
          + (" x2 with --resample 1m" if args.resample != "none" else ""))
    print("note: each daily S3 file is about 44 MB all-market; "
          "egress about $0.114/GB from ap-northeast-1")
    if args.dry_run:
        return 0

    try:
        import duckdb
    except ImportError:
        print("error: duckdb is not installed. Run: pip install duckdb",
              file=sys.stderr)
        return 2

    sanitize_proxy_env()
    con = duckdb.connect()
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    con.execute(f"SET s3_region = '{REGION}'")
    try:
        con.execute("SET s3_requester_pays = true")
    except Exception as exc:  # older DuckDB builds lack the setting
        print(f"warning: could not set s3_requester_pays: {exc}")
    if args.aws_profile:
        con.execute(f"SET s3_profile = '{args.aws_profile}'")
    if not os.environ.get("AWS_ACCESS_KEY_ID") and not args.aws_profile:
        print("warning: no AWS_ACCESS_KEY_ID in the environment and no "
              "--aws-profile given. Requester-pays reads need credentials; "
              "expect a 403 if none are configured.")

    wanted, skipped, missing = 0, 0, 0
    symbol_list = ", ".join(f"'{s}'" for s in symbols)
    for day in days:
        key = CANDLES_PREFIX.format(date=day.isoformat())
        uri = f"{BUCKET}/{key}"
        try:
            con.execute(
                f"CREATE OR REPLACE TEMP TABLE day AS "
                f"SELECT {CANDLE_COLUMNS} FROM read_parquet('{uri}') "
                f"WHERE coin IN ({symbol_list})"
            )
        except Exception as exc:
            message = str(exc)
            if "403" in message or "Requester Pays" in message:
                print("error: S3 refused the read with 403. The bucket is "
                      "requester-pays, so AWS credentials that can pay the "
                      "egress are required. Set AWS_ACCESS_KEY_ID and "
                      "AWS_SECRET_ACCESS_KEY, or pass --aws-profile, then "
                      "retry.", file=sys.stderr)
                return 3
            print(f"{day}: no data ({exc})")
            missing += 1
            continue
        for symbol in symbols:
            out_path = os.path.join(args.out, "candles_1s", symbol,
                                    f"{day.isoformat()}.parquet")
            if os.path.exists(out_path):
                skipped += 1
                continue
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            con.execute(
                f"COPY (SELECT * FROM day WHERE coin = '{symbol}' "
                f"ORDER BY timestamp) TO '{out_path}' (FORMAT PARQUET)"
            )
            wanted += 1
            if args.resample == "1m":
                out_1m = os.path.join(args.out, "candles_1m", symbol,
                                      f"{day.isoformat()}.parquet")
                if not os.path.exists(out_1m):
                    os.makedirs(os.path.dirname(out_1m), exist_ok=True)
                    con.execute(
                        "COPY (SELECT time_bucket(INTERVAL '1 minute', timestamp) AS timestamp, "
                        f"coin, first(open) AS open, max(high) AS high, "
                        f"min(low) AS low, last(close) AS close, "
                        f"sum(volume) AS volume, sum(trade_count) AS trade_count "
                        f"FROM day WHERE coin = '{symbol}' "
                        f"GROUP BY time_bucket(INTERVAL '1 minute', timestamp), coin "
                        f"ORDER BY timestamp) TO '{out_1m}' (FORMAT PARQUET)"
                    )
                    wanted += 1
                else:
                    skipped += 1
        con.execute("DROP TABLE day")
    print(f"done: wrote {wanted}, skipped existing {skipped}, "
          f"days with no data {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
