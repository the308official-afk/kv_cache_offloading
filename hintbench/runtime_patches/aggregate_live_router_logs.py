#!/usr/bin/env python3

"""Aggregate multiple live hint-router logs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hintbench.runtime_patches.analyze_live_router_log import (  # noqa: E402
    build_summary,
    load_rows,
    load_worker_name_map,
)


def print_run_summary(log_file: Path, summary: dict[str, object]) -> None:
    print(
        f"{log_file.name}:"
        f" success={summary['successful_requests']}/{summary['total_requests']}"
        f" avg_latency_ms={summary['avg_latency_ms']}"
        f" prefill_alignment={summary['prefill_alignment_rate']}"
        f" matched_avg_latency_ms={summary['matched_avg_latency_ms']}"
        f" mismatched_avg_latency_ms={summary['mismatched_avg_latency_ms']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "log_files",
        nargs="+",
        help="One or more live router decision logs to aggregate.",
    )
    parser.add_argument(
        "--worker-name-map",
        default="hintbench/runtime_patches/worker_name_map.json",
        help="Optional JSON file mapping Dynamo worker IDs to friendly names.",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path to write the aggregate summary JSON.",
    )
    args = parser.parse_args()

    worker_name_map = load_worker_name_map(Path(args.worker_name_map))
    all_rows: list[dict] = []
    per_log: list[dict[str, object]] = []

    for raw_path in args.log_files:
        log_file = Path(raw_path)
        if not log_file.exists():
            raise SystemExit(f"Live router log not found: {log_file}")
        rows = load_rows(log_file)
        summary = build_summary(rows, worker_name_map)
        per_log.append({"log_file": str(log_file), "summary": summary})
        all_rows.extend(rows)

    aggregate = build_summary(all_rows, worker_name_map)

    print("per_log:")
    for item in per_log:
        print_run_summary(Path(str(item["log_file"])), dict(item["summary"]))
    print("aggregate:")
    print(
        f"  logs={len(per_log)}"
        f" total_requests={aggregate['total_requests']}"
        f" success={aggregate['successful_requests']}/{aggregate['total_requests']}"
        f" avg_latency_ms={aggregate['avg_latency_ms']}"
        f" p95_latency_ms={aggregate['p95_latency_ms']}"
        f" prefill_alignment={aggregate['prefill_alignment_rate']}"
        f" decode_alignment={aggregate['decode_alignment_rate']}"
        f" matched_avg_latency_ms={aggregate['matched_avg_latency_ms']}"
        f" mismatched_avg_latency_ms={aggregate['mismatched_avg_latency_ms']}"
        f" matched_avg_cached_tokens={aggregate['matched_avg_cached_tokens']}"
        f" mismatched_avg_cached_tokens={aggregate['mismatched_avg_cached_tokens']}"
    )

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {
                    "per_log": per_log,
                    "aggregate": aggregate,
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
