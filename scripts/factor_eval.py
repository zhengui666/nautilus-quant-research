#!/usr/bin/env python3
"""Evaluate a factor from a CSV of factor values and forward returns.

Usage:
    python factor_eval.py <csv_path> [--min-periods N]

CSV columns, one row per symbol per period:
    timestamp   period label, such as 2026-10-01T00:01:00Z
    symbol      coin symbol, such as BTCUSDT-PERP
    factor      factor value for that symbol at that period
    fwd_1       forward return over the next 1 period
    fwd_5       forward return over the next 5 periods (optional)
    fwd_20      forward return over the next 20 periods (optional)
    weight      portfolio weight for that symbol at that period (optional)

The script prints the Spearman rank IC per horizon, the ICIR, the IC
decay across horizons, the quantile monotonicity at the 1 period horizon,
and the turnover when a weight column is present. It prints a verdict of
PASS, WEAK, or FAIL. It uses only the standard library, so it runs in any
Python 3.10 or newer environment.

IC is judged against the same horizon baseline, never against daily
conventions. A factor with fewer than 30 periods is reported as
UNRELIABLE regardless of its IC.
"""
import argparse
import csv
import math
import sys
from collections import defaultdict


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def pearson(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    if den == 0:
        return 0.0
    return num / den


def spearman(xs, ys):
    return pearson(ranks(xs), ranks(ys))


def mean(values):
    return sum(values) / len(values) if values else float("nan")


def stdev(values):
    if len(values) < 2:
        return float("nan")
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def load(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", "symbol", "factor"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        fwd_cols = [c for c in (reader.fieldnames or []) if c.startswith("fwd_")]
        if not fwd_cols:
            raise ValueError("no fwd_* forward return columns found")
        for row in reader:
            try:
                rows.append({
                    "timestamp": row["timestamp"],
                    "symbol": row["symbol"],
                    "factor": float(row["factor"]),
                    "fwd": {c: float(row[c]) for c in fwd_cols},
                    "weight": float(row["weight"]) if row.get("weight") not in (None, "") else None,
                })
            except (TypeError, ValueError):
                continue
    return rows, fwd_cols


def ic_by_period(rows, fwd_col):
    by_period = defaultdict(list)
    for row in rows:
        by_period[row["timestamp"]].append(row)
    ics = []
    for period in sorted(by_period):
        group = by_period[period]
        if len(group) < 3:
            continue
        factors = [r["factor"] for r in group]
        rets = [r["fwd"][fwd_col] for r in group]
        if len(set(factors)) < 3 or len(set(rets)) < 3:
            continue
        ics.append(spearman(factors, rets))
    return ics


def quantile_monotonicity(rows, fwd_col, buckets=5):
    by_period = defaultdict(list)
    for row in rows:
        by_period[row["timestamp"]].append(row)
    bucket_returns = defaultdict(list)
    for period in sorted(by_period):
        group = sorted(by_period[period], key=lambda r: r["factor"])
        if len(group) < buckets:
            continue
        size = len(group) / buckets
        for i, row in enumerate(group):
            bucket = min(int(i / size), buckets - 1)
            bucket_returns[bucket].append(row["fwd"][fwd_col])
    means = [mean(bucket_returns[b]) for b in range(buckets) if bucket_returns[b]]
    if len(means) < buckets:
        return means, False
    rank_corr = spearman(list(range(len(means))), means)
    monotonic = abs(rank_corr) >= 0.8
    return means, monotonic


def turnover(rows):
    by_period = defaultdict(dict)
    for row in rows:
        if row["weight"] is not None:
            by_period[row["timestamp"]][row["symbol"]] = row["weight"]
    periods = sorted(by_period)
    if len(periods) < 2:
        return None
    changes = []
    for prev, cur in zip(periods, periods[1:]):
        symbols = set(by_period[prev]) | set(by_period[cur])
        delta = sum(abs(by_period[cur].get(s, 0.0) - by_period[prev].get(s, 0.0)) for s in symbols)
        changes.append(delta / 2.0)
    return mean(changes)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate a factor from factor values and forward returns.")
    parser.add_argument("csv_path")
    parser.add_argument("--min-periods", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        rows, fwd_cols = load(args.csv_path)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if not rows:
        print("FAIL: no usable rows in the CSV")
        return 1
    fwd_cols = sorted(fwd_cols, key=lambda c: int(c.split("_")[1]))
    print(f"rows: {len(rows)}, periods: {len({r['timestamp'] for r in rows})}, symbols: {len({r['symbol'] for r in rows})}")
    verdicts = []
    for col in fwd_cols:
        ics = ic_by_period(rows, col)
        if len(ics) < args.min_periods:
            print(f"{col}: IC n/a, only {len(ics)} periods, need {args.min_periods}")
            verdicts.append("UNRELIABLE")
            continue
        ic = mean(ics)
        icir = ic / stdev(ics) if stdev(ics) else float("nan")
        print(f"{col}: IC {ic:+.4f}, ICIR {icir:+.2f}, periods {len(ics)}, positive share {sum(1 for v in ics if v > 0) / len(ics):.2f}")
        verdicts.append("OK" if abs(ic) >= 0.02 else "WEAK")
    means, monotonic = quantile_monotonicity(rows, fwd_cols[0])
    print("quantile means:", ", ".join(f"{m:+.5f}" for m in means))
    print(f"quantile monotonic: {'yes' if monotonic else 'no'}")
    if not monotonic:
        verdicts.append("WEAK")
    turn = turnover(rows)
    if turn is None:
        print("turnover: n/a, no weight column")
    else:
        print(f"turnover per period: {turn:.4f}")
    if "UNRELIABLE" in verdicts:
        print("VERDICT: UNRELIABLE, too few periods to judge this factor")
        return 1
    if "WEAK" in verdicts or not monotonic:
        print("VERDICT: WEAK, the factor does not clear the evaluation gates")
        return 1
    print("VERDICT: PASS, the factor clears the evaluation gates at the tested horizons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
