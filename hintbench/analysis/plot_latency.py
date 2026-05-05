#!/usr/bin/env python3

"""Compare latency metrics across multiple HintBench runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hintbench.analysis.common import format_num, load_run, percentile, render_table


def summarize_latency(run_dir: Path) -> dict:
    run = load_run(run_dir)
    metadata = run["metadata"]
    results = run["results"]

    success_rows = [row for row in results if row.get("success")]
    latencies = [float(row["latency_ms"]) for row in success_rows if row.get("latency_ms") is not None]
    ttfts = [float(row["ttft_ms"]) for row in success_rows if row.get("ttft_ms") is not None]

    return {
        "experiment_name": metadata.get("experiment_name", run_dir.name),
        "router_mode": metadata.get("router_mode"),
        "run_started_at": metadata.get("run_started_at"),
        "successful_requests": len(success_rows),
        "total_requests": len(results),
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "p99_latency_ms": percentile(latencies, 0.99),
        "avg_ttft_ms": sum(ttfts) / len(ttfts) if ttfts else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dirs", nargs="+", help="One or more HintBench run directories.")
    parser.add_argument("--json-output", help="Optional path to write structured JSON.")
    args = parser.parse_args()

    rows = [summarize_latency(Path(run_dir)) for run_dir in args.run_dirs]

    headers = [
        "experiment",
        "router",
        "success",
        "avg_ms",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "avg_ttft_ms",
        "run_started_at",
    ]
    table_rows = []
    for row in rows:
        table_rows.append([
            str(row["experiment_name"]),
            str(row["router_mode"]),
            f"{row['successful_requests']}/{row['total_requests']}",
            format_num(row["avg_latency_ms"]),
            format_num(row["p50_latency_ms"]),
            format_num(row["p95_latency_ms"]),
            format_num(row["p99_latency_ms"]),
            format_num(row["avg_ttft_ms"]),
            str(row["run_started_at"]),
        ])

    print(render_table(headers, table_rows))

    if args.json_output:
        Path(args.json_output).write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
