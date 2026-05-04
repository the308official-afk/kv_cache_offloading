#!/usr/bin/env python3

"""Compare multiple HintBench run directories side by side."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize_run(run_dir: Path) -> dict:
    metadata = load_json(run_dir / "metadata.json")
    summary = load_json(run_dir / "summary.json")
    results = load_jsonl(run_dir / "results.jsonl")

    success_rows = [row for row in results if row.get("success")]
    latencies = [float(row["latency_ms"]) for row in success_rows if row.get("latency_ms") is not None]
    cached_tokens = [
        float(row["cached_tokens"])
        for row in success_rows
        if row.get("cached_tokens") is not None
    ]
    kv_hit_rates = []
    worker_pairs: dict[str, int] = {}

    for row in success_rows:
        raw_response = row.get("raw_response") or {}
        nvext = raw_response.get("nvext") or {}
        timing = nvext.get("timing") or {}
        worker_id = nvext.get("worker_id") or {}

        kv_hit_rate = timing.get("kv_hit_rate")
        if kv_hit_rate is not None:
            kv_hit_rates.append(float(kv_hit_rate))

        prefill = worker_id.get("prefill_worker_id")
        decode = worker_id.get("decode_worker_id")
        if prefill is not None or decode is not None:
            key = f"{prefill}->{decode}"
            worker_pairs[key] = worker_pairs.get(key, 0) + 1

    return {
        "run_dir": str(run_dir),
        "experiment_name": metadata.get("experiment_name", run_dir.name),
        "router_mode": metadata.get("router_mode"),
        "model": metadata.get("model"),
        "results_timezone": metadata.get("results_timezone"),
        "run_started_at": metadata.get("run_started_at"),
        "total_requests": summary.get("total_requests"),
        "successful_requests": summary.get("successful_requests"),
        "failed_requests": summary.get("failed_requests"),
        "avg_latency_ms": summary.get("avg_latency_ms"),
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "p99_latency_ms": percentile(latencies, 0.99),
        "avg_cached_tokens": summary.get("avg_cached_tokens"),
        "max_cached_tokens": max(cached_tokens) if cached_tokens else None,
        "avg_kv_hit_rate": statistics.mean(kv_hit_rates) if kv_hit_rates else None,
        "worker_pairs": worker_pairs,
    }


def render_table(rows: list[dict]) -> str:
    headers = [
        "experiment",
        "router",
        "success",
        "avg_ms",
        "p50_ms",
        "p95_ms",
        "avg_cached",
        "avg_kv_hit",
        "run_started_at",
    ]
    table_rows = []
    for row in rows:
        total = row["total_requests"] or 0
        success = row["successful_requests"] or 0
        table_rows.append([
            str(row["experiment_name"]),
            str(row["router_mode"]),
            f"{success}/{total}",
            format_num(row["avg_latency_ms"]),
            format_num(row["p50_latency_ms"]),
            format_num(row["p95_latency_ms"]),
            format_num(row["avg_cached_tokens"]),
            format_num(row["avg_kv_hit_rate"]),
            str(row["run_started_at"]),
        ])

    widths = [len(header) for header in headers]
    for values in table_rows:
        for i, value in enumerate(values):
            widths[i] = max(widths[i], len(value))

    def fmt_line(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[i]) for i, value in enumerate(values))

    divider = "-+-".join("-" * width for width in widths)
    lines = [fmt_line(headers), divider]
    lines.extend(fmt_line(values) for values in table_rows)
    return "\n".join(lines)


def format_num(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "run_dirs",
        nargs="+",
        help="One or more HintBench run directories to compare.",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path to write the structured comparison JSON.",
    )
    args = parser.parse_args()

    rows = [summarize_run(Path(run_dir)) for run_dir in args.run_dirs]

    print(render_table(rows))
    print()

    for row in rows:
        worker_pairs = row["worker_pairs"] or {}
        if worker_pairs:
            print(f"{row['experiment_name']} worker pairs:")
            for worker_key, count in sorted(worker_pairs.items()):
                print(f"  {worker_key}: {count}")
            print()

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
