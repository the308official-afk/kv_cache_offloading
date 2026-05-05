#!/usr/bin/env python3

"""Summarize live hint-router decision logs."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_rows(log_file: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with log_file.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_worker_name_map(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Worker name map must be a JSON object.")
    return {str(key): str(value) for key, value in payload.items()}


def apply_name_map(counts: Counter[str], worker_name_map: dict[str, str]) -> dict[str, int]:
    named: dict[str, int] = {}
    for worker_id, count in sorted(counts.items()):
        label = worker_name_map.get(worker_id, worker_id)
        named[label] = named.get(label, 0) + count
    return named


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * p
    lower = int(idx)
    upper = min(lower + 1, len(ordered) - 1)
    weight = idx - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def build_summary(rows: list[dict[str, Any]], worker_name_map: dict[str, str]) -> dict[str, Any]:
    success_rows = [row for row in rows if 200 <= int(row.get("status_code") or 0) < 300]
    latency_values = [float(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None]
    cache_scores = [float(row["cache_score"]) for row in rows if row.get("cache_score") is not None]
    load_scores = [float(row["load_score"]) for row in rows if row.get("load_score") is not None]
    priority_scores = [float(row["priority_score"]) for row in rows if row.get("priority_score") is not None]
    cached_tokens = [float(row["cached_tokens"]) for row in success_rows if row.get("cached_tokens") is not None]

    worker_counts = Counter(str(row.get("chosen_worker_id") or "unknown") for row in rows)
    shadow_backend_counts = Counter(
        str(row.get("shadow_preferred_backend_worker_id") or "unknown") for row in rows
    )
    actual_prefill_counts = Counter(
        str(row.get("actual_prefill_worker_id") or "unknown") for row in rows
    )
    actual_decode_counts = Counter(
        str(row.get("actual_decode_worker_id") or "unknown") for row in rows
    )
    phase_counts = Counter(
        str(((row.get("hint_payload") or {}).get("agent_phase")) or "unknown")
        for row in rows
    )
    group_counts = Counter(str(row.get("shared_prefix_group") or "unknown") for row in rows)
    comparable_rows = [
        row for row in rows
        if row.get("shadow_preferred_backend_worker_id") and row.get("actual_prefill_worker_id")
    ]
    prefill_matches = sum(
        1
        for row in comparable_rows
        if str(row.get("shadow_preferred_backend_worker_id"))
        == str(row.get("actual_prefill_worker_id"))
    )
    decode_matches = sum(
        1
        for row in comparable_rows
        if str(row.get("shadow_preferred_backend_worker_id"))
        == str(row.get("actual_decode_worker_id"))
    )
    matched_rows = [
        row
        for row in comparable_rows
        if str(row.get("shadow_preferred_backend_worker_id"))
        == str(row.get("actual_prefill_worker_id"))
    ]
    mismatched_rows = [
        row
        for row in comparable_rows
        if str(row.get("shadow_preferred_backend_worker_id"))
        != str(row.get("actual_prefill_worker_id"))
    ]

    def avg_metric(subset: list[dict[str, Any]], key: str) -> float | None:
        values = [float(row[key]) for row in subset if row.get(key) is not None]
        return round(statistics.fmean(values), 3) if values else None

    return {
        "total_requests": len(rows),
        "successful_requests": len(success_rows),
        "success_rate": round(len(success_rows) / len(rows), 4) if rows else 0.0,
        "avg_latency_ms": round(statistics.fmean(latency_values), 3) if latency_values else None,
        "p50_latency_ms": round(percentile(latency_values, 0.50), 3) if latency_values else None,
        "p95_latency_ms": round(percentile(latency_values, 0.95), 3) if latency_values else None,
        "avg_cached_tokens": round(statistics.fmean(cached_tokens), 3) if cached_tokens else None,
        "avg_cache_score": round(statistics.fmean(cache_scores), 4) if cache_scores else None,
        "avg_load_score": round(statistics.fmean(load_scores), 4) if load_scores else None,
        "avg_priority_score": round(statistics.fmean(priority_scores), 4) if priority_scores else None,
        "worker_counts": apply_name_map(worker_counts, worker_name_map),
        "shadow_preferred_backend_worker_counts": apply_name_map(shadow_backend_counts, worker_name_map),
        "actual_prefill_worker_counts": apply_name_map(actual_prefill_counts, worker_name_map),
        "actual_decode_worker_counts": apply_name_map(actual_decode_counts, worker_name_map),
        "alignment_rows": len(comparable_rows),
        "prefill_alignment_rate": (
            round(prefill_matches / len(comparable_rows), 4) if comparable_rows else None
        ),
        "decode_alignment_rate": (
            round(decode_matches / len(comparable_rows), 4) if comparable_rows else None
        ),
        "matched_rows": len(matched_rows),
        "mismatched_rows": len(mismatched_rows),
        "matched_avg_latency_ms": avg_metric(matched_rows, "latency_ms"),
        "mismatched_avg_latency_ms": avg_metric(mismatched_rows, "latency_ms"),
        "matched_avg_cached_tokens": avg_metric(matched_rows, "cached_tokens"),
        "mismatched_avg_cached_tokens": avg_metric(mismatched_rows, "cached_tokens"),
        "agent_phase_counts": dict(phase_counts),
        "shared_prefix_group_counts": dict(group_counts),
    }


def print_summary(summary: dict[str, Any], log_file: Path) -> None:
    print(f"log_file: {log_file}")
    print(
        f"success: {summary['successful_requests']}/{summary['total_requests']} "
        f"({summary['success_rate']:.1%})"
    )
    print(
        "latency_ms:"
        f" avg={summary['avg_latency_ms']}"
        f" p50={summary['p50_latency_ms']}"
        f" p95={summary['p95_latency_ms']}"
    )
    print(f"avg_cached_tokens: {summary['avg_cached_tokens']}")
    print(
        "policy_scores:"
        f" cache={summary['avg_cache_score']}"
        f" load={summary['avg_load_score']}"
        f" priority={summary['avg_priority_score']}"
    )
    print("worker_counts:")
    for worker_id, count in sorted(summary["worker_counts"].items()):
        print(f"  {worker_id}: {count}")
    print("shadow_preferred_backend_worker_counts:")
    for worker_id, count in sorted(summary["shadow_preferred_backend_worker_counts"].items()):
        print(f"  {worker_id}: {count}")
    print("actual_prefill_worker_counts:")
    for worker_id, count in sorted(summary["actual_prefill_worker_counts"].items()):
        print(f"  {worker_id}: {count}")
    print("actual_decode_worker_counts:")
    for worker_id, count in sorted(summary["actual_decode_worker_counts"].items()):
        print(f"  {worker_id}: {count}")
    print(
        "alignment:"
        f" rows={summary['alignment_rows']}"
        f" prefill={summary['prefill_alignment_rate']}"
        f" decode={summary['decode_alignment_rate']}"
    )
    print(
        "match_vs_mismatch:"
        f" matched_rows={summary['matched_rows']}"
        f" mismatched_rows={summary['mismatched_rows']}"
        f" matched_avg_latency_ms={summary['matched_avg_latency_ms']}"
        f" mismatched_avg_latency_ms={summary['mismatched_avg_latency_ms']}"
        f" matched_avg_cached_tokens={summary['matched_avg_cached_tokens']}"
        f" mismatched_avg_cached_tokens={summary['mismatched_avg_cached_tokens']}"
    )
    print("agent_phase_counts:")
    for phase, count in sorted(summary["agent_phase_counts"].items()):
        print(f"  {phase}: {count}")
    print("shared_prefix_group_counts:")
    for group, count in sorted(summary["shared_prefix_group_counts"].items()):
        print(f"  {group}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-file",
        default="hintbench/results/live_hint_router/decisions.jsonl",
        help="Path to the live hint-router decision log.",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path to write the summary JSON.",
    )
    parser.add_argument(
        "--worker-name-map",
        default="hintbench/runtime_patches/worker_name_map.json",
        help="Optional JSON file mapping Dynamo worker IDs to friendly names.",
    )
    args = parser.parse_args()

    log_file = Path(args.log_file)
    if not log_file.exists():
        raise SystemExit(f"Live router log not found: {log_file}")
    worker_name_map = load_worker_name_map(Path(args.worker_name_map))
    rows = load_rows(log_file)
    summary = build_summary(rows, worker_name_map)
    print_summary(summary, log_file)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
