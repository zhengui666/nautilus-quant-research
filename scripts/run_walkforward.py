#!/usr/bin/env python3
"""Run a backtest script over rolling walk-forward windows.

Usage:
    python run_walkforward.py <backtest.py> --start 2026-07-01 --end 2026-11-01 \
        --is-days 60 --oos-days 30 --step-days 30

The backtest script must accept --start and --end as ISO dates and
--out as a JSON path, and it must write a JSON object with at least
{"sharpe": <float>, "trades": <int>} for that window. The wrapper runs
the script once per in-sample window and once per out-of-sample window,
prints the per-window Sharpes, the concatenated out-of-sample Sharpe,
and the walk-forward efficiency, which is the out-of-sample Sharpe
divided by the in-sample Sharpe. It prints a verdict of DEPLOY,
REDUCED, PAPER, or REJECT, and exits 0 only on DEPLOY or REDUCED.

Walk-forward efficiency above 0.8 is excellent, above 0.6 is deployable,
above 0.4 is reduced allocation, and below 0.4 is paper trade only.
"""
import argparse
import json
import subprocess
import sys
from datetime import date, timedelta


def parse_iso(text):
    return date.fromisoformat(text)


def run_window(script, start, end, out_path):
    result = subprocess.run(
        [sys.executable, script, "--start", start.isoformat(),
         "--end", end.isoformat(), "--out", out_path],
        capture_output=True, text=True, timeout=3600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"backtest failed for {start} to {end}:\n{result.stderr[-2000:]}")
    with open(out_path, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a backtest over rolling walk-forward windows.")
    parser.add_argument("backtest")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--is-days", type=int, default=60)
    parser.add_argument("--oos-days", type=int, default=30)
    parser.add_argument("--step-days", type=int, default=30)
    args = parser.parse_args(argv)
    start = parse_iso(args.start)
    end = parse_iso(args.end)
    is_len = timedelta(days=args.is_days)
    oos_len = timedelta(days=args.oos_days)
    step = timedelta(days=args.step_days)
    windows = []
    cursor = start
    while cursor + is_len + oos_len <= end:
        windows.append((cursor, cursor + is_len, cursor + is_len + oos_len))
        cursor += step
    if not windows:
        print("FAIL: the date range holds no complete in-sample plus out-of-sample window")
        return 1
    print(f"windows: {len(windows)}, in-sample {args.is_days}d, out-of-sample {args.oos_days}d, step {args.step_days}d")
    is_sharpes = []
    oos_sharpes = []
    for i, (is_start, split, oos_end) in enumerate(windows, start=1):
        is_metrics = run_window(args.backtest, is_start, split, f"/tmp/wf_is_{i}.json")
        oos_metrics = run_window(args.backtest, split, oos_end, f"/tmp/wf_oos_{i}.json")
        is_sharpes.append(is_metrics.get("sharpe", float("nan")))
        oos_sharpes.append(oos_metrics.get("sharpe", float("nan")))
        print(f"window {i}: IS {is_start} to {split} Sharpe {is_metrics.get('sharpe')}, "
              f"OOS {split} to {oos_end} Sharpe {oos_metrics.get('sharpe')}, "
              f"OOS trades {oos_metrics.get('trades')}")
    n = len(is_sharpes)
    mean_is = sum(is_sharpes) / n
    mean_oos = sum(oos_sharpes) / n
    wfe = mean_oos / mean_is if mean_is else float("nan")
    print(f"mean IS Sharpe: {mean_is:.3f}")
    print(f"mean OOS Sharpe: {mean_oos:.3f}")
    print(f"walk-forward efficiency: {wfe:.3f}")
    if wfe >= 0.6:
        print("VERDICT: DEPLOY, walk-forward efficiency clears 0.6")
        return 0
    if wfe >= 0.4:
        print("VERDICT: REDUCED, walk-forward efficiency clears 0.4, deploy at reduced size")
        return 0
    print("VERDICT: REJECT, walk-forward efficiency below 0.4, paper trade only")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
