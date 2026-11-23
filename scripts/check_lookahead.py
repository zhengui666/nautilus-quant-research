#!/usr/bin/env python3
"""Scan strategy and factor files for look-ahead bias patterns.

Usage:
    python check_lookahead.py <path> [<path> ...]

Each path is a Python file or a directory. Directories are scanned
recursively for .py files. Prints PASS or FAIL plus one line per hit,
then exits 0 on PASS and 1 on FAIL. Run it before reporting any result.

REJECT patterns (each hit is a failure):
  - shift with a negative period, which pulls future values into the past
  - rolling with center=True, which uses future bars in the window
  - bfill or two-sided interpolation on features, which fills from the future
  - indexing a future row, such as iloc[i+1] or close[i+1]
  - using the full sample to normalize a feature, such as a whole-series
    z-score computed inside a per-bar callback
  - hardcoded hindsight date filters that split on a date chosen after
    seeing the results
"""
import re
import sys
from pathlib import Path

PATTERNS = [
    (re.compile(r"\.shift\(\s*-"), "shift with a negative period pulls future values into the past"),
    (re.compile(r"rolling\([^)]*center\s*=\s*True"), "rolling with center=True uses future bars in the window"),
    (re.compile(r"\.bfill\("), "bfill fills feature values from the future"),
    (re.compile(r"interpolate\([^)]*limit_direction\s*=\s*['\"]both['\"]"), "two-sided interpolation fills feature values from the future"),
    (re.compile(r"\.iloc\[\s*[^]]*\+\s*1\s*\]"), "indexing a future row, such as iloc[i+1]"),
    (re.compile(r"\[\s*[^]]*\+\s*1\s*\]"), "indexing a future row, such as close[i+1]"),
    (re.compile(r"\(df\[[^\]]+\]\s*-\s*df\[[^\]]+\]\.mean\(\)\)\s*/\s*df\[[^\]]+\]\.std\(\)"), "whole-sample z-score normalizes with future information"),
    (re.compile(r"start_date\s*=\s*['\"]20\d\d-\d\d-\d\d['\"]"), "hardcoded start date may be a hindsight split, confirm it was chosen before seeing results"),
]


def collect_paths(paths):
    files = []
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        else:
            print(f"SKIP: {p} is not a Python file or directory")
    return files


def scan_file(path):
    hits = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [(0, f"cannot read file: {exc}")]
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern, reason in PATTERNS:
            if pattern.search(line):
                hits.append((lineno, reason))
    return hits


def main(argv):
    if len(argv) < 2:
        print("Usage: python check_lookahead.py <path> [<path> ...]")
        return 2
    files = collect_paths(argv[1:])
    if not files:
        print("FAIL: no Python files found")
        return 1
    total_hits = 0
    for path in files:
        hits = scan_file(path)
        for lineno, reason in hits:
            print(f"FAIL: {path}:{lineno}: {reason}")
            total_hits += 1
    if total_hits:
        print(f"FAIL: {total_hits} look-ahead pattern(s) found in {len(files)} file(s)")
        return 1
    print(f"PASS: no look-ahead patterns found in {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
