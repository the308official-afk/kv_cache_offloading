#!/usr/bin/env python3
"""Rewrite cache-pinning retention reports with simpler column names."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


MATRIX_COLUMNS = [
    "status",
    "run_id",
    "model",
    "kv_tier",
    "arm",
    "cache_control",
    "distractors",
    "first_http_status",
    "replay_http_status",
    "first_ms",
    "replay_ms",
    "delta_ms",
    "speedup_x",
    "replay_cached",
    "replay_reuse",
    "warm",
    "warm_source",
    "reuse_signal",
    "req_cache_status",
    "req_cache_values",
    "worker_cache_status",
    "worker_cache_values",
    "replay_evicts",
    "replay_evict_cache",
    "replay_evict_cache_match",
    "replay_evict_status",
    "result",
]

COMPARISON_COLUMNS = [
    "status",
    "model",
    "attribution_mode",
    "kv_tier",
    "control_cache_control",
    "protected_cache_control",
    "control_last_warm",
    "control_first_cold",
    "protected_last_warm",
    "protected_first_cold",
    "threshold_gap",
    "worker_cache_status",
    "worker_priority_ready",
    "worker_priority_path",
    "result",
    "sweep_result",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--comparison", required=True)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pick(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        if key in row and row.get(key, "") != "":
            return row.get(key, "")
    return ""


def compact_matrix_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "status": pick(row, "status", "sweep_status"),
        "run_id": pick(row, "run_id", "sweep_id", "retention_sweep_id"),
        "model": pick(row, "model"),
        "kv_tier": pick(row, "kv_tier", "kv_tier_mode"),
        "arm": pick(row, "arm"),
        "cache_control": pick(row, "cache_control", "protected_cache", "protected_cache_control_profile"),
        "distractors": pick(row, "distractors", "distractor_count"),
        "first_http_status": pick(row, "first_http_status", "first_status", "a_first_status"),
        "replay_http_status": pick(row, "replay_http_status", "replay_status", "a_replay_status"),
        "first_ms": pick(row, "first_ms", "a_first_latency_ms"),
        "replay_ms": pick(row, "replay_ms", "a_replay_latency_ms"),
        "delta_ms": pick(row, "delta_ms", "replay_delta_ms", "a_replay_latency_delta_ms"),
        "speedup_x": pick(row, "speedup_x", "replay_speedup", "a_replay_speedup_ratio"),
        "replay_cached": pick(row, "replay_cached", "a_replay_cached_tokens"),
        "replay_reuse": pick(row, "replay_reuse", "a_replay_cache_reuse_ratio"),
        "warm": pick(row, "warm", "survived", "survived_effective"),
        "warm_source": pick(row, "warm_source", "survival_source", "effective_survival_source"),
        "reuse_signal": pick(row, "reuse_signal", "reuse_status"),
        "req_cache_status": pick(row, "req_cache_status", "request_cache_control_status"),
        "req_cache_values": pick(row, "req_cache_values", "request_cache_control_values"),
        "worker_cache_status": pick(row, "worker_cache_status", "worker_cache_control_status"),
        "worker_cache_values": pick(row, "worker_cache_values", "worker_cache_control_values"),
        "replay_evicts": pick(row, "replay_evicts", "a_replay_sglang_cache_evict_events"),
        "replay_evict_cache": pick(row, "replay_evict_cache", "a_replay_sglang_evict_cache_control_values"),
        "replay_evict_cache_match": pick(row, "replay_evict_cache_match", "a_replay_sglang_evict_cache_control_match"),
        "replay_evict_status": pick(row, "replay_evict_status", "a_replay_sglang_evict_identity_status"),
        "result": pick(row, "result", "effect_status", "hint_runtime_effect_status"),
    }


def compact_comparison_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "status": pick(row, "status", "sweep_status"),
        "model": pick(row, "model"),
        "attribution_mode": pick(row, "attribution_mode", "retention_attribution_mode"),
        "kv_tier": pick(row, "kv_tier", "kv_tier_mode"),
        "control_cache_control": pick(row, "control_cache_control", "control_cache_control_profile"),
        "protected_cache_control": pick(row, "protected_cache_control", "protected_cache_control_profile"),
        "control_last_warm": pick(row, "control_last_warm", "control_last_survived_distractor_count"),
        "control_first_cold": pick(row, "control_first_cold", "control_first_evicted_distractor_count"),
        "protected_last_warm": pick(row, "protected_last_warm", "protected_last_survived_distractor_count"),
        "protected_first_cold": pick(row, "protected_first_cold", "protected_first_evicted_distractor_count"),
        "threshold_gap": pick(row, "threshold_gap", "threshold_gap_distractors"),
        "worker_cache_status": pick(row, "worker_cache_status", "worker_cache_control_status"),
        "worker_priority_ready": pick(row, "worker_priority_ready", "worker_priority_mechanism_ready"),
        "worker_priority_path": pick(row, "worker_priority_path", "worker_priority_path_status"),
        "result": pick(row, "result", "hint_runtime_effect_status"),
        "sweep_result": pick(row, "sweep_result", "interpretation"),
    }


def main() -> int:
    args = parse_args()
    matrix_path = Path(args.matrix)
    comparison_path = Path(args.comparison)

    matrix_rows = [compact_matrix_row(row) for row in read_csv(matrix_path)]
    comparison_rows = [compact_comparison_row(row) for row in read_csv(comparison_path)]

    if matrix_rows:
        write_csv(matrix_path, matrix_rows, MATRIX_COLUMNS)
    if comparison_rows:
        write_csv(comparison_path, comparison_rows, COMPARISON_COLUMNS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
