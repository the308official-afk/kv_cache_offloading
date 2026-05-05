#!/usr/bin/env python3

"""Compare worker selection counts across multiple HintBench runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hintbench.analysis.common import load_run, render_table


def summarize_workers(run_dir: Path) -> dict:
    run = load_run(run_dir)
    metadata = run["metadata"]
    results = run["results"]

    worker_counts: dict[str, int] = {}
    for row in results:
        if not row.get("success"):
            continue
        worker = row.get("worker_id") or {}
        prefill = worker.get("prefill_worker_id")
        decode = worker.get("decode_worker_id")
        if prefill is None and decode is None:
            continue
        key = f"{prefill}->{decode}"
        worker_counts[key] = worker_counts.get(key, 0) + 1

    return {
        "experiment_name": metadata.get("experiment_name", run_dir.name),
        "router_mode": metadata.get("router_mode"),
        "worker_counts": worker_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dirs", nargs="+", help="One or more HintBench run directories.")
    parser.add_argument("--json-output", help="Optional path to write structured JSON.")
    args = parser.parse_args()

    rows = [summarize_workers(Path(run_dir)) for run_dir in args.run_dirs]
    worker_keys = sorted({key for row in rows for key in row["worker_counts"].keys()})

    headers = ["experiment", "router", *worker_keys]
    table_rows: list[list[str]] = []
    for row in rows:
        values = [
            str(row["experiment_name"]),
            str(row["router_mode"]),
        ]
        for key in worker_keys:
            values.append(str(row["worker_counts"].get(key, 0)))
        table_rows.append(values)

    print(render_table(headers, table_rows))

    if args.json_output:
        Path(args.json_output).write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
