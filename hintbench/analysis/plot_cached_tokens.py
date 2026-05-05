#!/usr/bin/env python3

"""Compare cache-reuse metrics across multiple HintBench runs."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hintbench.analysis.common import format_num, load_run, render_table


def summarize_cache(run_dir: Path) -> dict:
    run = load_run(run_dir)
    metadata = run["metadata"]
    results = run["results"]

    success_rows = [row for row in results if row.get("success")]
    cached_tokens = [
        float(row["cached_tokens"])
        for row in success_rows
        if row.get("cached_tokens") is not None
    ]
    kv_hit_rates = [
        float(row["kv_hit_rate"])
        for row in success_rows
        if row.get("kv_hit_rate") is not None
    ]

    return {
        "experiment_name": metadata.get("experiment_name", run_dir.name),
        "router_mode": metadata.get("router_mode"),
        "successful_requests": len(success_rows),
        "total_requests": len(results),
        "avg_cached_tokens": statistics.mean(cached_tokens) if cached_tokens else None,
        "max_cached_tokens": max(cached_tokens) if cached_tokens else None,
        "avg_kv_hit_rate": statistics.mean(kv_hit_rates) if kv_hit_rates else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dirs", nargs="+", help="One or more HintBench run directories.")
    parser.add_argument("--json-output", help="Optional path to write structured JSON.")
    args = parser.parse_args()

    rows = [summarize_cache(Path(run_dir)) for run_dir in args.run_dirs]

    headers = [
        "experiment",
        "router",
        "success",
        "avg_cached",
        "max_cached",
        "avg_kv_hit",
    ]
    table_rows = []
    for row in rows:
        table_rows.append([
            str(row["experiment_name"]),
            str(row["router_mode"]),
            f"{row['successful_requests']}/{row['total_requests']}",
            format_num(row["avg_cached_tokens"]),
            format_num(row["max_cached_tokens"]),
            format_num(row["avg_kv_hit_rate"]),
        ])

    print(render_table(headers, table_rows))

    if args.json_output:
        Path(args.json_output).write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
