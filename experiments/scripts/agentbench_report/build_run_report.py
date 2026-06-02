#!/usr/bin/env python3
"""Build a compact run-level report from AgentBench and SGLang artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRANSFER_PREFIX = "[SGLANG_TRANSFER_JSON] "
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
TIMESTAMP_RE = re.compile(r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[^\s]+Z)")
PREFILL_RE = re.compile(
    r"Prefill batch, #new-seq: (?P<new_seq>\d+), #new-token: (?P<new_token>\d+), "
    r"#cached-token: (?P<cached_token>\d+), token usage: (?P<token_usage>[0-9.]+), "
    r"#running-req: (?P<running_req>\d+), #queue-req: (?P<queue_req>\d+), "
    r"input throughput \(token/s\): (?P<input_throughput_tps>[0-9.]+), "
    r"cuda graph: (?P<cuda_graph>True|False)"
)
DECODE_RE = re.compile(
    r"Decode batch, #running-req: (?P<running_req>\d+), #token: (?P<token>\d+), "
    r"token usage: (?P<token_usage>[0-9.]+), cuda graph: (?P<cuda_graph>True|False), "
    r"gen throughput \(token/s\): (?P<gen_throughput_tps>[0-9.]+), "
    r"#queue-req: (?P<queue_req>\d+)"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def ms_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return (end - start).total_seconds() * 1000.0


def clean_log_line(line: str) -> str:
    return ANSI_RE.sub("", line)


def latest_agentbench_result(root: Path) -> Path:
    results_root = root / "experiments/raw/agentbench/results"
    candidates = [path for path in results_root.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No AgentBench result directories under {results_root}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def latest_transfer_log(root: Path) -> Path | None:
    log_root = root / "experiments/raw/sglang_transfer_logs"
    latest_link = log_root / "latest_sglang_transfer_events.jsonl"
    if latest_link.exists():
        return latest_link
    candidates = sorted(log_root.glob("sglang_transfer_events*.jsonl"), key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def first_row(path: Path) -> dict[str, str]:
    rows = read_csv_rows(path)
    return rows[0] if rows else {}


def scalar(value: Any) -> Any:
    if isinstance(value, dict) and "_provenance" in value:
        return {key: val for key, val in value.items() if key != "_provenance"}
    return value


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in ("", None):
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def git_sha(root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


def parse_worker_runtime_log(path: Path) -> dict[str, Any]:
    prefill_events: list[dict[str, Any]] = []
    decode_events: list[dict[str, Any]] = []
    if not path.exists():
        return {
            "source": str(path),
            "prefill_events": prefill_events,
            "decode_events": decode_events,
            "summary": {
                "prefill_event_count": 0,
                "decode_event_count": 0,
                "prefill_cached_token_total_line_sum": 0,
                "prefill_cached_token_max": 0,
                "prefill_events_with_cached_tokens": 0,
            },
        }

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = clean_log_line(raw_line)
        timestamp_match = TIMESTAMP_RE.search(line)
        timestamp = timestamp_match.group("timestamp") if timestamp_match else None
        parsed_timestamp = parse_timestamp(timestamp)
        prefill_match = PREFILL_RE.search(line)
        if prefill_match:
            groups = prefill_match.groupdict()
            prefill_events.append(
                {
                    "line_number": line_number,
                    "timestamp": timestamp,
                    "_timestamp_sort": parsed_timestamp,
                    "new_seq": as_int(groups["new_seq"]),
                    "new_token": as_int(groups["new_token"]),
                    "cached_token": as_int(groups["cached_token"]),
                    "token_usage": as_float(groups["token_usage"]),
                    "running_req": as_int(groups["running_req"]),
                    "queue_req": as_int(groups["queue_req"]),
                    "input_throughput_tps": as_float(groups["input_throughput_tps"]),
                    "cuda_graph": groups["cuda_graph"] == "True",
                }
            )
            continue
        decode_match = DECODE_RE.search(line)
        if decode_match:
            groups = decode_match.groupdict()
            decode_events.append(
                {
                    "line_number": line_number,
                    "timestamp": timestamp,
                    "_timestamp_sort": parsed_timestamp,
                    "running_req": as_int(groups["running_req"]),
                    "token": as_int(groups["token"]),
                    "token_usage": as_float(groups["token_usage"]),
                    "cuda_graph": groups["cuda_graph"] == "True",
                    "gen_throughput_tps": as_float(groups["gen_throughput_tps"]),
                    "queue_req": as_int(groups["queue_req"]),
                }
            )

    prefill_events.sort(key=lambda event: event["_timestamp_sort"] or datetime.min.replace(tzinfo=timezone.utc))
    decode_events.sort(key=lambda event: event["_timestamp_sort"] or datetime.min.replace(tzinfo=timezone.utc))
    summary = {
        "prefill_event_count": len(prefill_events),
        "decode_event_count": len(decode_events),
        "prefill_new_token_total_line_sum": sum(event["new_token"] for event in prefill_events),
        "prefill_cached_token_total_line_sum": sum(event["cached_token"] for event in prefill_events),
        "prefill_cached_token_max": max((event["cached_token"] for event in prefill_events), default=0),
        "prefill_events_with_cached_tokens": sum(1 for event in prefill_events if event["cached_token"] > 0),
        "decode_token_max": max((event["token"] for event in decode_events), default=0),
        "decode_gen_throughput_tps_max": max((event["gen_throughput_tps"] for event in decode_events), default=0.0),
    }
    for event in prefill_events + decode_events:
        event.pop("_timestamp_sort", None)
    return {
        "source": str(path),
        "prefill_events": prefill_events,
        "decode_events": decode_events,
        "summary": summary,
    }


def transfer_direction_label(direction: str) -> str:
    if direction == "host_to_device":
        return "host->device"
    if direction == "device_to_host":
        return "device->host"
    return direction


def parse_transfer_events(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if TRANSFER_PREFIX in line:
                payload = line.split(TRANSFER_PREFIX, 1)[1].strip()
            else:
                payload = line.strip()
            if not payload:
                continue
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if event.get("event") != "sglang.transfer":
                continue
            event.setdefault("source", str(path))
            event.setdefault("line_number", line_number)
            events.append(event)
    return events


def summarize_transfers(events: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    totals: dict[str, Any] = {
        "event_count": len(events),
        "direction_counts": dict(Counter(str(event.get("direction", "")) for event in events)),
        "function_counts": dict(Counter(str(event.get("function", "")) for event in events)),
        "num_bytes_observed": 0,
        "num_mb_observed": 0.0,
        "kv_num_bytes_estimated": 0,
        "kv_num_mb_estimated": 0.0,
        "kv_num_bytes_estimated_page_granular": 0,
        "kv_num_mb_estimated_page_granular": 0.0,
        "elapsed_ms_wall": 0.0,
        "elapsed_ms_cuda_sync": 0.0,
        "cuda_sync_wait_ms": 0.0,
        "cuda_sync_timing_count": 0,
        "semantic_token_count": 0,
        "unique_semantic_token_hashes": 0,
        "has_host_to_device": False,
        "has_device_to_host": False,
    }
    by_key: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "function": "",
            "direction": "",
            "direction_label": "",
            "count": 0,
            "num_bytes_observed": 0,
            "num_mb_observed": 0.0,
            "kv_num_bytes_estimated": 0,
            "kv_num_mb_estimated": 0.0,
            "kv_num_bytes_estimated_page_granular": 0,
            "kv_num_mb_estimated_page_granular": 0.0,
            "elapsed_ms_wall": 0.0,
            "elapsed_ms_cuda_sync": 0.0,
            "cuda_sync_wait_ms": 0.0,
            "cuda_sync_timing_count": 0,
            "semantic_token_count": 0,
            "error_count": 0,
        }
    )
    token_hashes = set()
    by_direction: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "kv_num_bytes_estimated": 0,
            "kv_num_mb_estimated": 0.0,
            "elapsed_ms_cuda_sync": 0.0,
            "cuda_sync_wait_ms": 0.0,
        }
    )
    for event in events:
        direction = str(event.get("direction", ""))
        function = str(event.get("function", ""))
        key = (function, direction)
        row = by_key[key]
        row["function"] = function
        row["direction"] = direction
        row["direction_label"] = transfer_direction_label(direction)
        row["count"] += 1
        observed_bytes = as_int(event.get("num_bytes_observed"))
        kv_bytes = as_int(event.get("kv_num_bytes_estimated"))
        page_kv_bytes = as_int(event.get("kv_num_bytes_estimated_page_granular"))
        wall_ms = as_float(event.get("elapsed_ms_wall", event.get("elapsed_ms")))
        cuda_ms = as_float(event.get("elapsed_ms_cuda_sync"))
        wait_ms = as_float(event.get("cuda_sync_wait_ms"))
        semantic_count = as_int(event.get("semantic_token_count"))

        row["num_bytes_observed"] += observed_bytes
        row["num_mb_observed"] += observed_bytes / (1024.0 * 1024.0)
        row["kv_num_bytes_estimated"] += kv_bytes
        row["kv_num_mb_estimated"] += kv_bytes / (1024.0 * 1024.0)
        row["kv_num_bytes_estimated_page_granular"] += page_kv_bytes
        row["kv_num_mb_estimated_page_granular"] += page_kv_bytes / (1024.0 * 1024.0)
        row["elapsed_ms_wall"] += wall_ms
        row["semantic_token_count"] += semantic_count
        if event.get("elapsed_ms_cuda_sync") is not None:
            row["elapsed_ms_cuda_sync"] += cuda_ms
            row["cuda_sync_wait_ms"] += wait_ms
            row["cuda_sync_timing_count"] += 1
        if event.get("error"):
            row["error_count"] += 1

        direction_row = by_direction[direction]
        direction_row["count"] += 1
        direction_row["kv_num_bytes_estimated"] += kv_bytes
        direction_row["kv_num_mb_estimated"] += kv_bytes / (1024.0 * 1024.0)
        if event.get("elapsed_ms_cuda_sync") is not None:
            direction_row["elapsed_ms_cuda_sync"] += cuda_ms
            direction_row["cuda_sync_wait_ms"] += wait_ms

        totals["num_bytes_observed"] += observed_bytes
        totals["num_mb_observed"] += observed_bytes / (1024.0 * 1024.0)
        totals["kv_num_bytes_estimated"] += kv_bytes
        totals["kv_num_mb_estimated"] += kv_bytes / (1024.0 * 1024.0)
        totals["kv_num_bytes_estimated_page_granular"] += page_kv_bytes
        totals["kv_num_mb_estimated_page_granular"] += page_kv_bytes / (1024.0 * 1024.0)
        totals["elapsed_ms_wall"] += wall_ms
        totals["semantic_token_count"] += semantic_count
        if event.get("elapsed_ms_cuda_sync") is not None:
            totals["elapsed_ms_cuda_sync"] += cuda_ms
            totals["cuda_sync_wait_ms"] += wait_ms
            totals["cuda_sync_timing_count"] += 1
        if direction == "host_to_device":
            totals["has_host_to_device"] = True
        if direction == "device_to_host":
            totals["has_device_to_host"] = True
        if event.get("semantic_token_ids_sha256"):
            token_hashes.add(str(event["semantic_token_ids_sha256"]))

    totals["unique_semantic_token_hashes"] = len(token_hashes)
    totals["by_direction"] = dict(by_direction)
    rows = sorted(by_key.values(), key=lambda row: (row["direction"], row["function"]))
    return totals, rows


def write_transfer_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "function",
        "direction",
        "direction_label",
        "count",
        "num_bytes_observed",
        "num_mb_observed",
        "kv_num_bytes_estimated",
        "kv_num_mb_estimated",
        "kv_num_bytes_estimated_page_granular",
        "kv_num_mb_estimated_page_granular",
        "elapsed_ms_wall",
        "elapsed_ms_cuda_sync",
        "cuda_sync_wait_ms",
        "cuda_sync_timing_count",
        "semantic_token_count",
        "error_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def event_timestamp(event: dict[str, Any]) -> datetime | None:
    return parse_timestamp(event.get("timestamp"))


def worker_phase_evidence(
    *,
    phase_start: datetime | None,
    worker_runtime: dict[str, Any],
) -> dict[str, Any]:
    if phase_start is None:
        return {}

    prefill_events = worker_runtime.get("prefill_events", [])
    decode_events = worker_runtime.get("decode_events", [])
    first_decode = next(
        (event for event in decode_events if (event_timestamp(event) or datetime.min.replace(tzinfo=timezone.utc)) >= phase_start),
        None,
    )
    first_decode_at = event_timestamp(first_decode or {})
    if first_decode_at is not None:
        prefill_window = [
            event
            for event in prefill_events
            if phase_start <= (event_timestamp(event) or datetime.min.replace(tzinfo=timezone.utc)) <= first_decode_at
        ]
    else:
        prefill_window = [
            event
            for event in prefill_events
            if (event_timestamp(event) or datetime.min.replace(tzinfo=timezone.utc)) >= phase_start
        ]
    first_prefill = prefill_window[0] if prefill_window else None
    first_prefill_at = event_timestamp(first_prefill or {})
    cached_values = [as_int(event.get("cached_token")) for event in prefill_window]
    new_values = [as_int(event.get("new_token")) for event in prefill_window]
    sglang_ttft_ms = ms_between(first_prefill_at, first_decode_at)
    return {
        "sglang_cache_hit": max(cached_values, default=0) > 0,
        "sglang_cached_token_count": max(cached_values, default=0),
        "sglang_cache_source": "worker_runtime.prefill.cached_token" if cached_values else "none",
        "sglang_new_token_count": sum(new_values),
        "sglang_ttft_ms_prefill_to_first_decode": sglang_ttft_ms,
        "sglang_ttft_source": "worker_runtime.prefill_to_first_decode" if sglang_ttft_ms is not None else "none",
        "worker_first_prefill_timestamp": first_prefill.get("timestamp") if first_prefill else None,
        "worker_first_prefill_line_number": first_prefill.get("line_number") if first_prefill else None,
        "worker_first_decode_timestamp": first_decode.get("timestamp") if first_decode else None,
        "worker_first_decode_line_number": first_decode.get("line_number") if first_decode else None,
        "worker_request_to_first_decode_ms": ms_between(phase_start, first_decode_at),
        "worker_first_prefill_to_first_decode_ms": ms_between(first_prefill_at, first_decode_at),
        "worker_prefill_event_count_before_first_decode": len(prefill_window),
        "worker_prefill_cached_token_max_before_first_decode": max(cached_values, default=0),
        "worker_prefill_cached_token_sum_before_first_decode": sum(cached_values),
        "worker_prefill_new_token_sum_before_first_decode": sum(new_values),
    }


def phase_metrics(result_dir: Path, worker_runtime: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    worker_runtime = worker_runtime or {}
    runtime_events = load_json(result_dir / "others/runtime_events.json", [])
    measurements = load_json(result_dir / "others/measurements.json", [])
    measurements_by_request = {
        item.get("request_context", {}).get("request_id"): item for item in measurements
    }
    rows: list[dict[str, Any]] = []
    for event in runtime_events:
        request_id = event.get("request_id")
        measurement = measurements_by_request.get(request_id, {})
        cache = scalar(event.get("cache", {}) or {})
        latency = scalar(event.get("latency", {}) or {})
        scheduler = scalar(event.get("scheduler", {}) or {})
        worker = scalar(event.get("worker_metrics", {}) or {})
        hints = scalar(event.get("request_hints", {}) or {})
        phase_start = parse_timestamp(event.get("timestamp"))
        worker_evidence = worker_phase_evidence(
            phase_start=phase_start,
            worker_runtime=worker_runtime,
        )
        runtime_cache_hit = as_bool(cache.get("cache_hit"))
        runtime_cached_tokens = as_int(cache.get("cached_token_count"))
        runtime_recomputed_tokens = as_int(cache.get("recomputed_prefix_tokens"))
        api_cached_tokens = as_int(measurement.get("cached_prompt_tokens"))
        worker_cached_tokens = as_int(worker_evidence.get("worker_prefill_cached_token_max_before_first_decode"))
        scheduler_cached_blocks = as_int(scheduler.get("cached_blocks"))
        effective_cached_tokens = max(api_cached_tokens, runtime_cached_tokens, worker_cached_tokens)
        prompt_tokens = as_int(measurement.get("prompt_tokens"))
        if prompt_tokens:
            effective_recomputed_tokens = max(prompt_tokens - effective_cached_tokens, 0)
        else:
            effective_recomputed_tokens = runtime_recomputed_tokens
        cache_sources = []
        if api_cached_tokens > 0:
            cache_sources.append("api_usage.cached_prompt_tokens")
        if runtime_cached_tokens > 0 or runtime_cache_hit:
            cache_sources.append("runtime_events.cache")
        if worker_cached_tokens > 0:
            cache_sources.append("worker_runtime.prefill.cached_token")
        if scheduler_cached_blocks > 0:
            cache_sources.append("frontend_scheduler.cached_blocks")
        cache_hit = bool(effective_cached_tokens > 0 or runtime_cache_hit or scheduler_cached_blocks > 0)
        reuse_denominator = effective_cached_tokens + effective_recomputed_tokens
        ttft_ms = latency.get("ttft_ms")
        ttft_source = "runtime_events.latency.ttft_ms" if ttft_ms not in (None, "") else None
        if ttft_ms in (None, "") and worker_evidence.get("worker_request_to_first_decode_ms") is not None:
            ttft_ms = worker_evidence["worker_request_to_first_decode_ms"]
            ttft_source = "worker_runtime.request_to_first_decode"
        rows.append(
            {
                "phase": event.get("phase"),
                "request_id": request_id,
                "phase_source": "agentbench.runtime_events",
                "request_id_source": "agentbench.runtime_events",
                "request_timestamp": event.get("timestamp"),
                "step_index": event.get("step_index"),
                "step_title": event.get("step_title"),
                "hint_source": "agentbench.runtime_events.request_hints",
                "hint_probe_id": hints.get("hint_probe_id"),
                "hint_priority": hints.get("priority"),
                "hint_reuse_likelihood": hints.get("reuse_likelihood"),
                "hint_latency_sensitivity": hints.get("latency_sensitivity"),
                "hint_expected_output_tokens": hints.get("expected_output_tokens"),
                "hint_agent_phase": hints.get("agent_phase"),
                "latency_ms": measurement.get("latency_ms"),
                "latency_ms_source": "agentbench.measurements",
                "ttft_ms": ttft_ms,
                "ttft_source": ttft_source,
                "end_to_end_ms": latency.get("end_to_end_ms"),
                "prefill_ms": latency.get("prefill_ms"),
                "decode_ms": latency.get("decode_ms"),
                "fetch_ms": latency.get("fetch_ms"),
                "recompute_ms": latency.get("recompute_ms"),
                "prompt_tokens": measurement.get("prompt_tokens"),
                "prompt_tokens_source": "agentbench.measurements",
                "completion_tokens": measurement.get("completion_tokens"),
                "completion_tokens_source": "agentbench.measurements",
                "total_tokens": measurement.get("total_tokens"),
                "cached_prompt_tokens": measurement.get("cached_prompt_tokens"),
                "api_cached_prompt_tokens": measurement.get("cached_prompt_tokens"),
                "api_cached_prompt_tokens_source": "agentbench.measurements.usage",
                "input_tokens": measurement.get("input_tokens"),
                "output_tokens": measurement.get("output_tokens"),
                "cache_hit": cache_hit,
                "cache_hit_source": ",".join(cache_sources) if cache_sources else "none",
                "cached_token_count": effective_cached_tokens,
                "reused_prefix_tokens": effective_cached_tokens,
                "recomputed_prefix_tokens": effective_recomputed_tokens,
                "cache_reuse_ratio": effective_cached_tokens / reuse_denominator if reuse_denominator else 0.0,
                "runtime_cache_hit_reported": cache.get("cache_hit"),
                "runtime_cached_token_count_reported": cache.get("cached_token_count"),
                "runtime_reused_prefix_tokens_reported": cache.get("reused_prefix_tokens"),
                "runtime_recomputed_prefix_tokens_reported": cache.get("recomputed_prefix_tokens"),
                "scheduler_cached_blocks": scheduler_cached_blocks,
                "scheduler_tree_size": scheduler.get("tree_size"),
                "scheduler_total_blocks": scheduler.get("total_blocks"),
                "scheduler_source": "agentbench.runtime_events.scheduler",
                "worker_new_token_count": worker.get("new_token_count"),
                "worker_prefill_token_usage": worker.get("prefill_token_usage"),
                "worker_input_throughput_tps": worker.get("input_throughput_tps"),
                "worker_max_gen_throughput_tps": worker.get("max_gen_throughput_tps"),
                "worker_metrics_reported_source": "agentbench.runtime_events.worker_metrics",
                **worker_evidence,
            }
        )
    return rows


def write_phase_csv(path: Path, rows: list[dict[str, Any]], run_level: dict[str, Any]) -> None:
    fields = [
        "run_id",
        "model",
        "app_variant",
        "phase",
        "request_id",
        "phase_source",
        "request_id_source",
        "hint_source",
        "hint_probe_id",
        "hint_priority",
        "hint_reuse_likelihood",
        "hint_latency_sensitivity",
        "hint_expected_output_tokens",
        "latency_ms",
        "latency_ms_source",
        "ttft_ms",
        "ttft_source",
        "end_to_end_ms",
        "prompt_tokens",
        "prompt_tokens_source",
        "completion_tokens",
        "completion_tokens_source",
        "total_tokens",
        "cached_prompt_tokens",
        "api_cached_prompt_tokens",
        "api_cached_prompt_tokens_source",
        "cache_hit",
        "cache_hit_source",
        "cached_token_count",
        "recomputed_prefix_tokens",
        "cache_reuse_ratio",
        "runtime_cache_hit_reported",
        "runtime_cached_token_count_reported",
        "runtime_recomputed_prefix_tokens_reported",
        "scheduler_cached_blocks",
        "scheduler_tree_size",
        "scheduler_total_blocks",
        "scheduler_source",
        "sglang_cache_hit",
        "sglang_cached_token_count",
        "sglang_cache_source",
        "sglang_new_token_count",
        "sglang_ttft_ms_prefill_to_first_decode",
        "sglang_ttft_source",
        "worker_request_to_first_decode_ms",
        "worker_first_prefill_to_first_decode_ms",
        "worker_first_prefill_timestamp",
        "worker_first_decode_timestamp",
        "worker_prefill_cached_token_max_before_first_decode",
        "worker_prefill_cached_token_sum_before_first_decode",
        "worker_prefill_new_token_sum_before_first_decode",
        "worker_metrics_reported_source",
        "transfer_device_to_host_kv_mb",
        "transfer_host_to_device_kv_mb",
        "transfer_cuda_sync_ms",
        "patch_nonempty",
        "git_diff_nonempty",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = {
                "run_id": run_level.get("run_id"),
                "model": run_level.get("model"),
                "app_variant": run_level.get("app_variant"),
                "transfer_device_to_host_kv_mb": run_level.get("transfer_device_to_host_kv_mb"),
                "transfer_host_to_device_kv_mb": run_level.get("transfer_host_to_device_kv_mb"),
                "transfer_cuda_sync_ms": run_level.get("transfer_cuda_sync_ms"),
                "patch_nonempty": run_level.get("patch_nonempty"),
                "git_diff_nonempty": run_level.get("git_diff_nonempty"),
            }
            out.update({field: row.get(field) for field in fields if field not in out})
            writer.writerow(out)


def write_summary_md(path: Path, manifest: dict[str, Any], metrics: dict[str, Any]) -> None:
    def display(value: Any) -> Any:
        return "n/a" if value in (None, "") else value

    transfer = metrics["transfer_totals"]
    outcome = metrics["agent_outcome"]
    phase_rows = metrics["phase_metrics"]
    lines = [
        f"# Run Report: {manifest['run_id']}",
        "",
        f"- Model: `{manifest.get('model')}`",
        f"- App variant: `{manifest.get('app_variant')}`",
        f"- AgentBench result: `{manifest['paths']['agentbench_result_dir']}`",
        f"- SGLang transfer log: `{manifest['paths'].get('sglang_transfer_log')}`",
        "",
        "## Outcome",
        "",
        f"- Patch nonempty: `{outcome['patch_nonempty']}`",
        f"- Git diff nonempty: `{outcome['git_diff_nonempty']}`",
        f"- Workspace patch bytes: `{outcome['workspace_patch_bytes']}`",
        "",
        "## Runtime",
        "",
    ]
    if phase_rows:
        lines.extend(
            [
                "| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |",
                "| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |",
            ]
        )
        for row in phase_rows:
            lines.append(
                "| {phase} | {latency} | {ttft} | {ttft_source} | {prompt} | {output} | {hit} | {cached} | {recomputed} | {ratio:.4f} |".format(
                    phase=row.get("phase", ""),
                    latency=display(row.get("latency_ms")),
                    ttft=display(row.get("ttft_ms")),
                    ttft_source=display(row.get("ttft_source")),
                    prompt=display(row.get("prompt_tokens")),
                    output=display(row.get("output_tokens")),
                    hit=display(row.get("cache_hit")),
                    cached=display(row.get("cached_token_count")),
                    recomputed=display(row.get("recomputed_prefix_tokens")),
                    ratio=as_float(row.get("cache_reuse_ratio")),
                )
            )
    lines.extend(
        [
            "",
            "## Transfers",
            "",
            f"- Events: `{transfer['event_count']}`",
            f"- Device to host present: `{transfer['has_device_to_host']}`",
            f"- Host to device present: `{transfer['has_host_to_device']}`",
            f"- Estimated KV MB: `{transfer['kv_num_mb_estimated']:.3f}`",
            f"- CUDA sync timing ms: `{transfer['elapsed_ms_cuda_sync']:.3f}`",
            f"- Unique semantic token hashes: `{transfer['unique_semantic_token_hashes']}`",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report(root: Path, result_dir: Path, transfer_log: Path | None, out_root: Path, run_id: str | None) -> Path:
    result_dir = result_dir.resolve()
    run_id = run_id or result_dir.name
    out_dir = (out_root / run_id).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    result = load_json(result_dir / "others/result.json", {})
    run_summary = first_row(result_dir / "others/run_summary_table.csv")
    events = parse_transfer_events(transfer_log)
    transfer_totals, transfer_rows = summarize_transfers(events)
    worker_runtime = parse_worker_runtime_log(result_dir / "others/worker_runtime.log")
    phase_rows = phase_metrics(result_dir, worker_runtime)

    transfer_by_direction = transfer_totals.get("by_direction", {})
    device_to_host = transfer_by_direction.get("device_to_host", {})
    host_to_device = transfer_by_direction.get("host_to_device", {})
    workspace_patch = result_dir / "workspace.patch"
    git_diff_stat = result_dir / "others/git_diff_stat.txt"
    git_status = result_dir / "others/git_status.txt"
    patch_bytes = workspace_patch.stat().st_size if workspace_patch.exists() else 0

    manifest = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_commit": git_sha(root),
        "model": result.get("model") or run_summary.get("model"),
        "app_variant": result.get("app_variant"),
        "frontend_url": result.get("frontend_url"),
        "run_started_at": result.get("run_started_at"),
        "task": {
            "instance_id": (result.get("task") or {}).get("instance_id") or run_summary.get("instance_id"),
            "repo": (result.get("task") or {}).get("repo") or run_summary.get("repo"),
            "base_commit": (result.get("task") or {}).get("base_commit"),
        },
        "prompt_evolution_value_char_limit": result.get("prompt_evolution_value_char_limit"),
        "paths": {
            "agentbench_result_dir": str(result_dir),
            "sglang_transfer_log": str(transfer_log.resolve()) if transfer_log else None,
            "report_dir": str(out_dir),
        },
        "environment_snapshot": {
            key: os.environ.get(key)
            for key in [
                "AGENTBENCH_WORKFLOW_MODE",
                "MODEL_NAME",
                "DYN_TOOL_CALL_PARSER",
                "WORKER_EXTRA_ARGS",
                "SGLANG_TRANSFER_LOG",
                "SGLANG_TRANSFER_LOG_SYNC_TIMING",
                "SGLANG_TRANSFER_LOG_VERBOSE",
                "SGLANG_TRANSFER_LOG_TOKEN_PREVIEW",
            ]
            if os.environ.get(key) is not None
        },
    }

    run_level = {
        "run_id": run_id,
        "model": manifest.get("model"),
        "app_variant": manifest.get("app_variant"),
        "transfer_device_to_host_kv_mb": device_to_host.get("kv_num_mb_estimated", 0.0),
        "transfer_host_to_device_kv_mb": host_to_device.get("kv_num_mb_estimated", 0.0),
        "transfer_cuda_sync_ms": transfer_totals.get("elapsed_ms_cuda_sync", 0.0),
        "patch_nonempty": patch_bytes > 0,
        "git_diff_nonempty": git_diff_stat.exists() and bool(git_diff_stat.read_text(encoding="utf-8", errors="replace").strip()),
    }
    metric_sources = {
        "sglang_worker_log": {
            "path": str((result_dir / "others/worker_runtime.log").resolve()),
            "fields": [
                "sglang_cache_hit",
                "sglang_cached_token_count",
                "sglang_new_token_count",
                "sglang_ttft_ms_prefill_to_first_decode",
                "worker_runtime_log",
                "worker_request_to_first_decode_ms",
                "worker_first_prefill_to_first_decode_ms",
            ],
        },
        "sglang_transfer_log": {
            "path": str(transfer_log.resolve()) if transfer_log else None,
            "fields": [
                "transfer_totals",
                "transfer_by_function_direction",
                "transfer_device_to_host_kv_mb",
                "transfer_host_to_device_kv_mb",
                "transfer_cuda_sync_ms",
            ],
        },
        "agentbench_result_metadata": {
            "path": str(result_dir.resolve()),
            "fields": [
                "phase",
                "request_id",
                "request_timestamp",
                "step_index",
                "step_title",
                "request_hints",
                "task",
                "agent_outcome",
                "model",
                "app_variant",
            ],
            "note": (
                "SGLang logs do not currently include AgentBench phase names, hint metadata, task metadata, "
                "or patch outcome. Those fields still come from the AgentBench result directory."
            ),
        },
        "agentbench_api_measurements": {
            "path": str((result_dir / "others/measurements.json").resolve()),
            "fields": [
                "latency_ms",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "api_cached_prompt_tokens",
            ],
            "note": (
                "These are client/API accounting fields. For SGLang-only comparisons, prefer sglang_* cache "
                "and timing fields plus transfer_totals."
            ),
        },
        "runtime_events_reported_fields": {
            "path": str((result_dir / "others/runtime_events.json").resolve()),
            "fields": [
                "runtime_cache_hit_reported",
                "runtime_cached_token_count_reported",
                "runtime_reused_prefix_tokens_reported",
                "runtime_recomputed_prefix_tokens_reported",
                "scheduler_cached_blocks",
                "scheduler_tree_size",
                "scheduler_total_blocks",
                "worker_new_token_count",
                "worker_prefill_token_usage",
                "worker_input_throughput_tps",
                "worker_max_gen_throughput_tps",
            ],
            "note": (
                "These reported fields are preserved for debugging, but they are not the preferred source "
                "for cache hit or TTFT conclusions."
            ),
        },
    }
    metrics = {
        "metric_sources": metric_sources,
        "report_notes": {
            "cache_hit": (
                "cache_hit, cached_token_count, recomputed_prefix_tokens, and cache_reuse_ratio are effective "
                "values derived from the strongest measured evidence available. Raw runtime_events cache fields "
                "are preserved as runtime_*_reported fields on each phase."
            ),
            "sglang_fields": (
                "Fields prefixed with sglang_* are derived directly from SGLang worker logs. Use these when "
                "comparing how upstream hints affect runtime cache behavior without relying on stale AgentBench "
                "runtime cache fields."
            ),
            "ttft_ms": (
                "ttft_ms uses runtime_events.latency.ttft_ms when present. For non-streaming runs where that field "
                "is missing, it is derived from worker logs as frontend request timestamp to first SGLang decode batch "
                "and marked with ttft_source=worker_runtime.request_to_first_decode."
            ),
            "sglang_ttft_ms_prefill_to_first_decode": (
                "sglang_ttft_ms_prefill_to_first_decode is the SGLang-log-only timing from first prefill batch "
                "to first decode batch for the phase window."
            ),
        },
        "agent_outcome": {
            "patch_nonempty": run_level["patch_nonempty"],
            "git_diff_nonempty": run_level["git_diff_nonempty"],
            "workspace_patch_bytes": patch_bytes,
            "git_status": git_status.read_text(encoding="utf-8", errors="replace") if git_status.exists() else "",
            "git_diff_stat": git_diff_stat.read_text(encoding="utf-8", errors="replace") if git_diff_stat.exists() else "",
        },
        "phase_metrics": phase_rows,
        "worker_runtime_log": worker_runtime,
        "transfer_totals": transfer_totals,
        "transfer_by_function_direction": transfer_rows,
    }

    write_json(out_dir / "run_manifest.json", manifest)
    write_json(out_dir / "run_metrics.json", metrics)
    write_phase_csv(out_dir / "run_metrics.csv", phase_rows, run_level)
    write_transfer_csv(out_dir / "transfer_summary.csv", transfer_rows)
    write_summary_md(out_dir / "summary.md", manifest, metrics)

    for rel in [
        "others/run_summary_table.csv",
        "others/measurement_summary_table.csv",
        "others/runtime_events_table.csv",
        "others/cache_value_summary_table.csv",
        "others/kv_hierarchy_summary_table.csv",
    ]:
        source = result_dir / rel
        if source.exists():
            shutil.copy2(source, out_dir / source.name)

    return out_dir


def main() -> int:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agentbench-result-dir",
        type=Path,
        default=None,
        help="AgentBench result directory. Defaults to the latest experiments/raw/agentbench/results/* directory.",
    )
    parser.add_argument(
        "--transfer-log",
        type=Path,
        default=None,
        help="SGLang transfer JSONL. Defaults to latest_sglang_transfer_events.jsonl or latest timestamped log.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=root / "experiments/reports/runs",
        help="Report root directory.",
    )
    parser.add_argument("--run-id", default=None, help="Override the report run id.")
    args = parser.parse_args()

    result_dir = args.agentbench_result_dir or latest_agentbench_result(root)
    transfer_log = args.transfer_log if args.transfer_log else latest_transfer_log(root)
    out_dir = build_report(root, result_dir, transfer_log, args.out_root, args.run_id)
    print(f"report: {out_dir}")
    print(f"manifest: {out_dir / 'run_manifest.json'}")
    print(f"metrics: {out_dir / 'run_metrics.json'}")
    print(f"csv: {out_dir / 'run_metrics.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
