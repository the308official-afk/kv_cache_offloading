#!/usr/bin/env python3
"""Build a compact run-level report from AgentBench and SGLang artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


TRANSFER_PREFIX = "[SGLANG_TRANSFER_JSON] "
RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"
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


def unlink_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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


def parse_runtime_json_payload(line: str) -> dict[str, Any] | None:
    if RUNTIME_JSON_PREFIX not in line:
        return None
    payload = line.split(RUNTIME_JSON_PREFIX, 1)[1].strip()
    json_start = payload.find("{")
    if json_start >= 0:
        payload = payload[json_start:]
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def request_context_from_record(record: dict[str, Any]) -> dict[str, Any]:
    request_context = record.get("request_context")
    if isinstance(request_context, dict):
        return request_context

    runtime_observability = record.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        request_context = runtime_observability.get("request_context")
        if isinstance(request_context, dict):
            return request_context
        nvext = runtime_observability.get("nvext")
        if isinstance(nvext, dict) and isinstance(nvext.get("request_context"), dict):
            return nvext["request_context"]

    nvext = record.get("nvext")
    if isinstance(nvext, dict) and isinstance(nvext.get("request_context"), dict):
        return nvext["request_context"]
    return {}


def record_request_ids(record: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in (
        "request_id",
        "external_request_id",
        "runtime_request_id",
        "runtime_context_id",
        "frontend_request_id",
        "sglang_request_id",
    ):
        value = record.get(key)
        if isinstance(value, str) and value:
            values.add(value)
    request_context = request_context_from_record(record)
    for key in ("request_id", "parent_run_id", "task_instance_id"):
        value = request_context.get(key)
        if isinstance(value, str) and value:
            values.add(value)
    hint_probe_id = record.get("hint_probe_id")
    if isinstance(hint_probe_id, str) and hint_probe_id:
        values.add(hint_probe_id)
    return values


def runtime_records_by_request(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_request: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        for request_id in record_request_ids(record):
            by_request[request_id].append(record)
    return dict(by_request)


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


def is_ms_field(field: str) -> bool:
    if field.endswith("_source") or field.endswith("_evidence"):
        return False
    return field.endswith("_ms") or "_ms_" in field


def rounded_ms_value(value: Any) -> Any:
    if value in (None, ""):
        return value
    try:
        return str(int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
    except (InvalidOperation, TypeError, ValueError):
        return value


def is_cache_reuse_ratio_field(field: str) -> bool:
    return "cache_reuse_ratio" in field


def rounded_cache_reuse_ratio_value(value: Any) -> Any:
    if value in (None, ""):
        return value
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError):
        return value


def report_csv_value(field: str, value: Any) -> Any:
    if is_ms_field(field):
        return rounded_ms_value(value)
    if is_cache_reuse_ratio_field(field):
        return rounded_cache_reuse_ratio_value(value)
    return value


def report_csv_row(fields: list[str], row: dict[str, Any]) -> dict[str, Any]:
    return {field: report_csv_value(field, row.get(field)) for field in fields}


def copy_report_csv(source: Path, destination: Path) -> None:
    try:
        with source.open(newline="") as infile:
            reader = csv.DictReader(infile)
            fields = reader.fieldnames or []
            rows = list(reader)
    except csv.Error:
        shutil.copy2(source, destination)
        return

    if not fields:
        shutil.copy2(source, destination)
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(report_csv_row(fields, row))


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


def limit_text(text: str, limit: int = 3000) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)] + "..."


def compact_text(text: Any, limit: int = 220) -> str:
    normalized = " ".join(str(text or "").split())
    return limit_text(normalized, limit=limit)


def strip_wrapping_quotes(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return text[1:-1].strip()
    return text


def clean_problem_statement_text(text: Any) -> str:
    raw = strip_wrapping_quotes(str(text or ""))
    raw = raw.replace("\\r\\n", "\n").replace("\\n", "\n")
    lines = [line.strip() for line in raw.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if not line:
            continue
        if line.startswith("#"):
            continue
        line = re.sub(r'^\*\*Title:\s*(.+?)\*\*$', r"\1", line, flags=re.IGNORECASE)
        line = re.sub(r"^\*\*Title:\*\*\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^\*\*Description:\*\*\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^\*\*Issue Description\*\*\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^Title:\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^Description:\s*", "", line, flags=re.IGNORECASE)
        cleaned.append(line)
    normalized = " ".join(cleaned)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def summarize_problem_statement(text: Any, limit: int = 180) -> str:
    raw = strip_wrapping_quotes(str(text or ""))
    raw = raw.replace("\\r\\n", "\n").replace("\\n", "\n")
    title_match = re.search(r"##\s*Title:?\s*(.+?)(?:\n##|\Z)", raw, flags=re.IGNORECASE | re.DOTALL)
    if title_match:
        title = " ".join(title_match.group(1).split()).strip()
        if title:
            return limit_text(title, limit=limit)
    inline_bold_title_match = re.search(r"\*\*Title:\s*(.+?)\*\*", raw, flags=re.IGNORECASE | re.DOTALL)
    if inline_bold_title_match:
        title = " ".join(inline_bold_title_match.group(1).split()).strip()
        if title:
            return limit_text(title, limit=limit)
    bold_title_match = re.search(r"\*\*Title:\*\*\s*(.+?)(?:\n|$)", raw, flags=re.IGNORECASE)
    if bold_title_match:
        title = " ".join(bold_title_match.group(1).split()).strip()
        if title:
            return limit_text(title, limit=limit)
    hash_title_match = re.search(r"#\s*title:\s*(.+?)(?:\n|$)", raw, flags=re.IGNORECASE)
    if hash_title_match:
        title = " ".join(hash_title_match.group(1).split()).strip()
        if title:
            return limit_text(title, limit=limit)
    cleaned = clean_problem_statement_text(raw)
    if not cleaned:
        return ""
    sentence_match = re.match(r"(.+?[.!?])(?:\s|$)", cleaned)
    if sentence_match:
        return limit_text(sentence_match.group(1).strip(), limit=limit)
    return limit_text(cleaned, limit=limit)


def run_timestamp_text(run_id: str) -> str:
    text = str(run_id)
    if text.startswith("agentbench-"):
        text = text[len("agentbench-") :]
    parts = text.split("_")
    if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 8 and parts[1].isdigit() and len(parts[1]) == 6:
        timestamp = f"{parts[0]}_{parts[1]}"
        if len(parts) >= 3 and parts[2].isdigit():
            timestamp = f"{timestamp}_{parts[2]}"
        return timestamp
    return text


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


def infer_hint_profile(hints: dict[str, Any]) -> str:
    profile_shapes = {
        "baseline": {
            "priority": 5,
            "reuse_likelihood": 0.9,
            "latency_sensitivity": 0.7,
            "expected_output_tokens": 512,
        },
        "high-reuse": {
            "priority": 5,
            "reuse_likelihood": 1.0,
            "latency_sensitivity": 0.5,
            "expected_output_tokens": 512,
        },
        "low-reuse": {
            "priority": 5,
            "reuse_likelihood": 0.0,
            "latency_sensitivity": 0.5,
            "expected_output_tokens": 512,
        },
        "high-priority": {
            "priority": 10,
            "reuse_likelihood": 0.5,
            "latency_sensitivity": 1.0,
            "expected_output_tokens": 512,
        },
        "low-priority": {
            "priority": 1,
            "reuse_likelihood": 0.5,
            "latency_sensitivity": 0.2,
            "expected_output_tokens": 512,
        },
        "long-output": {
            "priority": 5,
            "reuse_likelihood": 0.8,
            "latency_sensitivity": 0.5,
            "expected_output_tokens": 2048,
        },
        "short-output": {
            "priority": 5,
            "reuse_likelihood": 0.8,
            "latency_sensitivity": 0.5,
            "expected_output_tokens": 128,
        },
    }
    for profile, expected in profile_shapes.items():
        if all(as_float(hints.get(key), default=-1.0) == float(value) for key, value in expected.items()):
            return profile
    return "unknown"


def parse_worker_runtime_log(path: Path) -> dict[str, Any]:
    prefill_events: list[dict[str, Any]] = []
    decode_events: list[dict[str, Any]] = []
    runtime_json_events: list[dict[str, Any]] = []
    if not path.exists():
        return {
            "source": str(path),
            "prefill_events": prefill_events,
            "decode_events": decode_events,
            "runtime_json_events": runtime_json_events,
            "runtime_json_by_request": {},
            "summary": {
                "prefill_event_count": 0,
                "decode_event_count": 0,
                "runtime_json_event_count": 0,
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
        runtime_json = parse_runtime_json_payload(line)
        if runtime_json is not None:
            runtime_json.setdefault("line_number", line_number)
            runtime_json.setdefault("timestamp", timestamp)
            runtime_json["_timestamp_sort"] = parsed_timestamp
            runtime_json_events.append(runtime_json)
            continue
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
    runtime_json_events.sort(key=lambda event: event["_timestamp_sort"] or datetime.min.replace(tzinfo=timezone.utc))
    summary = {
        "prefill_event_count": len(prefill_events),
        "decode_event_count": len(decode_events),
        "runtime_json_event_count": len(runtime_json_events),
        "prefill_new_token_total_line_sum": sum(event["new_token"] for event in prefill_events),
        "prefill_cached_token_total_line_sum": sum(event["cached_token"] for event in prefill_events),
        "prefill_cached_token_max": max((event["cached_token"] for event in prefill_events), default=0),
        "prefill_events_with_cached_tokens": sum(1 for event in prefill_events if event["cached_token"] > 0),
        "decode_token_max": max((event["token"] for event in decode_events), default=0),
        "decode_gen_throughput_tps_max": max((event["gen_throughput_tps"] for event in decode_events), default=0.0),
    }
    for event in prefill_events + decode_events + runtime_json_events:
        event.pop("_timestamp_sort", None)
    return {
        "source": str(path),
        "prefill_events": prefill_events,
        "decode_events": decode_events,
        "runtime_json_events": runtime_json_events,
        "runtime_json_by_request": runtime_records_by_request(runtime_json_events),
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


def transfer_phase_evidence(events: list[dict[str, Any]], request_id: str | None) -> dict[str, Any]:
    if not request_id:
        return {
            "transfer_request_id_matched": False,
            "transfer_event_count_for_request": 0,
        }
    matched = [
        event
        for event in events
        if request_id
        in {
            str(event.get("request_id") or ""),
            str(event.get("external_request_id") or ""),
            str(event.get("runtime_context_id") or ""),
            str(event.get("sglang_request_id") or ""),
            str(event.get("hint_probe_id") or ""),
        }
    ]
    if not matched:
        return {
            "transfer_request_id_matched": False,
            "transfer_event_count_for_request": 0,
        }

    totals, _rows = summarize_transfers(matched)
    by_direction = totals.get("by_direction", {})
    device_to_host = by_direction.get("device_to_host", {})
    host_to_device = by_direction.get("host_to_device", {})
    return {
        "transfer_request_id_matched": True,
        "transfer_event_count_for_request": len(matched),
        "transfer_request_id_source": "sglang_transfer_event.request_id/external_request_id/hint_probe_id",
        "transfer_device_to_host_kv_mb_for_request": device_to_host.get("kv_num_mb_estimated", 0.0),
        "transfer_host_to_device_kv_mb_for_request": host_to_device.get("kv_num_mb_estimated", 0.0),
        "transfer_cuda_sync_ms_for_request": totals.get("elapsed_ms_cuda_sync", 0.0),
        "transfer_has_device_to_host_for_request": totals.get("has_device_to_host", False),
        "transfer_has_host_to_device_for_request": totals.get("has_host_to_device", False),
    }


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
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(report_csv_row(fields, row))


INSTRUMENTATION_OVERHEAD_FIELDS = [
    "run_id",
    "task",
    "hint_profile",
    "hint_provider",
    "phase",
    "request",
    "profile",
    "events",
    "data_mb",
    "transfer_time_ms",
    "logger_overhead_ms",
    "overhead_pct",
    "token_overhead_ms",
    "sync_overhead_ms",
    "json_write_overhead_ms",
    "slowest_overhead_component",
]


def transfer_event_phase(event: dict[str, Any]) -> str:
    request_context = dict_or_empty(event.get("request_context"))
    value = first_nonempty(
        event.get("phase"),
        event.get("agent_phase"),
        request_context.get("phase"),
        "unknown",
    )
    return str(value or "unknown")


def transfer_event_request(event: dict[str, Any]) -> str:
    value = first_nonempty(
        event.get("request_id"),
        event.get("external_request_id"),
        event.get("runtime_context_id"),
        event.get("sglang_request_id"),
        event.get("hint_probe_id"),
        "",
    )
    return compact_text(value, limit=64)


def transfer_event_has_overhead(event: dict[str, Any]) -> bool:
    if as_bool(event.get("instrumentation_overhead_enabled")) is True:
        return True
    return any(key.startswith("overhead_") and key.endswith("_ms") for key in event)


def transfer_event_data_mb(event: dict[str, Any]) -> float:
    kv_mb = as_float(event.get("kv_num_mb_estimated"))
    return kv_mb if kv_mb > 0 else as_float(event.get("num_mb_observed"))


def transfer_event_time_ms(event: dict[str, Any]) -> float:
    if event.get("elapsed_ms_cuda_sync") not in (None, ""):
        return as_float(event.get("elapsed_ms_cuda_sync"))
    return as_float(event.get("elapsed_ms_wall", event.get("elapsed_ms")))


def overhead_component_ms(event: dict[str, Any], component: str) -> float:
    return as_float(event.get(f"overhead_{component}_ms"))


def instrumentation_overhead_rows(
    events: list[dict[str, Any]],
    *,
    manifest: dict[str, Any],
    run_id: str,
) -> list[dict[str, Any]]:
    overhead_events = [event for event in events if transfer_event_has_overhead(event)]
    if not overhead_events:
        return []

    task = dict_or_empty(manifest.get("task"))
    task_label = str(task.get("repo") or manifest.get("repo") or "")
    hint_profile = str(manifest.get("hint_profile") or "")
    hint_provider = str(manifest.get("hint_provider") or "")
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in overhead_events:
        grouped[
            (
                transfer_event_phase(event),
                transfer_event_request(event),
                str(event.get("transfer_log_profile") or "unknown"),
            )
        ].append(event)

    rows: list[dict[str, Any]] = []
    for (phase, request, profile), items in sorted(grouped.items()):
        data_mb = sum(transfer_event_data_mb(event) for event in items)
        transfer_time_ms = sum(transfer_event_time_ms(event) for event in items)
        token_overhead_ms = sum(overhead_component_ms(event, "token") for event in items)
        if token_overhead_ms == 0:
            token_overhead_ms = sum(
                overhead_component_ms(event, "semantic_token_extract")
                + overhead_component_ms(event, "semantic_token_hash")
                + overhead_component_ms(event, "local_token_preview")
                for event in items
            )
        sync_overhead_ms = sum(overhead_component_ms(event, "cuda_sync_timing") for event in items)
        json_write_overhead_ms = sum(overhead_component_ms(event, "json_write") for event in items)
        if json_write_overhead_ms == 0:
            json_write_overhead_ms = sum(
                overhead_component_ms(event, "json_serialize")
                + overhead_component_ms(event, "stderr_print")
                + overhead_component_ms(event, "file_write")
                for event in items
            )
        component_totals = {
            "tokens": token_overhead_ms,
            "sync": sync_overhead_ms,
            "json_write": json_write_overhead_ms,
            "tensor_scan": sum(overhead_component_ms(event, "tensor_scan") for event in items),
            "request_metadata": sum(overhead_component_ms(event, "request_metadata_extract") for event in items),
            "index_summary": sum(overhead_component_ms(event, "index_summary") for event in items),
            "kv_payload": sum(overhead_component_ms(event, "kv_payload_estimate") for event in items),
        }
        logger_overhead_ms = sum(
            as_float(event.get("overhead_total_logger_ms")) for event in items
        )
        if logger_overhead_ms == 0:
            logger_overhead_ms = sum(component_totals.values())
        slowest_component, slowest_value = max(component_totals.items(), key=lambda item: item[1])
        rows.append(
            {
                "run_id": run_id,
                "task": task_label,
                "hint_profile": hint_profile,
                "hint_provider": hint_provider,
                "phase": phase,
                "request": request,
                "profile": profile,
                "events": len(items),
                "data_mb": data_mb,
                "transfer_time_ms": transfer_time_ms,
                "logger_overhead_ms": logger_overhead_ms,
                "overhead_pct": (logger_overhead_ms / transfer_time_ms * 100.0)
                if transfer_time_ms > 0
                else "",
                "token_overhead_ms": token_overhead_ms,
                "sync_overhead_ms": sync_overhead_ms,
                "json_write_overhead_ms": json_write_overhead_ms,
                "slowest_overhead_component": slowest_component if slowest_value > 0 else "",
            }
        )
    return rows


def write_instrumentation_overhead_md(path: Path, rows: list[dict[str, Any]], *, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "| Run | Task | Hint | Phase | Request | Profile | Events | Data MB | Transfer ms | Logger ms | Overhead % | Token ms | Sync ms | JSON/write ms | Slowest |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {run} | {task} | {hint} | {phase} | {request} | {profile} | {events} | {data} | {transfer} | {logger} | {pct} | {token} | {sync} | {json_write} | {slowest} |".format(
                run=row.get("run_id"),
                task=row.get("task"),
                hint=row.get("hint_profile"),
                phase=row.get("phase"),
                request=row.get("request") or "-",
                profile=row.get("profile"),
                events=row.get("events"),
                data=format_metric(row.get("data_mb")),
                transfer=format_metric(row.get("transfer_time_ms"), field="transfer_time_ms"),
                logger=format_metric(row.get("logger_overhead_ms"), field="logger_overhead_ms"),
                pct=format_metric(row.get("overhead_pct")),
                token=format_metric(row.get("token_overhead_ms"), field="token_overhead_ms"),
                sync=format_metric(row.get("sync_overhead_ms"), field="sync_overhead_ms"),
                json_write=format_metric(row.get("json_write_overhead_ms"), field="json_write_overhead_ms"),
                slowest=row.get("slowest_overhead_component") or "-",
            )
        )
    if not rows:
        lines.extend(["", "No instrumentation overhead timing fields were found. Set `SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1` for calibration runs."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def event_timestamp(event: dict[str, Any]) -> datetime | None:
    return parse_timestamp(event.get("timestamp"))


def runtime_json_records_evidence(
    records: list[dict[str, Any]],
    *,
    request_id_source: str,
) -> dict[str, Any]:
    if not records:
        return {}

    records = sorted(records, key=lambda item: event_timestamp(item) or datetime.min.replace(tzinfo=timezone.utc))
    event_types = [str(record.get("event_type") or "") for record in records if record.get("event_type")]
    received = next((record for record in records if str(record.get("event_type", "")).endswith("request_received")), None)
    attached = next((record for record in records if str(record.get("event_type", "")).endswith("request_attached")), None)
    completed = next((record for record in reversed(records) if str(record.get("event_type", "")).endswith("request_completed")), None)

    usage = dict_or_empty(completed.get("completion_usage") if isinstance(completed, dict) else None)
    prompt_details = dict_or_empty(usage.get("prompt_tokens_details"))
    cached_tokens = as_int(prompt_details.get("cached_tokens"))
    prompt_tokens = as_int(usage.get("prompt_tokens"))
    completion_tokens = as_int(usage.get("completion_tokens"))
    received_at = event_timestamp(received or {})
    attached_at = event_timestamp(attached or {})
    completed_at = event_timestamp(completed or {})
    request_context = request_context_from_record(records[0])
    agent_hints = next((record.get("agent_hints") for record in records if isinstance(record.get("agent_hints"), dict)), None)
    hint_probe_id = next((record.get("hint_probe_id") for record in records if record.get("hint_probe_id")), None)
    sglang_request_id = next((record.get("sglang_request_id") for record in records if record.get("sglang_request_id")), None)
    runtime_context_id = next((record.get("runtime_context_id") for record in records if record.get("runtime_context_id")), None)
    external_request_id = next((record.get("external_request_id") for record in records if record.get("external_request_id")), None)

    ttft_ms = ms_between(received_at, attached_at)
    return {
        "worker_runtime_json_matched": True,
        "worker_runtime_json_event_count": len(records),
        "worker_runtime_json_event_types": event_types,
        "worker_runtime_json_request_id_source": request_id_source,
        "worker_runtime_json_external_request_id": external_request_id,
        "worker_runtime_json_runtime_context_id": runtime_context_id,
        "worker_runtime_json_sglang_request_id": sglang_request_id,
        "worker_runtime_json_request_context": request_context,
        "worker_runtime_json_agent_hints": agent_hints,
        "worker_runtime_json_agent_hints_source": next(
            (record.get("agent_hints_source") for record in records if record.get("agent_hints_source")),
            None,
        ),
        "worker_runtime_json_hint_probe_id": hint_probe_id,
        "worker_runtime_json_request_received_timestamp": received.get("timestamp") if received else None,
        "worker_runtime_json_request_attached_timestamp": attached.get("timestamp") if attached else None,
        "worker_runtime_json_request_completed_timestamp": completed.get("timestamp") if completed else None,
        "worker_runtime_json_request_received_to_attached_ms": ttft_ms,
        "worker_runtime_json_request_received_to_completed_ms": ms_between(received_at, completed_at),
        "worker_runtime_json_prompt_tokens": prompt_tokens,
        "worker_runtime_json_completion_tokens": completion_tokens,
        "worker_runtime_json_cached_tokens": cached_tokens,
        "worker_runtime_json_cache_hit": cached_tokens > 0,
    }


def runtime_json_worker_evidence(
    *,
    request_id: str | None,
    worker_runtime: dict[str, Any],
) -> dict[str, Any]:
    if not request_id:
        return {}

    records = worker_runtime.get("runtime_json_by_request", {}).get(request_id, [])
    return runtime_json_records_evidence(
        records,
        request_id_source="worker_runtime_json.external_request_id/request_context",
    )


def runtime_json_subrequest_groups(records: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    fallback_index = 0
    for record in records:
        group_key = (
            record.get("runtime_context_id")
            or record.get("sglang_request_id")
            or f"subrequest-{fallback_index}"
        )
        if group_key == f"subrequest-{fallback_index}":
            fallback_index += 1
        grouped[str(group_key)].append(record)
    return sorted(
        grouped.items(),
        key=lambda item: event_timestamp(item[1][0]) or datetime.min.replace(tzinfo=timezone.utc),
    )


def worker_phase_evidence(
    *,
    request_id: str | None = None,
    phase_start: datetime | None,
    worker_runtime: dict[str, Any],
) -> dict[str, Any]:
    direct_evidence = runtime_json_worker_evidence(
        request_id=request_id,
        worker_runtime=worker_runtime,
    )
    if phase_start is None:
        return direct_evidence

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
    evidence = {
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
    if direct_evidence:
        direct_cached_tokens = as_int(direct_evidence.get("worker_runtime_json_cached_tokens"))
        if direct_cached_tokens > 0:
            evidence["sglang_cache_hit"] = True
            evidence["sglang_cached_token_count"] = direct_cached_tokens
            evidence["sglang_cache_source"] = "worker_runtime_json.completion_usage.cached_tokens"
        if direct_evidence.get("worker_runtime_json_request_received_to_attached_ms") is not None:
            evidence["sglang_ttft_ms_prefill_to_first_decode"] = direct_evidence[
                "worker_runtime_json_request_received_to_attached_ms"
            ]
            evidence["sglang_ttft_source"] = "worker_runtime_json.request_received_to_attached"
        evidence.update(direct_evidence)
    else:
        evidence["worker_runtime_json_matched"] = False
        evidence["worker_runtime_json_event_count"] = 0
        evidence["worker_runtime_json_request_id_source"] = "none"
    return evidence


def phase_metrics(
    result_dir: Path,
    worker_runtime: dict[str, Any] | None = None,
    transfer_events: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    worker_runtime = worker_runtime or {}
    transfer_events = transfer_events or []
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
            request_id=request_id,
            phase_start=phase_start,
            worker_runtime=worker_runtime,
        )
        worker_request_context = dict_or_empty(worker_evidence.get("worker_runtime_json_request_context"))
        worker_agent_hints = dict_or_empty(worker_evidence.get("worker_runtime_json_agent_hints"))
        transfer_match_ids = {
            str(request_id or ""),
            str(worker_evidence.get("worker_runtime_json_external_request_id") or ""),
            str(worker_evidence.get("worker_runtime_json_runtime_context_id") or ""),
            str(worker_evidence.get("worker_runtime_json_sglang_request_id") or ""),
            str(worker_evidence.get("worker_runtime_json_hint_probe_id") or ""),
            str(worker_request_context.get("request_id") or ""),
            str(worker_agent_hints.get("hint_probe_id") or ""),
        }
        per_request_transfer = transfer_evidence_for_ids(transfer_events, transfer_match_ids)
        runtime_cache_hit = as_bool(cache.get("cache_hit"))
        runtime_cached_tokens = as_int(cache.get("cached_token_count"))
        runtime_recomputed_tokens = as_int(cache.get("recomputed_prefix_tokens"))
        api_cached_tokens = as_int(measurement.get("cached_prompt_tokens"))
        worker_prefill_cached_tokens = as_int(worker_evidence.get("worker_prefill_cached_token_max_before_first_decode"))
        direct_worker_cached_tokens = as_int(worker_evidence.get("worker_runtime_json_cached_tokens"))
        worker_cached_tokens = max(worker_prefill_cached_tokens, direct_worker_cached_tokens)
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
        if worker_prefill_cached_tokens > 0:
            cache_sources.append("worker_runtime.prefill.cached_token")
        if direct_worker_cached_tokens > 0:
            cache_sources.append("worker_runtime_json.completion_usage.cached_tokens")
        if scheduler_cached_blocks > 0:
            cache_sources.append("frontend_scheduler.cached_blocks")
        cache_hit = bool(effective_cached_tokens > 0 or runtime_cache_hit or scheduler_cached_blocks > 0)
        reuse_denominator = effective_cached_tokens + effective_recomputed_tokens
        ttft_ms = latency.get("ttft_ms")
        ttft_source = "runtime_events.latency.ttft_ms" if ttft_ms not in (None, "") else None
        if ttft_ms in (None, "") and worker_evidence.get("worker_runtime_json_request_received_to_attached_ms") is not None:
            ttft_ms = worker_evidence["worker_runtime_json_request_received_to_attached_ms"]
            ttft_source = "worker_runtime_json.request_received_to_attached"
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
                "hint_provider": first_nonempty(hints.get("hint_provider"), worker_agent_hints.get("hint_provider")),
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
                **per_request_transfer,
            }
        )
    return rows


def transfer_evidence_for_ids(events: list[dict[str, Any]], match_ids: set[str]) -> dict[str, Any]:
    clean_ids = {value for value in match_ids if value}
    if not clean_ids:
        return {
            "transfer_request_id_matched": False,
            "transfer_event_count_for_request": 0,
        }
    matched = [
        event
        for event in events
        if clean_ids
        & {
            str(event.get("request_id") or ""),
            str(event.get("external_request_id") or ""),
            str(event.get("runtime_context_id") or ""),
            str(event.get("sglang_request_id") or ""),
            str(event.get("hint_probe_id") or ""),
        }
    ]
    if not matched:
        return {
            "transfer_request_id_matched": False,
            "transfer_event_count_for_request": 0,
        }

    totals, _rows = summarize_transfers(matched)
    by_direction = totals.get("by_direction", {})
    device_to_host = by_direction.get("device_to_host", {})
    host_to_device = by_direction.get("host_to_device", {})
    return {
        "transfer_request_id_matched": True,
        "transfer_event_count_for_request": len(matched),
        "transfer_request_id_source": "sglang_transfer_event.request_id/external_request_id/runtime_context_id/sglang_request_id/hint_probe_id",
        "transfer_device_to_host_kv_mb_for_request": device_to_host.get("kv_num_mb_estimated", 0.0),
        "transfer_host_to_device_kv_mb_for_request": host_to_device.get("kv_num_mb_estimated", 0.0),
        "transfer_cuda_sync_ms_for_request": totals.get("elapsed_ms_cuda_sync", 0.0),
        "transfer_has_device_to_host_for_request": totals.get("has_device_to_host", False),
        "transfer_has_host_to_device_for_request": totals.get("has_host_to_device", False),
    }


def transfer_evidence_for_time_window(
    events: list[dict[str, Any]],
    *,
    start: datetime | None,
    end: datetime | None,
) -> dict[str, Any]:
    if start is None or end is None:
        return {
            "transfer_time_window_matched": False,
            "transfer_event_count_for_time_window": 0,
        }
    matched = [
        event
        for event in events
        if start <= (event_timestamp(event) or datetime.min.replace(tzinfo=timezone.utc)) <= end
    ]
    if not matched:
        return {
            "transfer_time_window_matched": False,
            "transfer_event_count_for_time_window": 0,
        }

    totals, _rows = summarize_transfers(matched)
    by_direction = totals.get("by_direction", {})
    device_to_host = by_direction.get("device_to_host", {})
    host_to_device = by_direction.get("host_to_device", {})
    return {
        "transfer_time_window_matched": True,
        "transfer_event_count_for_time_window": len(matched),
        "transfer_time_window_source": "sglang_transfer_event.timestamp within worker_runtime_json subrequest window",
        "transfer_device_to_host_kv_mb_for_time_window": device_to_host.get("kv_num_mb_estimated", 0.0),
        "transfer_host_to_device_kv_mb_for_time_window": host_to_device.get("kv_num_mb_estimated", 0.0),
        "transfer_cuda_sync_ms_for_time_window": totals.get("elapsed_ms_cuda_sync", 0.0),
        "transfer_has_device_to_host_for_time_window": totals.get("has_device_to_host", False),
        "transfer_has_host_to_device_for_time_window": totals.get("has_host_to_device", False),
    }


def subrequest_metrics(
    result_dir: Path,
    worker_runtime: dict[str, Any] | None = None,
    transfer_events: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    worker_runtime = worker_runtime or {}
    transfer_events = transfer_events or []
    runtime_events = load_json(result_dir / "others/runtime_events.json", [])
    rows: list[dict[str, Any]] = []

    for event in runtime_events:
        phase_request_id = event.get("request_id")
        if not phase_request_id:
            continue
        records = worker_runtime.get("runtime_json_by_request", {}).get(phase_request_id, [])
        for subrequest_index, (_group_key, group_records) in enumerate(runtime_json_subrequest_groups(records)):
            evidence = runtime_json_records_evidence(
                group_records,
                request_id_source="worker_runtime_json.runtime_context_id/sglang_request_id",
            )
            if not evidence:
                continue
            hints = dict_or_empty(evidence.get("worker_runtime_json_agent_hints"))
            request_context = dict_or_empty(evidence.get("worker_runtime_json_request_context"))
            prompt_tokens = as_int(evidence.get("worker_runtime_json_prompt_tokens"))
            cached_tokens = as_int(evidence.get("worker_runtime_json_cached_tokens"))
            recomputed_tokens = max(prompt_tokens - cached_tokens, 0) if prompt_tokens else 0
            reuse_denominator = cached_tokens + recomputed_tokens
            match_ids = {
                str(phase_request_id),
                str(evidence.get("worker_runtime_json_external_request_id") or ""),
                str(evidence.get("worker_runtime_json_runtime_context_id") or ""),
                str(evidence.get("worker_runtime_json_sglang_request_id") or ""),
                str(evidence.get("worker_runtime_json_hint_probe_id") or ""),
                str(hints.get("hint_probe_id") or ""),
                str(request_context.get("request_id") or ""),
            }
            transfer_evidence = transfer_evidence_for_ids(transfer_events, match_ids)
            if not transfer_evidence.get("transfer_request_id_matched"):
                transfer_evidence.update(
                    transfer_evidence_for_time_window(
                        transfer_events,
                        start=parse_timestamp(evidence.get("worker_runtime_json_request_received_timestamp")),
                        end=parse_timestamp(evidence.get("worker_runtime_json_request_completed_timestamp")),
                    )
                )
            rows.append(
                {
                    "phase": event.get("phase"),
                    "phase_request_id": phase_request_id,
                    "subrequest_index": subrequest_index,
                    "runtime_context_id": evidence.get("worker_runtime_json_runtime_context_id"),
                    "sglang_request_id": evidence.get("worker_runtime_json_sglang_request_id"),
                    "external_request_id": evidence.get("worker_runtime_json_external_request_id"),
                    "request_received_timestamp": evidence.get("worker_runtime_json_request_received_timestamp"),
                    "request_attached_timestamp": evidence.get("worker_runtime_json_request_attached_timestamp"),
                    "request_completed_timestamp": evidence.get("worker_runtime_json_request_completed_timestamp"),
                    "ttft_ms": evidence.get("worker_runtime_json_request_received_to_attached_ms"),
                    "request_received_to_completed_ms": evidence.get("worker_runtime_json_request_received_to_completed_ms"),
                    "prompt_tokens": evidence.get("worker_runtime_json_prompt_tokens"),
                    "completion_tokens": evidence.get("worker_runtime_json_completion_tokens"),
                    "cached_token_count": cached_tokens,
                    "recomputed_prefix_tokens": recomputed_tokens,
                    "cache_hit": cached_tokens > 0,
                    "cache_reuse_ratio": cached_tokens / reuse_denominator if reuse_denominator else 0.0,
                    "hint_priority": hints.get("priority"),
                    "hint_reuse_likelihood": hints.get("reuse_likelihood"),
                    "hint_latency_sensitivity": hints.get("latency_sensitivity"),
                    "hint_expected_output_tokens": hints.get("expected_output_tokens"),
                    "hint_agent_phase": hints.get("agent_phase"),
                    "hint_profile": hints.get("hint_profile"),
                    "hint_provider": hints.get("hint_provider"),
                    "hint_probe_id": hints.get("hint_probe_id"),
                    **transfer_evidence,
                }
            )
    return rows


def write_subrequest_csv(path: Path, rows: list[dict[str, Any]], run_level: dict[str, Any]) -> None:
    fields = [
        "run_id",
        "model",
        "app_variant",
        "run_hint_profile",
        "run_hint_provider",
        "phase",
        "phase_request_id",
        "subrequest_index",
        "runtime_context_id",
        "sglang_request_id",
        "external_request_id",
        "request_received_timestamp",
        "request_attached_timestamp",
        "request_completed_timestamp",
        "ttft_ms",
        "request_received_to_completed_ms",
        "prompt_tokens",
        "completion_tokens",
        "cached_token_count",
        "recomputed_prefix_tokens",
        "cache_hit",
        "cache_reuse_ratio",
        "hint_priority",
        "hint_reuse_likelihood",
        "hint_latency_sensitivity",
        "hint_expected_output_tokens",
        "hint_agent_phase",
        "hint_profile",
        "hint_provider",
        "hint_probe_id",
        "transfer_request_id_matched",
        "transfer_event_count_for_request",
        "transfer_request_id_source",
        "transfer_device_to_host_kv_mb_for_request",
        "transfer_host_to_device_kv_mb_for_request",
        "transfer_cuda_sync_ms_for_request",
        "transfer_has_device_to_host_for_request",
        "transfer_has_host_to_device_for_request",
        "transfer_time_window_matched",
        "transfer_event_count_for_time_window",
        "transfer_time_window_source",
        "transfer_device_to_host_kv_mb_for_time_window",
        "transfer_host_to_device_kv_mb_for_time_window",
        "transfer_cuda_sync_ms_for_time_window",
        "transfer_has_device_to_host_for_time_window",
        "transfer_has_host_to_device_for_time_window",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            out = {
                "run_id": run_level.get("run_id"),
                "model": run_level.get("model"),
                "app_variant": run_level.get("app_variant"),
                "run_hint_profile": run_level.get("hint_profile"),
                "run_hint_provider": run_level.get("hint_provider"),
            }
            out.update({field: row.get(field) for field in fields if field not in out})
            writer.writerow(report_csv_row(fields, out))


def write_phase_csv(path: Path, rows: list[dict[str, Any]], run_level: dict[str, Any]) -> None:
    fields = [
        "run_id",
        "model",
        "app_variant",
        "hint_profile",
        "hint_provider",
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
        "worker_runtime_json_matched",
        "worker_runtime_json_event_count",
        "worker_runtime_json_event_types",
        "worker_runtime_json_request_id_source",
        "worker_runtime_json_external_request_id",
        "worker_runtime_json_runtime_context_id",
        "worker_runtime_json_sglang_request_id",
        "worker_runtime_json_agent_hints_source",
        "worker_runtime_json_hint_probe_id",
        "worker_runtime_json_request_received_timestamp",
        "worker_runtime_json_request_attached_timestamp",
        "worker_runtime_json_request_completed_timestamp",
        "worker_runtime_json_request_received_to_attached_ms",
        "worker_runtime_json_request_received_to_completed_ms",
        "worker_runtime_json_prompt_tokens",
        "worker_runtime_json_completion_tokens",
        "worker_runtime_json_cached_tokens",
        "worker_runtime_json_cache_hit",
        "worker_metrics_reported_source",
        "transfer_request_id_matched",
        "transfer_event_count_for_request",
        "transfer_request_id_source",
        "transfer_device_to_host_kv_mb_for_request",
        "transfer_host_to_device_kv_mb_for_request",
        "transfer_cuda_sync_ms_for_request",
        "transfer_has_device_to_host_for_request",
        "transfer_has_host_to_device_for_request",
        "transfer_device_to_host_kv_mb",
        "transfer_host_to_device_kv_mb",
        "transfer_cuda_sync_ms",
        "patch_nonempty",
        "git_diff_nonempty",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            out = {
                "run_id": run_level.get("run_id"),
                "model": run_level.get("model"),
                "app_variant": run_level.get("app_variant"),
                "hint_profile": run_level.get("hint_profile"),
                "hint_provider": run_level.get("hint_provider"),
                "transfer_device_to_host_kv_mb": run_level.get("transfer_device_to_host_kv_mb"),
                "transfer_host_to_device_kv_mb": run_level.get("transfer_host_to_device_kv_mb"),
                "transfer_cuda_sync_ms": run_level.get("transfer_cuda_sync_ms"),
                "patch_nonempty": run_level.get("patch_nonempty"),
                "git_diff_nonempty": run_level.get("git_diff_nonempty"),
            }
            out.update({field: row.get(field) for field in fields if field not in out})
            writer.writerow(report_csv_row(fields, out))


def normalize_step_results(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []

    def sort_key(item: tuple[Any, Any]) -> tuple[int, str]:
        key = str(item[0])
        return (as_int(key, 10**9), key)

    return [item for _key, item in sorted(value.items(), key=sort_key) if isinstance(item, dict)]


def load_step_results(result_dir: Path, result: dict[str, Any]) -> list[dict[str, Any]]:
    step_results = load_json(result_dir / "step_results.json", None)
    if step_results is None:
        step_results = result.get("step_results")
    return normalize_step_results(step_results)


def list_from_any(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def tool_progress_from_step(step: dict[str, Any]) -> dict[str, Any]:
    progress = dict_or_empty(step.get("tool_progress"))
    names = list_from_any(progress.get("tool_call_names"))
    unique_names = list_from_any(progress.get("unique_tool_call_names")) or sorted(set(names))
    count = as_int(progress.get("tool_call_count"), len(names))
    if not progress and not names and count == 0:
        return {}
    return {
        "tool_call_count": count,
        "tool_call_names": names,
        "unique_tool_call_names": unique_names,
        "has_read_file": bool(progress.get("has_read_file") or "read_file" in unique_names),
        "has_write_or_edit": bool(
            progress.get("has_write_or_edit") or bool({"write_file", "edit_file"} & set(unique_names))
        ),
        "has_execute": bool(progress.get("has_execute") or "execute" in unique_names),
        "has_edit_plus_validation": bool(
            progress.get("has_edit_plus_validation")
            or (bool({"write_file", "edit_file"} & set(unique_names)) and "execute" in unique_names)
        ),
    }


def model_behavior_tool_summary(result_dir: Path) -> dict[str, Any]:
    behavior = load_json(result_dir / "prompt_evolution_values/07_model_behavior.json", {})
    after = dict_or_empty(behavior.get("after"))
    names = list_from_any(after.get("observed_tool_call_names"))
    count = as_int(after.get("observed_tool_call_count"))
    if names or count:
        return {
            "tool_call_count": count,
            "unique_tool_call_names": names,
            "tool_call_names": names,
            "source": "prompt_evolution_values/07_model_behavior.json",
            "workspace_changed": after.get("workspace_changed"),
            "finish_reason": after.get("finish_reason"),
        }

    alignment = load_json(result_dir / "runtime_alignment_analysis.json", {})
    for row in dict_or_empty(alignment).get("rows", []):
        if not isinstance(row, dict) or row.get("decision_type") != "tool_use":
            continue
        evidence = str(row.get("evidence") or "")
        count_match = re.search(r"tool_call_count=(\d+)", evidence)
        tools_match = re.search(r"tool_calls=([^;]+)", evidence)
        names = list_from_any(tools_match.group(1)) if tools_match else []
        count = as_int(count_match.group(1)) if count_match else len(names)
        if names or count:
            return {
                "tool_call_count": count,
                "unique_tool_call_names": names,
                "tool_call_names": names,
                "source": "runtime_alignment_analysis.json",
            }
    return {
        "tool_call_count": 0,
        "unique_tool_call_names": [],
        "tool_call_names": [],
        "source": "unavailable",
    }


def summarize_step_tools(step_results: list[dict[str, Any]]) -> dict[str, Any]:
    phase_counts: dict[str, int] = Counter()
    phase_tools: dict[str, list[str]] = defaultdict(list)
    phase_tool_counts: dict[str, int] = Counter()
    phase_has_progress: dict[str, bool] = defaultdict(bool)
    total_names: list[str] = []
    total_count = 0
    has_progress = False

    for step in step_results:
        phase = str(step.get("phase") or "unknown")
        phase_counts[phase] += 1
        progress = tool_progress_from_step(step)
        if not progress:
            continue
        has_progress = True
        phase_has_progress[phase] = True
        names = list_from_any(progress.get("tool_call_names"))
        count = as_int(progress.get("tool_call_count"), len(names))
        total_count += count
        total_names.extend(names)
        phase_tool_counts[phase] += count
        phase_tools[phase].extend(names)

    return {
        "has_step_tool_progress": has_progress,
        "total_tool_call_count": total_count,
        "total_tool_call_names": total_names,
        "total_unique_tool_call_names": sorted(set(total_names)),
        "phase_request_counts": dict(phase_counts),
        "phase_tool_counts": dict(phase_tool_counts),
        "phase_tool_names": {phase: names for phase, names in phase_tools.items()},
        "phase_has_progress": dict(phase_has_progress),
    }


def repo_display_name(repo: Any) -> str:
    if not repo:
        return "unknown"
    text = str(repo)
    return text.rsplit("/", 1)[-1] if "/" in text else text


def run_short_id(run_id: str) -> str:
    text = str(run_id)
    if text.startswith("agentbench-"):
        text = text[len("agentbench-") :]
    parts = text.split("_")
    if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 8 and parts[1].isdigit() and len(parts[1]) == 6:
        short = parts[1]
        if len(parts) >= 3 and parts[2].isdigit():
            short = f"{short}_{parts[2]}"
        return short
    return text.rsplit("_", 1)[-1]


def runtime_label(result: dict[str, Any]) -> str:
    source = str(result.get("deepagents_runtime_source") or "")
    if not source:
        return "unknown"
    if source == "python_environment":
        return "python_environment"
    if "/upstream/deepagents/" in source or source.endswith("/upstream/deepagents/libs/deepagents"):
        return "upstream"
    if "site-packages" in source:
        return "python_environment"
    return Path(source).name or source


def display_tools(names: list[str]) -> str:
    unique = sorted({name for name in names if name})
    return ", ".join(unique) if unique else "none"


def display_bytes(num_bytes: Any) -> str:
    value = as_float(num_bytes)
    if value < 1024:
        return f"{int(value)} bytes"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.2f} MB"


def display_bytes_short(num_bytes: Any) -> str:
    value = as_float(num_bytes)
    if value < 1024:
        return f"{int(value)} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.2f} MB"


def compact_model_label(model: Any) -> str:
    text = str(model or "")
    if "Qwen3" in text:
        return "Qwen 3"
    if "Qwen2.5" in text:
        return "Qwen 2.5"
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    return compact_text(text, limit=18) if text else "unknown"


def prompt_evolution_phase_cell(tool_count: Any, tools_used: Any) -> str:
    count = as_int(tool_count)
    tools = str(tools_used or "none").strip()
    if not tools or tools == "none":
        tools = "none"
    return f"{count} - {tools}"


def average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def percentile(values: list[float], pct: float) -> float | None:
    clean = sorted(value for value in values if value is not None)
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    rank = (len(clean) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(clean) - 1)
    weight = rank - lower
    return clean[lower] * (1 - weight) + clean[upper] * weight


def phase_runtime_summaries(phase_rows: list[dict[str, Any]], subrequest_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in phase_rows:
        grouped[str(row.get("phase") or "unknown")].append(row)

    subrequest_counts: dict[str, int] = Counter()
    for row in subrequest_rows:
        subrequest_counts[str(row.get("phase") or "unknown")] += 1

    summaries: dict[str, dict[str, Any]] = {}
    for phase, rows in grouped.items():
        latency_values = [as_float(row.get("latency_ms")) for row in rows if row.get("latency_ms") not in (None, "")]
        ttft_values = [as_float(row.get("ttft_ms")) for row in rows if row.get("ttft_ms") not in (None, "")]
        reuse_values = [
            as_float(row.get("cache_reuse_ratio"))
            for row in rows
            if row.get("cache_reuse_ratio") not in (None, "")
        ]
        summaries[phase] = {
            "phase_request_count": len(rows),
            "worker_subrequest_count": subrequest_counts.get(phase, 0),
            "latency_ms_total": sum(latency_values),
            "latency_ms_avg": average(latency_values),
            "ttft_ms_avg": average(ttft_values),
            "ttft_ms_min": min(ttft_values) if ttft_values else None,
            "prompt_tokens_sum": sum(as_int(row.get("prompt_tokens")) for row in rows),
            "completion_tokens_sum": sum(as_int(row.get("completion_tokens") or row.get("output_tokens")) for row in rows),
            "cache_hit": any(bool(row.get("cache_hit")) for row in rows),
            "cached_token_count_max": max((as_int(row.get("cached_token_count")) for row in rows), default=0),
            "cached_token_count_sum": sum(as_int(row.get("cached_token_count")) for row in rows),
            "cache_reuse_ratio_avg": average(reuse_values),
            "cache_reuse_ratio_max": max(reuse_values) if reuse_values else None,
            "transfer_device_to_host_kv_mb": sum(
                as_float(row.get("transfer_device_to_host_kv_mb_for_request")) for row in rows
            ),
            "transfer_host_to_device_kv_mb": sum(
                as_float(row.get("transfer_host_to_device_kv_mb_for_request")) for row in rows
            ),
            "transfer_cuda_sync_ms": sum(as_float(row.get("transfer_cuda_sync_ms_for_request")) for row in rows),
        }
    for phase, count in subrequest_counts.items():
        summaries.setdefault(phase, {"phase_request_count": 0})["worker_subrequest_count"] = count
    return summaries


def execution_loop_rows(result_dir: Path, result: dict[str, Any]) -> list[dict[str, Any]]:
    trace = load_json(result_dir / "others/execution_loop_trace.json", None)
    if trace is None:
        trace = result.get("execution_loop_trace") or dict_or_empty(result.get("result")).get("execution_loop")
    steps = dict_or_empty(trace).get("steps")
    if isinstance(steps, list):
        return [step for step in steps if isinstance(step, dict)]
    return []


def build_agent_behavior_summary(
    *,
    result_dir: Path,
    result: dict[str, Any],
    manifest: dict[str, Any],
    run_level: dict[str, Any],
    phase_rows: list[dict[str, Any]],
    subrequest_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    step_results = load_step_results(result_dir, result)
    step_summary = summarize_step_tools(step_results)
    behavior_fallback = model_behavior_tool_summary(result_dir)
    use_step_tools = bool(step_summary["has_step_tool_progress"])
    total_tools = (
        as_int(step_summary["total_tool_call_count"])
        if use_step_tools
        else as_int(behavior_fallback.get("tool_call_count"))
    )
    total_tool_names = (
        list_from_any(step_summary["total_tool_call_names"])
        if use_step_tools
        else list_from_any(behavior_fallback.get("tool_call_names"))
    )
    tool_source = "step_results.tool_progress" if use_step_tools else behavior_fallback.get("source")
    phase_runtime = phase_runtime_summaries(phase_rows, subrequest_rows)
    phase_names = sorted(
        set(phase_runtime)
        | set(step_summary["phase_request_counts"])
        | {str(row.get("phase") or "unknown") for row in phase_rows}
    )
    preferred_order = {"planning": 0, "execution": 1, "patch_generation": 2, "review": 3}
    phase_names.sort(key=lambda item: (preferred_order.get(item, 100), item))

    phase_summaries: list[dict[str, Any]] = []
    for phase in phase_names:
        phase_tool_names = list_from_any(step_summary["phase_tool_names"].get(phase, []))
        phase_tool_count = as_int(step_summary["phase_tool_counts"].get(phase))
        phase_source = "step_results.tool_progress" if step_summary["phase_has_progress"].get(phase) else "unavailable"
        runtime = phase_runtime.get(phase, {})
        phase_summaries.append(
            {
                "phase": phase,
                "phase_request_count": step_summary["phase_request_counts"].get(
                    phase, runtime.get("phase_request_count", 0)
                ),
                "worker_subrequest_count": runtime.get("worker_subrequest_count", 0),
                "tool_call_count": phase_tool_count,
                "tools_used": display_tools(phase_tool_names),
                "tool_source": phase_source,
                "has_read_file": "read_file" in set(phase_tool_names),
                "has_write_or_edit": bool({"write_file", "edit_file"} & set(phase_tool_names)),
                "has_execute": "execute" in set(phase_tool_names),
                "has_edit_plus_validation": bool({"write_file", "edit_file"} & set(phase_tool_names))
                and "execute" in set(phase_tool_names),
                **runtime,
            }
        )

    repo_name = repo_display_name(manifest.get("task", {}).get("repo"))
    loop_steps = execution_loop_rows(result_dir, result)
    run_summary = {
        "run_id": manifest["run_id"],
        "run_short": run_short_id(manifest["run_id"]),
        "repo": repo_name,
        "repo_full_name": manifest.get("task", {}).get("repo"),
        "runtime": runtime_label(result),
        "model": manifest.get("model"),
        "app_variant": manifest.get("app_variant"),
        "hint_profile": manifest.get("hint_profile"),
        "hint_provider": manifest.get("hint_provider"),
        "execution_subrequests": step_summary["phase_request_counts"].get("execution", 0),
        "worker_subrequests_total": len(subrequest_rows),
        "tool_call_count": total_tools,
        "tools_used": display_tools(total_tool_names),
        "tool_source": tool_source,
        "execution_tool_call_count": step_summary["phase_tool_counts"].get("execution", 0),
        "execution_tools_used": display_tools(step_summary["phase_tool_names"].get("execution", [])),
        "patch_bytes": run_level.get("workspace_patch_bytes", 0),
        "patch": display_bytes(run_level.get("workspace_patch_bytes", 0)),
        "patch_nonempty": run_level.get("patch_nonempty"),
        "git_diff_nonempty": run_level.get("git_diff_nonempty"),
        "execution_loop_enabled": bool(loop_steps),
        "execution_loop_steps": len(loop_steps),
        "source_note": (
            "Precise per-phase tool counts come from step_results.tool_progress. "
            "Older runs may only have aggregate prompt-evolution evidence."
        ),
    }
    return {
        "run": run_summary,
        "phases": phase_summaries,
        "execution_loop_steps": loop_steps,
    }


def write_agent_behavior_csv(path: Path, summary: dict[str, Any]) -> None:
    run = dict_or_empty(summary.get("run"))
    fields = [
        "run_id",
        "run_short",
        "repo",
        "runtime",
        "model",
        "app_variant",
        "hint_profile",
        "hint_provider",
        "phase",
        "phase_request_count",
        "execution_subrequests",
        "worker_subrequest_count",
        "tool_call_count",
        "tools_used",
        "tool_source",
        "has_read_file",
        "has_write_or_edit",
        "has_execute",
        "has_edit_plus_validation",
        "patch_bytes",
        "patch",
        "patch_nonempty",
        "git_diff_nonempty",
        "latency_ms_total",
        "latency_ms_avg",
        "ttft_ms_avg",
        "ttft_ms_min",
        "prompt_tokens_sum",
        "completion_tokens_sum",
        "cache_hit",
        "cached_token_count_max",
        "cached_token_count_sum",
        "cache_reuse_ratio_avg",
        "cache_reuse_ratio_max",
        "transfer_device_to_host_kv_mb",
        "transfer_host_to_device_kv_mb",
        "transfer_cuda_sync_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for phase in summary.get("phases", []):
            out = {
                "run_id": run.get("run_id"),
                "run_short": run.get("run_short"),
                "repo": run.get("repo"),
                "runtime": run.get("runtime"),
                "model": run.get("model"),
                "app_variant": run.get("app_variant"),
                "hint_profile": run.get("hint_profile"),
                "hint_provider": run.get("hint_provider"),
                "execution_subrequests": (
                    run.get("execution_subrequests") if phase.get("phase") == "execution" else ""
                ),
                "patch_bytes": run.get("patch_bytes"),
                "patch": run.get("patch"),
                "patch_nonempty": run.get("patch_nonempty"),
                "git_diff_nonempty": run.get("git_diff_nonempty"),
            }
            out.update({field: phase.get(field) for field in fields if field not in out})
            writer.writerow(report_csv_row(fields, out))


def write_agent_behavior_md(path: Path, summary: dict[str, Any]) -> None:
    run = dict_or_empty(summary.get("run"))
    phases = summary.get("phases", [])
    lines = [
        f"# Agent Behavior Summary: {run.get('run_id')}",
        "",
        "## Tool Results",
        "",
        "| Run | Repo | Runtime | Execution subrequests | Tool calls | Tools used | Patch |",
        "| --- | --- | --- | ---: | ---: | --- | ---: |",
        "| {run_short} | {repo} | {runtime} | {execution_subrequests} | {tool_call_count} | {tools_used} | {patch} |".format(
            run_short=run.get("run_short"),
            repo=run.get("repo"),
            runtime=run.get("runtime"),
            execution_subrequests=run.get("execution_subrequests"),
            tool_call_count=run.get("tool_call_count"),
            tools_used=run.get("tools_used"),
            patch=run.get("patch"),
        ),
        "",
        "## Phase Results",
        "",
        "| Phase | Requests | Worker subrequests | Tool calls | Tools used | TTFT avg ms | Cache hit | Cached max | H2D KV MB | D2H KV MB |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for phase in phases:
        lines.append(
            "| {phase} | {requests} | {worker_subrequests} | {tool_calls} | {tools} | {ttft} | {cache_hit} | {cached} | {h2d:.3f} | {d2h:.3f} |".format(
                phase=phase.get("phase"),
                requests=phase.get("phase_request_count", 0),
                worker_subrequests=phase.get("worker_subrequest_count", 0),
                tool_calls=phase.get("tool_call_count", 0),
                tools=phase.get("tools_used", "none"),
                ttft=format_metric(phase.get("ttft_ms_avg"), field="ttft_ms_avg"),
                cache_hit=phase.get("cache_hit", False),
                cached=phase.get("cached_token_count_max", 0),
                h2d=as_float(phase.get("transfer_host_to_device_kv_mb")),
                d2h=as_float(phase.get("transfer_device_to_host_kv_mb")),
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Exact tool-call arguments and command strings: `tool_call_details.md`",
            f"- Tool source: `{run.get('tool_source')}`",
            f"- Execution loop steps: `{run.get('execution_loop_steps')}`",
            f"- Patch nonempty: `{run.get('patch_nonempty')}`",
            f"- Git diff nonempty: `{run.get('git_diff_nonempty')}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_display_tools(value: Any) -> list[str]:
    if value in (None, "", "none"):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip() and item.strip() != "none"]


def sort_run_id_key(run_id: str) -> tuple[str, str]:
    text = str(run_id)
    if text.startswith("agentbench-"):
        text = text[len("agentbench-") :]
    return (text, str(run_id))


def iter_run_report_dirs(runs_root: Path) -> list[Path]:
    if not runs_root.exists():
        return []
    run_dirs = [
        path for path in runs_root.iterdir()
        if path.is_dir() and ((path / "phase_summary.json").exists() or (path / "agent_behavior_summary.json").exists())
    ]
    return sorted(run_dirs, key=lambda path: sort_run_id_key(path.name))


def load_phase_summary(report_dir: Path) -> dict[str, Any]:
    return load_json(
        report_dir / "phase_summary.json",
        load_json(report_dir / "agent_behavior_summary.json", {}),
    )


def aggregate_run_tool_summary(report_dir: Path) -> dict[str, Any] | None:
    summary = load_phase_summary(report_dir)
    run = dict_or_empty(summary.get("run"))
    phases_raw = summary.get("phases")
    phases = phases_raw if isinstance(phases_raw, list) else []
    if not run:
        return None

    execution_phase = next(
        (phase for phase in phases if isinstance(phase, dict) and phase.get("phase") == "execution"),
        {},
    )
    planning_phase = next(
        (phase for phase in phases if isinstance(phase, dict) and phase.get("phase") == "planning"),
        {},
    )
    patch_generation_phase = next(
        (phase for phase in phases if isinstance(phase, dict) and phase.get("phase") == "patch_generation"),
        {},
    )
    review_phase = next(
        (phase for phase in phases if isinstance(phase, dict) and phase.get("phase") == "review"),
        {},
    )
    other_phases = [
        phase for phase in phases
        if isinstance(phase, dict) and phase.get("phase") != "execution"
    ]

    def phase_tool_breakdown(phase: dict[str, Any], phase_name: str) -> str:
        tool_names = parse_display_tools(phase.get("tools_used"))
        tool_count = as_int(phase.get("tool_call_count"))
        if tool_count <= 0 or not tool_names:
            return f"{phase_name}: 0 x none"
        if len(tool_names) == 1:
            return f"{phase_name}: {tool_count} x {tool_names[0]}"

        counts = Counter()
        remaining = tool_count
        for tool_name in tool_names:
            counts[tool_name] += 1
            remaining -= 1
        if remaining > 0:
            counts[tool_names[0]] += remaining
        parts = [f"{count} x {tool_name}" for tool_name, count in counts.items()]
        return f"{phase_name}: {', '.join(parts)}"

    other_tool_count = sum(as_int(phase.get("tool_call_count")) for phase in other_phases)
    other_tools: list[str] = []
    for phase in other_phases:
        other_tools.extend(parse_display_tools(phase.get("tools_used")))
    other_tools = sorted(set(other_tools))
    other_phase_breakdowns = [
        phase_tool_breakdown(phase, str(phase.get("phase") or "unknown"))
        for phase in other_phases
        if as_int(phase.get("tool_call_count")) > 0
    ]

    return {
        "run_id": run.get("run_id"),
        "run_short": run.get("run_short"),
        "timestamp": str(run.get("run_id") or "").removeprefix("agentbench-"),
        "repo": run.get("repo"),
        "runtime": run.get("runtime"),
        "model": run.get("model"),
        "hint_profile": run.get("hint_profile"),
        "execution_steps": run.get("execution_subrequests"),
        "planning_tool_calls": as_int(planning_phase.get("tool_call_count")),
        "planning_tools": planning_phase.get("tools_used", "none"),
        "execution_phase_tool_calls": as_int(execution_phase.get("tool_call_count")),
        "execution_phase_tools": execution_phase.get("tools_used", "none"),
        "execution_phase_breakdown": phase_tool_breakdown(execution_phase, "execution"),
        "patch_generation_tool_calls": as_int(patch_generation_phase.get("tool_call_count")),
        "patch_generation_tools": patch_generation_phase.get("tools_used", "none"),
        "review_tool_calls": as_int(review_phase.get("tool_call_count")),
        "review_tools": review_phase.get("tools_used", "none"),
        "other_phase_tool_calls": other_tool_count,
        "other_phase_tools": display_tools(other_tools),
        "other_phase_breakdown": "; ".join(other_phase_breakdowns) if other_phase_breakdowns else "none",
        "total_tool_calls": run.get("tool_call_count"),
        "patch_bytes": run.get("patch_bytes"),
        "patch": run.get("patch"),
        "patch_nonempty": run.get("patch_nonempty"),
        "git_diff_nonempty": run.get("git_diff_nonempty"),
    }


def write_aggregate_tool_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run_id",
        "run_short",
        "timestamp",
        "repo",
        "runtime",
        "model",
        "hint_profile",
        "execution_steps",
        "planning_tool_calls",
        "planning_tools",
        "execution_phase_tool_calls",
        "execution_phase_tools",
        "execution_phase_breakdown",
        "patch_generation_tool_calls",
        "patch_generation_tools",
        "review_tool_calls",
        "review_tools",
        "other_phase_tool_calls",
        "other_phase_tools",
        "other_phase_breakdown",
        "total_tool_calls",
        "patch_bytes",
        "patch",
        "patch_nonempty",
        "git_diff_nonempty",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(report_csv_row(fields, row))


def prompt_evolution_stage_after(report_dir: Path, run: dict[str, Any], file_name: str) -> dict[str, Any]:
    result_dir = resolve_agentbench_result_dir(report_dir, run)
    if not result_dir:
        return {}
    payload = load_json(result_dir / "prompt_evolution_values" / file_name, {})
    return dict_or_empty(payload.get("after"))


def prompt_evolution_phase_column(phase: Any) -> str:
    text = str(phase or "").strip().lower()
    if text.startswith("planning"):
        return "Planning"
    if text.startswith("execution"):
        return "Execution"
    if text.startswith("patch_generation") or text.startswith("patch"):
        return "Patch Gen"
    if text.startswith("review"):
        return "Review"
    return "Other"


def aggregate_prompt_evolution_run_overview_row(
    report_dir: Path,
    fallback: dict[str, Any],
) -> dict[str, Any] | None:
    summary = load_phase_summary(report_dir)
    run = dict_or_empty(summary.get("run"))
    if not run:
        return fallback or None

    final_request = prompt_evolution_stage_after(report_dir, run, "03_final_model_request.json")
    model_behavior = prompt_evolution_stage_after(report_dir, run, "07_model_behavior.json")
    request_context = dict_or_empty(final_request.get("request_context"))

    if not final_request and not model_behavior:
        return fallback

    phase = request_context.get("phase")
    phase_column = prompt_evolution_phase_column(phase)
    tool_names = list_from_any(model_behavior.get("observed_tool_call_names"))
    tool_count = as_int(model_behavior.get("observed_tool_call_count"), len(tool_names))
    phase_cells = {
        "Planning": prompt_evolution_phase_cell(0, "none"),
        "Execution": prompt_evolution_phase_cell(0, "none"),
        "Patch Gen": prompt_evolution_phase_cell(0, "none"),
        "Review": prompt_evolution_phase_cell(0, "none"),
        "Other": prompt_evolution_phase_cell(0, "none"),
    }
    phase_cells[phase_column] = prompt_evolution_phase_cell(tool_count, display_tools(tool_names))

    step_index = request_context.get("step_index")
    steps = as_int(step_index) + 1 if step_index not in (None, "") else fallback.get("execution_steps", "")

    return {
        "run_short": run.get("run_short") or fallback.get("run_short"),
        "repo": run.get("repo") or fallback.get("repo"),
        "model": final_request.get("model") or run.get("model") or fallback.get("model"),
        "execution_steps": steps,
        "planning_cell": phase_cells["Planning"],
        "execution_cell": phase_cells["Execution"],
        "patch_generation_cell": phase_cells["Patch Gen"],
        "review_cell": phase_cells["Review"],
        "other_cell": phase_cells["Other"],
        "total_tool_calls": tool_count,
        "patch_bytes": run.get("patch_bytes", fallback.get("patch_bytes")),
    }


def write_prompt_evolution_run_overview_from_prompt_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "Run",
        "Repo",
        "Model",
        "Steps",
        "Planning",
        "Execution",
        "Patch Gen",
        "Review",
        "Other",
        "Total",
        "Patch",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "Run": row.get("run_short", ""),
                    "Repo": repo_display_name(row.get("repo")),
                    "Model": row.get("model", ""),
                    "Steps": row.get("execution_steps", ""),
                    "Planning": row.get("planning_cell", prompt_evolution_phase_cell(0, "none")),
                    "Execution": row.get("execution_cell", prompt_evolution_phase_cell(0, "none")),
                    "Patch Gen": row.get("patch_generation_cell", prompt_evolution_phase_cell(0, "none")),
                    "Review": row.get("review_cell", prompt_evolution_phase_cell(0, "none")),
                    "Other": row.get("other_cell", prompt_evolution_phase_cell(0, "none")),
                    "Total": row.get("total_tool_calls", ""),
                    "Patch": display_bytes_short(row.get("patch_bytes")),
                }
            )


def write_aggregate_tool_summary_md(path: Path, rows: list[dict[str, Any]], *, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "| Run | Repo | Runtime | Execution steps | Execution-phase tool calls | Execution-phase tools | Other tool calls | Patch |",
        "| --- | --- | --- | ---: | ---: | --- | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {run_short} | {repo} | {runtime} | {execution_steps} | {execution_phase_tool_calls} ({execution_phase_breakdown}) | {execution_phase_tools} | {other_phase_tool_calls} ({other_phase_breakdown}) | {patch} |".format(
                run_short=row.get("run_short", ""),
                repo=row.get("repo", ""),
                runtime=row.get("runtime", ""),
                execution_steps=row.get("execution_steps", ""),
                execution_phase_tool_calls=row.get("execution_phase_tool_calls", 0),
                execution_phase_breakdown=row.get("execution_phase_breakdown", "none"),
                execution_phase_tools=row.get("execution_phase_tools", "none"),
                other_phase_tool_calls=row.get("other_phase_tool_calls", 0),
                other_phase_breakdown=row.get("other_phase_breakdown", "none"),
                patch=row.get("patch", "0 bytes"),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_aggregate_tool_summaries(root: Path, runs_root: Path, *, latest_limit: int = 10) -> None:
    run_dirs = iter_run_report_dirs(runs_root)
    rows: list[dict[str, Any]] = []
    prompt_rows: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        row = aggregate_run_tool_summary(run_dir)
        if not row:
            continue
        rows.append(row)
        prompt_row = aggregate_prompt_evolution_run_overview_row(run_dir, row)
        if prompt_row:
            prompt_rows.append(prompt_row)
    reports_root = root / "experiments/reports"
    reports_root.mkdir(parents=True, exist_ok=True)

    write_aggregate_tool_summary_csv(reports_root / "all_runs_overview.csv", rows)
    write_prompt_evolution_run_overview_from_prompt_csv(
        reports_root / "prompt_evolution_run_overview.csv",
        prompt_rows,
    )
    write_aggregate_tool_summary_md(
        reports_root / "all_runs_overview.md",
        rows,
        title="All Runs Overview",
    )

    latest_rows = rows[-latest_limit:]
    write_aggregate_tool_summary_csv(reports_root / "latest_runs_overview.csv", latest_rows)
    write_aggregate_tool_summary_md(
        reports_root / "latest_runs_overview.md",
        latest_rows,
        title=f"Latest {len(latest_rows)} Runs Overview",
    )
    for legacy_name in (
        "all_runs_tool_summary.csv",
        "all_runs_tool_summary.md",
        "latest_runs_tool_summary.csv",
        "latest_runs_tool_summary.md",
    ):
        unlink_if_exists(reports_root / legacy_name)


def prompt_mentions_validation(prompt: str) -> bool:
    lowered = prompt.lower()
    keywords = ("test", "pytest", "mocha", "validate", "validation", "execute")
    return any(keyword in lowered for keyword in keywords)


def derive_expected_agent_action(
    *,
    problem_statement: str,
    requirements: str,
    selected_tests: list[str],
    validation_command: str,
    patch_expected: bool,
) -> str:
    text = " ".join(
        part for part in [problem_statement, requirements, validation_command, " ".join(selected_tests)] if part
    ).lower()
    has_refactor_signal = bool(
        re.search(r"\b(move|moved|refactor|split|separate|relocate|relocation)\b", text)
    )

    if any(token in text for token in ("route", "router", "endpoint", "controller", "webfinger", ".well-known")):
        base_action = "modify routing/controller logic"
    elif has_refactor_signal:
        base_action = "refactor code organization"
    elif any(token in text for token in ("validation", "invalid", "reject", "accept", "keyword")):
        base_action = "fix validation logic"
    elif any(token in text for token in ("subdomain", "hostname", "domain", "blocking", "blocklist")):
        base_action = "fix host-matching logic"
    else:
        base_action = ""

    if not base_action and patch_expected:
        base_action = "edit repo code"

    if selected_tests or validation_command:
        if base_action:
            return f"{base_action} and run targeted tests"
        return "edit repo code and run validation"
    if base_action:
        return base_action
    return "edit repo code"


def derive_validation_expectation(selected_tests: list[str], validation_command: str) -> str:
    command = str(validation_command or "").strip()
    if command:
        compact_command = compact_text(command, limit=120)
        if selected_tests:
            return f"run targeted tests ({compact_command})"
        return f"run validation command ({compact_command})"
    if selected_tests:
        if len(selected_tests) == 1:
            return "run targeted test file"
        return "run targeted tests"
    return "no explicit validation command provided"


def resolve_agentbench_result_dir(report_dir: Path, run: dict[str, Any]) -> Path | None:
    manifest = load_json(report_dir / "run_manifest.json", {})
    manifest_paths = dict_or_empty(manifest.get("paths"))
    manifest_value = manifest_paths.get("agentbench_result_dir")
    candidates: list[Path] = []
    if manifest_value:
        manifest_path = Path(str(manifest_value))
        candidates.append(manifest_path)
        if not manifest_path.is_absolute():
            candidates.append(repo_root() / manifest_path)
    run_id = str(run.get("run_id") or report_dir.name)
    if run_id:
        candidates.append(repo_root() / "experiments/raw/agentbench/results" / run_id)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def task_info_from_report_dir(report_dir: Path, run: dict[str, Any]) -> dict[str, Any]:
    result_dir = resolve_agentbench_result_dir(report_dir, run)
    result = load_json(result_dir / "others/result.json", {}) if result_dir else {}
    task = dict_or_empty(result.get("task"))
    problem_statement = str(task.get("problem_statement") or "")
    requirements = str(task.get("requirements") or "")
    selected_tests = task.get("selected_test_files_to_run")
    if not isinstance(selected_tests, list):
        selected_tests = []
    validation_command = str(task.get("validation_command") or "")
    patch_expected = bool(task.get("patch"))
    return {
        "task_source": result.get("task_source"),
        "instance_id": task.get("instance_id"),
        "repo": task.get("repo"),
        "base_commit": task.get("base_commit"),
        "problem_statement_summary": summarize_problem_statement(problem_statement),
        "problem_statement_preview": compact_text(clean_problem_statement_text(problem_statement), limit=220),
        "selected_test_count": len(selected_tests),
        "selected_tests_preview": ", ".join(str(item) for item in selected_tests[:3]),
        "patch_expected": patch_expected,
        "expected_agent_action": derive_expected_agent_action(
            problem_statement=clean_problem_statement_text(problem_statement),
            requirements=clean_problem_statement_text(requirements),
            selected_tests=[str(item) for item in selected_tests],
            validation_command=validation_command,
            patch_expected=patch_expected,
        ),
        "validation_expectation": derive_validation_expectation(
            [str(item) for item in selected_tests],
            validation_command,
        ),
    }


def aggregate_execution_prompt_rows(report_dir: Path) -> list[dict[str, Any]]:
    summary = load_phase_summary(report_dir)
    run = dict_or_empty(summary.get("run"))
    if not run:
        return []

    result_dir = resolve_agentbench_result_dir(report_dir, run)
    result = load_json(result_dir / "others/result.json", {}) if result_dir else {}
    phase_results = dict_or_empty(result.get("result")).get("phase_results") or []
    if not isinstance(phase_results, list):
        return []

    rows: list[dict[str, Any]] = []
    for phase_result in phase_results:
        if not isinstance(phase_result, dict):
            continue
        phase_name = str(phase_result.get("phase") or "")
        if not phase_name.startswith("execution"):
            continue
        prompt = str(phase_result.get("prompt") or "")
        progress = tool_progress_from_step(phase_result)
        tool_names = list_from_any(progress.get("tool_call_names"))
        tool_count = as_int(progress.get("tool_call_count"), len(tool_names))
        rows.append(
            {
                "run_id": run.get("run_id"),
                "run_short": run.get("run_short"),
                "repo": run.get("repo"),
                "runtime": run.get("runtime"),
                "model": run.get("model"),
                "hint_profile": run.get("hint_profile"),
                "phase": phase_name,
                "execution_step": phase_result.get("sequence_index"),
                "request_id": dict_or_empty(phase_result.get("request_context")).get("request_id"),
                "parent_run_id": dict_or_empty(phase_result.get("request_context")).get("parent_run_id"),
                "prompt_preview": compact_text(prompt, limit=220),
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest() if prompt else "",
                "prompt_chars": len(prompt),
                "prompt_lines": len(prompt.splitlines()) if prompt else 0,
                "prompt_mentions_validation": prompt_mentions_validation(prompt),
                "tool_call_count": tool_count,
                "tools_called": display_tools(tool_names),
                "patch_bytes": run.get("patch_bytes"),
            }
        )
    return rows


def write_execution_prompt_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run_id",
        "run_short",
        "repo",
        "runtime",
        "model",
        "hint_profile",
        "phase",
        "execution_step",
        "request_id",
        "parent_run_id",
        "prompt_preview",
        "prompt_sha256",
        "prompt_chars",
        "prompt_lines",
        "prompt_mentions_validation",
        "tool_call_count",
        "tools_called",
        "patch_bytes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(report_csv_row(fields, row))


def write_execution_prompt_summary_md(path: Path, rows: list[dict[str, Any]], *, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "| Run | Repo | Step | Prompt preview | Tools called | Patch |",
        "| --- | --- | ---: | --- | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {run_short} | {repo} | {execution_step} | {prompt_preview} | {tool_call_count} ({tools_called}) | {patch_bytes} |".format(
                run_short=row.get("run_short", ""),
                repo=row.get("repo", ""),
                execution_step=row.get("execution_step", ""),
                prompt_preview=row.get("prompt_preview", ""),
                tool_call_count=row.get("tool_call_count", 0),
                tools_called=row.get("tools_called", "none"),
                patch_bytes=row.get("patch_bytes", 0),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_execution_prompt_summaries(root: Path, runs_root: Path, *, latest_limit: int = 10) -> None:
    run_dirs = iter_run_report_dirs(runs_root)
    rows: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        rows.extend(aggregate_execution_prompt_rows(run_dir))

    reports_root = root / "experiments/reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    write_execution_prompt_summary_csv(reports_root / "all_runs_execution_prompts.csv", rows)

    latest_run_ids = {run_dir.name for run_dir in run_dirs[-latest_limit:]}
    latest_rows = [row for row in rows if row.get("run_id") in latest_run_ids]
    write_execution_prompt_summary_md(
        reports_root / "latest_runs_execution_prompts.md",
        latest_rows,
        title=f"Latest {len(latest_run_ids)} Runs Execution Prompts",
    )
    for legacy_name in (
        "all_runs_execution_prompt_summary.csv",
        "latest_runs_execution_prompt_summary.md",
    ):
        unlink_if_exists(reports_root / legacy_name)


def aggregate_task_summary_row(report_dir: Path) -> dict[str, Any] | None:
    summary = load_phase_summary(report_dir)
    run = dict_or_empty(summary.get("run"))
    if not run:
        return None
    task = task_info_from_report_dir(report_dir, run)
    return {
        "run_id": run.get("run_id"),
        "run_short": run.get("run_short"),
        "timestamp": run_timestamp_text(str(run.get("run_id") or report_dir.name)),
        "repo": task.get("repo") or run.get("repo"),
        "instance_id": task.get("instance_id"),
        "task_source": task.get("task_source"),
        "problem_statement_summary": task.get("problem_statement_summary"),
        "problem_statement_preview": task.get("problem_statement_preview"),
        "expected_agent_action": task.get("expected_agent_action"),
        "validation_expectation": task.get("validation_expectation"),
        "base_commit": task.get("base_commit"),
        "patch_expected": task.get("patch_expected"),
        "selected_test_count": task.get("selected_test_count"),
        "selected_tests_preview": task.get("selected_tests_preview"),
        "runtime": run.get("runtime"),
        "model": run.get("model"),
        "hint_profile": run.get("hint_profile"),
        "patch": "Yes" if as_bool(run.get("patch_nonempty")) is True else "No",
        "patch_bytes": run.get("patch_bytes"),
        "base_commit_short": str(task.get("base_commit") or "")[:8],
    }


def write_task_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run_id",
        "run_short",
        "timestamp",
        "repo",
        "instance_id",
        "task_source",
        "problem_statement_summary",
        "problem_statement_preview",
        "expected_agent_action",
        "validation_expectation",
        "base_commit",
        "patch_expected",
        "selected_test_count",
        "selected_tests_preview",
        "runtime",
        "model",
        "hint_profile",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(report_csv_row(fields, row))


def write_prompt_evolution_task_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "Run",
        "Repo",
        "Task Summary",
        "Expected Action",
        "Patch",
        "Base Commit",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "Run": row.get("run_short", ""),
                    "Repo": repo_display_name(row.get("repo")),
                    "Task Summary": row.get("problem_statement_summary", ""),
                    "Expected Action": row.get("expected_agent_action", ""),
                    "Patch": row.get("patch", "No"),
                    "Base Commit": first_nonempty(row.get("base_commit_short"), str(row.get("base_commit") or "")[:8]),
                }
            )


def write_task_summary_md(path: Path, rows: list[dict[str, Any]], *, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "| Run | Repo | Task summary | Expected action | Validation expectation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {run_short} | {repo} | {summary} | {action} | {validation} |".format(
                run_short=row.get("run_short", ""),
                repo=row.get("repo", ""),
                summary=(row.get("problem_statement_summary") or "").replace("|", "\\|"),
                action=(row.get("expected_agent_action") or "").replace("|", "\\|"),
                validation=(row.get("validation_expectation") or "").replace("|", "\\|"),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_task_summaries(root: Path, runs_root: Path, *, latest_limit: int = 10) -> None:
    run_dirs = iter_run_report_dirs(runs_root)
    rows = [aggregate_task_summary_row(run_dir) for run_dir in run_dirs]
    rows = [row for row in rows if row]
    reports_root = root / "experiments/reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    write_task_summary_csv(reports_root / "all_runs_task_summary.csv", rows)
    write_prompt_evolution_task_summary_csv(reports_root / "prompt_evolution_task_summary.csv", rows)
    latest_rows = rows[-latest_limit:]
    write_task_summary_md(
        reports_root / "latest_runs_task_summary.md",
        latest_rows,
        title=f"Latest {len(latest_rows)} Runs Task Summary",
    )


def run_metadata_for_aggregate(report_dir: Path) -> dict[str, Any]:
    manifest = load_json(report_dir / "run_manifest.json", {})
    summary = load_phase_summary(report_dir)
    run = dict_or_empty(summary.get("run"))
    task = dict_or_empty(manifest.get("task"))
    task_label = task.get("repo") or run.get("repo")
    instance_id = task.get("instance_id")
    return {
        "run_id": manifest.get("run_id") or run.get("run_id") or report_dir.name,
        "task_label": task_label,
        "instance_id_short": short_instance_id(instance_id),
        "model": manifest.get("model") or run.get("model"),
        "app_variant": manifest.get("app_variant") or run.get("app_variant"),
        "hint_profile": manifest.get("hint_profile") or run.get("hint_profile"),
        "hint_provider": manifest.get("hint_provider") or run.get("hint_provider") or "agentbench",
        "source_report_dir": str(report_dir),
    }


def short_instance_id(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    match = re.search(r"([0-9a-f]{8,})", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)[:8]
    return compact_text(text, limit=24)


def phase_request_index(value: Any) -> str:
    text = str(value or "")
    match = re.search(r"::(\d+)$", text)
    return match.group(1) if match else ""


def aggregate_report_csv_rows(
    run_dirs: list[Path],
    *,
    file_name: str,
    source_file: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        source = run_dir / file_name
        metadata = run_metadata_for_aggregate(run_dir)
        for row in read_csv_rows(source):
            merged = dict(metadata)
            merged["source_file"] = source_file
            for key, value in row.items():
                if key in {"run_id", "model", "app_variant", "hint_profile", "hint_provider"} and value in ("", None):
                    continue
                merged[key] = value
            if not merged.get("hint_profile") and merged.get("run_hint_profile"):
                merged["hint_profile"] = merged.get("run_hint_profile")
            if not merged.get("hint_provider") and merged.get("run_hint_provider"):
                merged["hint_provider"] = merged.get("run_hint_provider")
            merged["phase_request_index"] = phase_request_index(
                merged.get("phase_request_id") or merged.get("request_id")
            )
            merged["host_to_device_kv_mb"] = first_nonempty(
                merged.get("host_to_device_kv_mb"),
                merged.get("transfer_host_to_device_kv_mb_for_request"),
            )
            merged["device_to_host_kv_mb"] = first_nonempty(
                merged.get("device_to_host_kv_mb"),
                merged.get("transfer_device_to_host_kv_mb_for_request"),
            )
            merged["transfer_cuda_sync_ms"] = first_nonempty(
                merged.get("transfer_cuda_sync_ms_for_request"),
                merged.get("transfer_cuda_sync_ms"),
            )
            merged["ttft_ms"] = nonnegative_metric(merged.get("ttft_ms"))
            rows.append(merged)
    return rows


def write_rows_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(report_csv_row(fields, row))


AGG_PHASE_FIELDS = [
    "run_id",
    "task_label",
    "instance_id_short",
    "hint_profile",
    "hint_provider",
    "phase",
    "phase_request_index",
    "ttft_ms",
    "latency_ms",
    "prompt_tokens",
    "completion_tokens",
    "cache_hit",
    "cached_token_count",
    "recomputed_prefix_tokens",
    "cache_reuse_ratio",
    "worker_runtime_json_matched",
    "transfer_request_id_matched",
    "host_to_device_kv_mb",
    "device_to_host_kv_mb",
    "transfer_cuda_sync_ms",
    "patch_nonempty",
]


AGG_SUBREQUEST_FIELDS = [
    "run_id",
    "task_label",
    "instance_id_short",
    "hint_profile",
    "hint_provider",
    "phase",
    "phase_request_index",
    "subrequest_index",
    "ttft_ms",
    "prompt_tokens",
    "completion_tokens",
    "cache_hit",
    "cached_token_count",
    "recomputed_prefix_tokens",
    "cache_reuse_ratio",
    "transfer_request_id_matched",
    "transfer_time_window_matched",
    "host_to_device_kv_mb",
    "device_to_host_kv_mb",
    "transfer_cuda_sync_ms",
]


REQUEST_PHASE_FIELDS = [
    "run_id",
    "task_label",
    "instance_id_short",
    "hint_profile",
    "hint_provider",
    "phase",
    "phase_request_index",
    "subrequest_index",
    "ttft_ms",
    "cache_hit",
    "cached_token_count",
    "recomputed_prefix_tokens",
    "cache_reuse_ratio",
    "prompt_tokens",
    "completion_tokens",
    "transfer_request_id_matched",
    "transfer_time_window_matched",
    "host_to_device_kv_mb",
    "device_to_host_kv_mb",
    "transfer_cuda_sync_ms",
    "worker_runtime_json_matched",
    "patch_nonempty",
    "source_level",
]


AGG_TRANSFER_FIELDS = [
    "run_id",
    "task_label",
    "instance_id_short",
    "hint_profile",
    "hint_provider",
    "function",
    "direction",
    "count",
    "kv_num_mb_estimated",
    "elapsed_ms_cuda_sync",
    "semantic_token_count",
    "error_count",
]


HINT_IMPACT_FIELDS = [
    "hint_profile",
    "hint_provider",
    "phase",
    "run_count",
    "request_count",
    "worker_runtime_json_match_rate",
    "direct_transfer_attribution_rate",
    "ttft_ms_avg",
    "ttft_ms_p50",
    "ttft_ms_p95",
    "cache_reuse_ratio_avg",
    "cached_token_count_avg",
    "recomputed_prefix_tokens_avg",
    "host_to_device_kv_mb_total",
    "device_to_host_kv_mb_total",
    "transfer_cuda_sync_ms_total",
    "host_to_device_seen_count",
    "device_to_host_seen_count",
]


def bool_rate(rows: list[dict[str, Any]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if as_bool(row.get(field)) is True) / len(rows)


def aggregate_hint_impact_rows(phase_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in phase_rows:
        grouped[
            (
                str(row.get("hint_provider") or "unknown"),
                str(row.get("hint_profile") or "unknown"),
                str(row.get("phase") or "unknown"),
            )
        ].append(row)

    rows: list[dict[str, Any]] = []
    for (hint_provider, hint_profile, phase), items in sorted(grouped.items()):
        ttft_values = [
            as_float(row.get("ttft_ms"))
            for row in items
            if row.get("ttft_ms") not in (None, "") and as_float(row.get("ttft_ms")) >= 0
        ]
        reuse_values = [
            as_float(row.get("cache_reuse_ratio"))
            for row in items
            if row.get("cache_reuse_ratio") not in (None, "")
        ]
        cached_values = [
            as_float(row.get("cached_token_count"))
            for row in items
            if row.get("cached_token_count") not in (None, "")
        ]
        recomputed_values = [
            as_float(row.get("recomputed_prefix_tokens"))
            for row in items
            if row.get("recomputed_prefix_tokens") not in (None, "")
        ]
        h2d_values = [as_float(row.get("transfer_host_to_device_kv_mb_for_request")) for row in items]
        d2h_values = [as_float(row.get("transfer_device_to_host_kv_mb_for_request")) for row in items]
        run_ids = {str(row.get("run_id")) for row in items if row.get("run_id")}
        rows.append(
            {
                "hint_profile": hint_profile,
                "hint_provider": hint_provider,
                "phase": phase,
                "run_count": len(run_ids),
                "request_count": len(items),
                "worker_runtime_json_match_rate": bool_rate(items, "worker_runtime_json_matched"),
                "direct_transfer_attribution_rate": bool_rate(items, "transfer_request_id_matched"),
                "ttft_ms_avg": average(ttft_values),
                "ttft_ms_p50": percentile(ttft_values, 0.50),
                "ttft_ms_p95": percentile(ttft_values, 0.95),
                "cache_reuse_ratio_avg": average(reuse_values),
                "cached_token_count_avg": average(cached_values),
                "recomputed_prefix_tokens_avg": average(recomputed_values),
                "host_to_device_kv_mb_total": sum(h2d_values),
                "device_to_host_kv_mb_total": sum(d2h_values),
                "transfer_cuda_sync_ms_total": sum(
                    as_float(row.get("transfer_cuda_sync_ms_for_request")) for row in items
                ),
                "host_to_device_seen_count": sum(
                    1
                    for row in items
                    if as_bool(row.get("transfer_has_host_to_device_for_request")) is True
                    or as_float(row.get("transfer_host_to_device_kv_mb_for_request")) > 0
                ),
                "device_to_host_seen_count": sum(
                    1
                    for row in items
                    if as_bool(row.get("transfer_has_device_to_host_for_request")) is True
                    or as_float(row.get("transfer_device_to_host_kv_mb_for_request")) > 0
                ),
            }
        )
    return rows


def format_metric(value: Any, digits: int = 3, *, field: str | None = None) -> str:
    if value in (None, ""):
        return "n/a"
    if field and is_ms_field(field):
        rounded = rounded_ms_value(value)
        return str(rounded) if rounded not in (None, "") else "n/a"
    if field and is_cache_reuse_ratio_field(field):
        rounded = rounded_cache_reuse_ratio_value(value)
        return str(rounded) if rounded not in (None, "") else "n/a"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def first_nonempty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def phase_lookup_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("run_id") or ""),
        str(row.get("phase") or ""),
        str(row.get("request_id") or row.get("phase_request_id") or ""),
    )


def nonnegative_metric(value: Any) -> Any:
    if value in (None, ""):
        return None
    numeric = as_float(value)
    return value if numeric >= 0 else None


def aggregate_request_phase_rows(
    phase_rows: list[dict[str, Any]],
    subrequest_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    phase_by_key = {phase_lookup_key(row): row for row in phase_rows}
    subrequest_keys: set[tuple[str, str, str]] = set()
    rows: list[dict[str, Any]] = []

    for sub in subrequest_rows:
        key = phase_lookup_key(sub)
        phase = phase_by_key.get(key, {})
        subrequest_keys.add(key)
        rows.append(
            {
                "run_id": first_nonempty(sub.get("run_id"), phase.get("run_id")),
                "task_label": first_nonempty(sub.get("task_label"), phase.get("task_label")),
                "instance_id_short": first_nonempty(sub.get("instance_id_short"), phase.get("instance_id_short")),
                "model": first_nonempty(sub.get("model"), phase.get("model")),
                "app_variant": first_nonempty(sub.get("app_variant"), phase.get("app_variant")),
                "hint_profile": first_nonempty(
                    sub.get("hint_profile"),
                    sub.get("run_hint_profile"),
                    phase.get("hint_profile"),
                ),
                "hint_provider": first_nonempty(
                    sub.get("hint_provider"),
                    sub.get("run_hint_provider"),
                    phase.get("hint_provider"),
                ),
                "phase": first_nonempty(sub.get("phase"), phase.get("phase")),
                "phase_request_id": first_nonempty(sub.get("phase_request_id"), phase.get("request_id")),
                "phase_request_index": phase_request_index(
                    first_nonempty(sub.get("phase_request_id"), phase.get("request_id"))
                ),
                "subrequest_index": sub.get("subrequest_index"),
                "runtime_context_id": sub.get("runtime_context_id"),
                "sglang_request_id": sub.get("sglang_request_id"),
                "ttft_ms": nonnegative_metric(first_nonempty(sub.get("ttft_ms"), phase.get("ttft_ms"))),
                "ttft_source": phase.get("ttft_source"),
                "cache_hit": first_nonempty(sub.get("cache_hit"), phase.get("cache_hit")),
                "cache_hit_source": phase.get("cache_hit_source"),
                "cached_token_count": first_nonempty(sub.get("cached_token_count"), phase.get("cached_token_count")),
                "recomputed_prefix_tokens": first_nonempty(
                    sub.get("recomputed_prefix_tokens"),
                    phase.get("recomputed_prefix_tokens"),
                ),
                "cache_reuse_ratio": first_nonempty(sub.get("cache_reuse_ratio"), phase.get("cache_reuse_ratio")),
                "prompt_tokens": first_nonempty(sub.get("prompt_tokens"), phase.get("prompt_tokens")),
                "completion_tokens": first_nonempty(sub.get("completion_tokens"), phase.get("completion_tokens")),
                "transfer_request_id_matched": first_nonempty(
                    sub.get("transfer_request_id_matched"),
                    phase.get("transfer_request_id_matched"),
                ),
                "transfer_time_window_matched": sub.get("transfer_time_window_matched"),
                "host_to_device_kv_mb": first_nonempty(
                    sub.get("transfer_host_to_device_kv_mb_for_request"),
                    phase.get("transfer_host_to_device_kv_mb_for_request"),
                ),
                "device_to_host_kv_mb": first_nonempty(
                    sub.get("transfer_device_to_host_kv_mb_for_request"),
                    phase.get("transfer_device_to_host_kv_mb_for_request"),
                ),
                "transfer_cuda_sync_ms": first_nonempty(
                    sub.get("transfer_cuda_sync_ms_for_request"),
                    phase.get("transfer_cuda_sync_ms_for_request"),
                ),
                "worker_runtime_json_matched": phase.get("worker_runtime_json_matched"),
                "patch_nonempty": phase.get("patch_nonempty"),
                "source_level": "model_request",
                "source_report_dir": first_nonempty(sub.get("source_report_dir"), phase.get("source_report_dir")),
            }
        )

    for phase in phase_rows:
        key = phase_lookup_key(phase)
        if key in subrequest_keys:
            continue
        rows.append(
            {
                "run_id": phase.get("run_id"),
                "task_label": phase.get("task_label"),
                "instance_id_short": phase.get("instance_id_short"),
                "model": phase.get("model"),
                "app_variant": phase.get("app_variant"),
                "hint_profile": phase.get("hint_profile"),
                "hint_provider": phase.get("hint_provider"),
                "phase": phase.get("phase"),
                "phase_request_id": phase.get("request_id"),
                "phase_request_index": phase_request_index(phase.get("request_id")),
                "subrequest_index": "",
                "runtime_context_id": phase.get("worker_runtime_json_runtime_context_id"),
                "sglang_request_id": phase.get("worker_runtime_json_sglang_request_id"),
                "ttft_ms": nonnegative_metric(phase.get("ttft_ms")),
                "ttft_source": phase.get("ttft_source"),
                "cache_hit": phase.get("cache_hit"),
                "cache_hit_source": phase.get("cache_hit_source"),
                "cached_token_count": phase.get("cached_token_count"),
                "recomputed_prefix_tokens": phase.get("recomputed_prefix_tokens"),
                "cache_reuse_ratio": phase.get("cache_reuse_ratio"),
                "prompt_tokens": phase.get("prompt_tokens"),
                "completion_tokens": phase.get("completion_tokens"),
                "transfer_request_id_matched": phase.get("transfer_request_id_matched"),
                "transfer_time_window_matched": "",
                "host_to_device_kv_mb": phase.get("transfer_host_to_device_kv_mb_for_request"),
                "device_to_host_kv_mb": phase.get("transfer_device_to_host_kv_mb_for_request"),
                "transfer_cuda_sync_ms": phase.get("transfer_cuda_sync_ms_for_request"),
                "worker_runtime_json_matched": phase.get("worker_runtime_json_matched"),
                "patch_nonempty": phase.get("patch_nonempty"),
                "source_level": "phase_fallback",
                "source_report_dir": phase.get("source_report_dir"),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            str(row.get("run_id") or ""),
            str(row.get("phase") or ""),
            as_int(row.get("subrequest_index"), -1),
            str(row.get("phase_request_id") or ""),
        ),
    )


def write_latest_request_phase_md(path: Path, rows: list[dict[str, Any]], *, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "| Run | Task | Case | Provider | Hint | Phase | Phase req | Model req | TTFT ms | Reuse | Cached | Recomputed | H2D MB | D2H MB | Direct | Worker JSON | Source | Patch |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {run} | {task} | {case} | {provider} | {hint} | {phase} | {phase_request} | {request} | {ttft} | {reuse} | {cached} | {recomputed} | {h2d} | {d2h} | {direct} | {worker} | {source} | {patch} |".format(
                run=row.get("run_id"),
                task=row.get("task_label"),
                case=row.get("instance_id_short"),
                provider=row.get("hint_provider"),
                hint=row.get("hint_profile"),
                phase=row.get("phase"),
                phase_request=row.get("phase_request_index") if row.get("phase_request_index") not in (None, "") else "-",
                request=row.get("subrequest_index") if row.get("subrequest_index") not in (None, "") else "-",
                ttft=format_metric(nonnegative_metric(row.get("ttft_ms")), field="ttft_ms"),
                reuse=format_metric(row.get("cache_reuse_ratio")),
                cached=format_metric(row.get("cached_token_count"), digits=0),
                recomputed=format_metric(row.get("recomputed_prefix_tokens"), digits=0),
                h2d=format_metric(row.get("host_to_device_kv_mb")),
                d2h=format_metric(row.get("device_to_host_kv_mb")),
                direct=row.get("transfer_request_id_matched"),
                worker=row.get("worker_runtime_json_matched"),
                source=row.get("source_level"),
                patch=row.get("patch_nonempty"),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_hint_impact_md(path: Path, rows: list[dict[str, Any]], *, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "| Provider | Hint profile | Phase | Runs | Requests | Direct attribution | Worker JSON | TTFT p50 ms | TTFT p95 ms | Reuse avg | H2D MB | D2H MB |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {provider} | {hint} | {phase} | {runs} | {requests} | {direct} | {worker} | {p50} | {p95} | {reuse} | {h2d} | {d2h} |".format(
                provider=row.get("hint_provider"),
                hint=row.get("hint_profile"),
                phase=row.get("phase"),
                runs=row.get("run_count"),
                requests=row.get("request_count"),
                direct=format_metric(row.get("direct_transfer_attribution_rate")),
                worker=format_metric(row.get("worker_runtime_json_match_rate")),
                p50=format_metric(row.get("ttft_ms_p50"), field="ttft_ms_p50"),
                p95=format_metric(row.get("ttft_ms_p95"), field="ttft_ms_p95"),
                reuse=format_metric(row.get("cache_reuse_ratio_avg")),
                h2d=format_metric(row.get("host_to_device_kv_mb_total")),
                d2h=format_metric(row.get("device_to_host_kv_mb_total")),
            )
        )
    low_direct = [
        row for row in rows
        if as_float(row.get("direct_transfer_attribution_rate")) < 1.0
        and as_int(row.get("request_count")) > 0
    ]
    if low_direct:
        lines.extend(
            [
                "",
                "## Attribution Note",
                "",
                "Some rows have direct transfer attribution below `1.0`. Treat transfer causality carefully for those rows.",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latest_phase_md(path: Path, rows: list[dict[str, Any]], *, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "| Run | Task | Case | Provider | Hint | Phase | Phase req | TTFT ms | Cache reuse | Cached tokens | Direct transfer | H2D MB | D2H MB |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {run} | {task} | {case} | {provider} | {hint} | {phase} | {phase_request} | {ttft} | {reuse} | {cached} | {direct} | {h2d} | {d2h} |".format(
                run=row.get("run_id"),
                task=row.get("task_label"),
                case=row.get("instance_id_short"),
                provider=row.get("hint_provider"),
                hint=row.get("hint_profile"),
                phase=row.get("phase"),
                phase_request=row.get("phase_request_index") if row.get("phase_request_index") not in (None, "") else "-",
                ttft=format_metric(nonnegative_metric(row.get("ttft_ms")), field="ttft_ms"),
                reuse=format_metric(row.get("cache_reuse_ratio")),
                cached=format_metric(row.get("cached_token_count"), digits=0),
                direct=row.get("transfer_request_id_matched"),
                h2d=format_metric(row.get("transfer_host_to_device_kv_mb_for_request")),
                d2h=format_metric(row.get("transfer_device_to_host_kv_mb_for_request")),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latest_subrequest_md(path: Path, rows: list[dict[str, Any]], *, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "| Run | Task | Case | Provider | Hint | Phase | Phase req | Model req | TTFT ms | Cache reuse | Direct transfer | Time-window transfer | H2D MB | D2H MB |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {run} | {task} | {case} | {provider} | {hint} | {phase} | {phase_request} | {index} | {ttft} | {reuse} | {direct} | {window} | {h2d} | {d2h} |".format(
                run=row.get("run_id"),
                task=row.get("task_label"),
                case=row.get("instance_id_short"),
                provider=row.get("hint_provider") or row.get("run_hint_provider"),
                hint=row.get("hint_profile") or row.get("run_hint_profile"),
                phase=row.get("phase"),
                phase_request=row.get("phase_request_index") if row.get("phase_request_index") not in (None, "") else "-",
                index=row.get("subrequest_index"),
                ttft=format_metric(nonnegative_metric(row.get("ttft_ms")), field="ttft_ms"),
                reuse=format_metric(row.get("cache_reuse_ratio")),
                direct=row.get("transfer_request_id_matched"),
                window=row.get("transfer_time_window_matched"),
                h2d=format_metric(row.get("transfer_host_to_device_kv_mb_for_request")),
                d2h=format_metric(row.get("transfer_device_to_host_kv_mb_for_request")),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latest_transfer_md(path: Path, rows: list[dict[str, Any]], *, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "| Run | Task | Case | Hint | Function | Direction | Count | KV MB | CUDA sync ms | Semantic tokens |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {run} | {task} | {case} | {hint} | {function} | {direction} | {count} | {kv_mb} | {cuda_ms} | {tokens} |".format(
                run=row.get("run_id"),
                task=row.get("task_label"),
                case=row.get("instance_id_short"),
                hint=row.get("hint_profile"),
                function=row.get("function"),
                direction=row.get("direction"),
                count=row.get("count"),
                kv_mb=format_metric(row.get("kv_num_mb_estimated")),
                cuda_ms=format_metric(row.get("elapsed_ms_cuda_sync"), field="elapsed_ms_cuda_sync"),
                tokens=format_metric(row.get("semantic_token_count"), digits=0),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_runtime_metric_summaries(root: Path, runs_root: Path, *, latest_limit: int = 10) -> None:
    run_dirs = iter_run_report_dirs(runs_root)
    reports_root = root / "experiments/reports"
    reports_root.mkdir(parents=True, exist_ok=True)

    phase_rows = aggregate_report_csv_rows(
        run_dirs,
        file_name="phase_runtime_metrics.csv",
        source_file="phase_runtime_metrics.csv",
    )
    subrequest_rows = aggregate_report_csv_rows(
        run_dirs,
        file_name="model_request_metrics.csv",
        source_file="model_request_metrics.csv",
    )
    transfer_rows = aggregate_report_csv_rows(
        run_dirs,
        file_name="transfer_events_by_function.csv",
        source_file="transfer_events_by_function.csv",
    )
    overhead_rows = aggregate_report_csv_rows(
        run_dirs,
        file_name="instrumentation_overhead_metrics.csv",
        source_file="instrumentation_overhead_metrics.csv",
    )
    request_phase_rows = aggregate_request_phase_rows(phase_rows, subrequest_rows)
    hint_rows = aggregate_hint_impact_rows(phase_rows)

    write_rows_csv(reports_root / "all_runs_phase_metrics.csv", phase_rows, AGG_PHASE_FIELDS)
    write_rows_csv(reports_root / "all_runs_phase_request_metrics.csv", subrequest_rows, AGG_SUBREQUEST_FIELDS)
    write_rows_csv(reports_root / "all_runs_task_phase_request_metrics.csv", request_phase_rows, REQUEST_PHASE_FIELDS)
    write_rows_csv(reports_root / "all_runs_kv_transfer_metrics.csv", transfer_rows, AGG_TRANSFER_FIELDS)
    write_rows_csv(reports_root / "all_runs_hint_profile_impact.csv", hint_rows, HINT_IMPACT_FIELDS)
    write_rows_csv(
        reports_root / "all_runs_instrumentation_overhead.csv",
        overhead_rows,
        INSTRUMENTATION_OVERHEAD_FIELDS,
    )
    write_hint_impact_md(
        reports_root / "all_runs_hint_profile_impact.md",
        hint_rows,
        title="All Runs Hint Impact Summary",
    )

    latest_run_ids = {run_dir.name for run_dir in run_dirs[-latest_limit:]}
    latest_phase_rows = [row for row in phase_rows if row.get("run_id") in latest_run_ids]
    latest_subrequest_rows = [row for row in subrequest_rows if row.get("run_id") in latest_run_ids]
    latest_request_phase_rows = [row for row in request_phase_rows if row.get("run_id") in latest_run_ids]
    latest_transfer_rows = [row for row in transfer_rows if row.get("run_id") in latest_run_ids]
    latest_overhead_rows = [row for row in overhead_rows if row.get("run_id") in latest_run_ids]
    latest_hint_rows = aggregate_hint_impact_rows(latest_phase_rows)

    write_latest_phase_md(
        reports_root / "latest_runs_phase_metrics.md",
        latest_phase_rows,
        title=f"Latest {len(latest_run_ids)} Runs Phase Metrics",
    )
    write_latest_subrequest_md(
        reports_root / "latest_runs_phase_request_metrics.md",
        latest_subrequest_rows,
        title=f"Latest {len(latest_run_ids)} Runs Model Request Metrics",
    )
    write_latest_request_phase_md(
        reports_root / "latest_runs_task_phase_request_metrics.md",
        latest_request_phase_rows,
        title=f"Latest {len(latest_run_ids)} Runs Request/Phase Metrics",
    )
    write_latest_transfer_md(
        reports_root / "latest_runs_kv_transfer_metrics.md",
        latest_transfer_rows,
        title=f"Latest {len(latest_run_ids)} Runs Transfer Metrics",
    )
    write_hint_impact_md(
        reports_root / "latest_runs_hint_profile_impact.md",
        latest_hint_rows,
        title=f"Latest {len(latest_run_ids)} Runs Hint Impact Summary",
    )
    write_instrumentation_overhead_md(
        reports_root / "latest_runs_instrumentation_overhead.md",
        latest_overhead_rows,
        title=f"Latest {len(latest_run_ids)} Runs Instrumentation Overhead",
    )


def detail_args(detail: dict[str, Any]) -> dict[str, Any]:
    args = detail.get("args")
    return args if isinstance(args, dict) else {}


def detail_command(detail: dict[str, Any]) -> str | None:
    args = detail_args(detail)
    value = detail.get("command") or detail.get("cmd") or args.get("command") or args.get("cmd")
    return str(value) if value not in (None, "") else None


def detail_path(detail: dict[str, Any]) -> str | None:
    args = detail_args(detail)
    for key in ("file_path", "path", "target_file", "filename"):
        value = detail.get(key) or args.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def normalize_tool_detail(
    detail: dict[str, Any],
    *,
    run_id: str,
    phase: str,
    step_index: Any,
    loop_step_type: Any = None,
    source: str,
) -> dict[str, Any]:
    args = detail.get("args")
    if isinstance(args, str):
        try:
            parsed_args = json.loads(args)
            args = parsed_args if isinstance(parsed_args, dict) else {"raw": detail.get("args")}
        except json.JSONDecodeError:
            args = {"raw": detail.get("args")}
    elif not isinstance(args, dict):
        args = {}
    normalized = {
        "run_id": run_id,
        "phase": phase,
        "step_index": step_index,
        "loop_step_type": loop_step_type,
        "tool_call_index": detail.get("tool_call_index"),
        "tool_call_id": detail.get("tool_call_id"),
        "tool_name": detail.get("tool_name") or detail.get("name"),
        "command": detail_command({**detail, "args": args}),
        "file_path": detail_path({**detail, "args": args}),
        "args": args,
        "args_json": json.dumps(args, sort_keys=True, default=str),
        "result_preview": limit_text(str(detail.get("result_preview") or ""), 1000),
        "source": detail.get("source") or source,
    }
    return normalized


def tool_result_previews_from_messages(messages: list[dict[str, Any]]) -> dict[str, str]:
    previews: dict[str, str] = {}
    for message in messages:
        if not isinstance(message, dict) or message.get("type") != "tool":
            continue
        call_id = message.get("tool_call_id")
        if call_id:
            previews[str(call_id)] = limit_text(str(message.get("text") or message.get("content") or ""), 1000)
    return previews


def tool_details_from_messages(
    messages: list[dict[str, Any]],
    *,
    run_id: str,
    phase: str,
    step_index: Any,
    source: str,
) -> list[dict[str, Any]]:
    previews = tool_result_previews_from_messages(messages)
    rows: list[dict[str, Any]] = []
    for message_index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            args = call.get("args")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": call.get("args")}
            detail = {
                "message_index": message_index,
                "tool_call_index": len(rows),
                "tool_call_id": call.get("id"),
                "tool_name": call.get("name"),
                "args": args if isinstance(args, dict) else {},
                "result_preview": previews.get(str(call.get("id") or ""), ""),
            }
            rows.append(
                normalize_tool_detail(
                    detail,
                    run_id=run_id,
                    phase=phase,
                    step_index=step_index,
                    source=source,
                )
            )
    return rows


def collect_agent_tool_calls(result_dir: Path, result: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    def add_row(row: dict[str, Any]) -> None:
        key = (
            row.get("phase"),
            row.get("step_index"),
            row.get("tool_call_id"),
            row.get("tool_name"),
            row.get("command"),
            row.get("file_path"),
            row.get("args_json"),
        )
        if key in seen:
            return
        seen.add(key)
        rows.append(row)

    for step in load_step_results(result_dir, result):
        phase = str(step.get("phase") or "unknown")
        step_index = step.get("sequence_index")
        loop_step_type = dict_or_empty(step.get("execution_loop")).get("step_type")
        for detail in step.get("tool_call_details") or []:
            if isinstance(detail, dict):
                add_row(
                    normalize_tool_detail(
                        detail,
                        run_id=run_id,
                        phase=phase,
                        step_index=step_index,
                        loop_step_type=loop_step_type,
                        source="step_results.tool_call_details",
                    )
                )

    for phase_result in dict_or_empty(result.get("result")).get("phase_results") or []:
        if not isinstance(phase_result, dict):
            continue
        phase = str(phase_result.get("phase") or "unknown")
        step_index = phase_result.get("sequence_index")
        loop_step_type = dict_or_empty(phase_result.get("execution_loop")).get("step_type")
        for detail in phase_result.get("tool_call_details") or []:
            if isinstance(detail, dict):
                add_row(
                    normalize_tool_detail(
                        detail,
                        run_id=run_id,
                        phase=phase,
                        step_index=step_index,
                        loop_step_type=loop_step_type,
                        source="result.phase_results.tool_call_details",
                    )
                )

    result_response = dict_or_empty(dict_or_empty(result.get("result")).get("response"))
    messages = result_response.get("messages")
    if isinstance(messages, list):
        for row in tool_details_from_messages(
            messages,
            run_id=run_id,
            phase=str(dict_or_empty(result.get("result")).get("phase") or "unknown"),
            step_index=dict_or_empty(result.get("result")).get("sequence_index"),
            source="others/result.json.result.response.messages",
        ):
            add_row(row)

    behavior = load_json(result_dir / "prompt_evolution_values/07_model_behavior.json", {})
    behavior_messages = dict_or_empty(behavior.get("after")).get("messages")
    if isinstance(behavior_messages, list):
        for row in tool_details_from_messages(
            behavior_messages,
            run_id=run_id,
            phase="execution",
            step_index=0,
            source="prompt_evolution_values/07_model_behavior.json",
        ):
            add_row(row)

    return rows


def write_agent_tool_calls_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run_id",
        "phase",
        "step_index",
        "loop_step_type",
        "tool_call_index",
        "tool_call_id",
        "tool_name",
        "command",
        "file_path",
        "args_json",
        "result_preview",
        "source",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(report_csv_row(fields, row))


def write_agent_tool_calls_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Agent Tool Calls",
        "",
        "| Phase | Step | Tool | Command | File path | Result preview |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| n/a | n/a | none | n/a | n/a | No exact tool-call details available for this run. |")
    for row in rows:
        command = row.get("command") or ""
        file_path = row.get("file_path") or ""
        preview = (row.get("result_preview") or "").replace("\n", " ")
        lines.append(
            "| {phase} | {step} | {tool} | {command} | {file_path} | {preview} |".format(
                phase=row.get("phase") or "",
                step=row.get("step_index") if row.get("step_index") not in (None, "") else "",
                tool=row.get("tool_name") or "",
                command=command.replace("|", "\\|"),
                file_path=file_path.replace("|", "\\|"),
                preview=limit_text(preview, 180).replace("|", "\\|"),
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary_md(path: Path, manifest: dict[str, Any], metrics: dict[str, Any]) -> None:
    def display(value: Any) -> Any:
        return "n/a" if value in (None, "") else value

    def display_field(field: str, value: Any) -> Any:
        if value in (None, ""):
            return "n/a"
        if is_ms_field(field):
            return rounded_ms_value(value)
        if is_cache_reuse_ratio_field(field):
            return rounded_cache_reuse_ratio_value(value)
        return value

    transfer = metrics["transfer_totals"]
    outcome = metrics["agent_outcome"]
    phase_rows = metrics["phase_metrics"]
    subrequest_rows = metrics.get("subrequest_metrics", [])
    lines = [
        f"# Run Report: {manifest['run_id']}",
        "",
        f"- Model: `{manifest.get('model')}`",
        f"- App variant: `{manifest.get('app_variant')}`",
        f"- Hint profile: `{manifest.get('hint_profile')}`",
        f"- Hint provider: `{manifest.get('hint_provider')}`",
        f"- AgentBench result: `{manifest['paths']['agentbench_result_dir']}`",
        f"- SGLang transfer log: `{manifest['paths'].get('sglang_transfer_log')}`",
        "",
        "## Task Summary",
        "",
        f"- Repo: `{manifest['task'].get('repo')}`",
        f"- Instance id: `{display(manifest['task'].get('instance_id'))}`",
        f"- Base commit: `{display(manifest['task'].get('base_commit'))}`",
        f"- Task source: `{display(manifest['task'].get('task_source'))}`",
        f"- Summary: {display(manifest['task'].get('problem_statement_summary'))}",
        f"- Expected action: {display(manifest['task'].get('expected_agent_action'))}",
        f"- Validation expectation: {display(manifest['task'].get('validation_expectation'))}",
        f"- Problem preview: {display(manifest['task'].get('problem_statement_preview'))}",
        f"- Selected tests: `{display(manifest['task'].get('selected_tests_preview'))}`",
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
                "| {phase} | {latency} | {ttft} | {ttft_source} | {prompt} | {output} | {hit} | {cached} | {recomputed} | {ratio} |".format(
                    phase=row.get("phase", ""),
                    latency=display_field("latency_ms", row.get("latency_ms")),
                    ttft=display_field("ttft_ms", row.get("ttft_ms")),
                    ttft_source=display(row.get("ttft_source")),
                    prompt=display(row.get("prompt_tokens")),
                    output=display(row.get("output_tokens")),
                    hit=display(row.get("cache_hit")),
                    cached=display(row.get("cached_token_count")),
                    recomputed=display(row.get("recomputed_prefix_tokens")),
                    ratio=display_field("cache_reuse_ratio", row.get("cache_reuse_ratio")),
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
            f"- CUDA sync timing ms: `{format_metric(transfer['elapsed_ms_cuda_sync'], field='elapsed_ms_cuda_sync')}`",
            f"- Unique semantic token hashes: `{transfer['unique_semantic_token_hashes']}`",
            "",
        ]
    )
    if subrequest_rows:
        transfer_matched = sum(1 for row in subrequest_rows if row.get("transfer_request_id_matched"))
        time_matched = sum(1 for row in subrequest_rows if row.get("transfer_time_window_matched"))
        lines.extend(
            [
                "## Worker Subrequests",
                "",
                f"- Subrequests: `{len(subrequest_rows)}`",
                f"- Transfer request-id matches: `{transfer_matched}`",
                f"- Transfer time-window matches: `{time_matched}`",
                "",
                "| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |",
                "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
            ]
        )
        for row in subrequest_rows:
            lines.append(
                "| {phase} | {index} | {ttft} | {prompt} | {cached} | {ratio} | {sglang_request_id} | {transfer_matched} | {time_matched} |".format(
                    phase=row.get("phase", ""),
                    index=row.get("subrequest_index", ""),
                    ttft=display_field("ttft_ms", row.get("ttft_ms")),
                    prompt=display(row.get("prompt_tokens")),
                    cached=display(row.get("cached_token_count")),
                    ratio=display_field("cache_reuse_ratio", row.get("cache_reuse_ratio")),
                    sglang_request_id=display(row.get("sglang_request_id")),
                    transfer_matched=display(row.get("transfer_request_id_matched")),
                    time_matched=display(row.get("transfer_time_window_matched")),
                )
            )
        lines.append("")
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
    phase_rows = phase_metrics(result_dir, worker_runtime, events)
    subrequest_rows = subrequest_metrics(result_dir, worker_runtime, events)

    transfer_by_direction = transfer_totals.get("by_direction", {})
    device_to_host = transfer_by_direction.get("device_to_host", {})
    host_to_device = transfer_by_direction.get("host_to_device", {})
    workspace_patch = result_dir / "workspace.patch"
    git_diff_stat = result_dir / "others/git_diff_stat.txt"
    git_status = result_dir / "others/git_status.txt"
    patch_bytes = workspace_patch.stat().st_size if workspace_patch.exists() else 0
    resolved_hints = scalar(result.get("hint_json") or {})
    hint_profile = (
        result.get("hint_profile")
        or resolved_hints.get("hint_profile")
        or run_summary.get("hint_profile")
        or infer_hint_profile(resolved_hints)
    )
    hint_provider = (
        result.get("hint_provider")
        or resolved_hints.get("hint_provider")
        or run_summary.get("hint_provider")
        or "agentbench"
    )

    task_payload = dict_or_empty(result.get("task"))
    problem_statement = str(task_payload.get("problem_statement") or "")
    selected_tests = task_payload.get("selected_test_files_to_run")
    if not isinstance(selected_tests, list):
        selected_tests = []

    manifest = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_commit": git_sha(root),
        "model": result.get("model") or run_summary.get("model"),
        "app_variant": result.get("app_variant"),
        "hint_profile": hint_profile,
        "hint_provider": hint_provider,
        "resolved_hints": resolved_hints,
        "frontend_url": result.get("frontend_url"),
        "run_started_at": result.get("run_started_at"),
        "task": {
            "instance_id": task_payload.get("instance_id") or run_summary.get("instance_id"),
            "repo": task_payload.get("repo") or run_summary.get("repo"),
            "base_commit": task_payload.get("base_commit"),
            "task_source": result.get("task_source"),
            "problem_statement_summary": summarize_problem_statement(problem_statement),
            "problem_statement_preview": compact_text(clean_problem_statement_text(problem_statement), limit=220),
            "selected_tests_preview": ", ".join(str(item) for item in selected_tests[:3]),
            "patch_expected": bool(task_payload.get("patch")),
            "expected_agent_action": derive_expected_agent_action(
                problem_statement=clean_problem_statement_text(problem_statement),
                requirements=clean_problem_statement_text(task_payload.get("requirements") or ""),
                selected_tests=[str(item) for item in selected_tests],
                validation_command=str(task_payload.get("validation_command") or ""),
                patch_expected=bool(task_payload.get("patch")),
            ),
            "validation_expectation": derive_validation_expectation(
                [str(item) for item in selected_tests],
                str(task_payload.get("validation_command") or ""),
            ),
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
    overhead_rows = instrumentation_overhead_rows(events, manifest=manifest, run_id=run_id)

    run_level = {
        "run_id": run_id,
        "model": manifest.get("model"),
        "app_variant": manifest.get("app_variant"),
        "hint_profile": manifest.get("hint_profile"),
        "hint_provider": manifest.get("hint_provider"),
        "transfer_device_to_host_kv_mb": device_to_host.get("kv_num_mb_estimated", 0.0),
        "transfer_host_to_device_kv_mb": host_to_device.get("kv_num_mb_estimated", 0.0),
        "transfer_cuda_sync_ms": transfer_totals.get("elapsed_ms_cuda_sync", 0.0),
        "patch_nonempty": patch_bytes > 0,
        "workspace_patch_bytes": patch_bytes,
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
                "worker_runtime_json_matched",
                "worker_runtime_json_request_received_to_attached_ms",
                "worker_runtime_json_cached_tokens",
                    "worker_runtime_json_sglang_request_id",
                    "subrequest_metrics",
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
                    "transfer_request_id_matched",
                    "transfer_device_to_host_kv_mb_for_request",
                    "transfer_host_to_device_kv_mb_for_request",
                    "transfer_time_window_matched",
                    "transfer_device_to_host_kv_mb_for_time_window",
                    "transfer_host_to_device_kv_mb_for_time_window",
                    "instrumentation_overhead_metrics",
                    "subrequest_metrics.transfer_*",
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
                "When worker [RUNTIME_JSON] or transfer events include request metadata, the report uses those "
                "direct request ids. Otherwise phase names, hint metadata, task metadata, and patch outcome still "
                "come from the AgentBench result directory."
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
                "is missing, it falls back first to worker [RUNTIME_JSON] request_received-to-attached timing, then "
                "to plain worker logs as frontend request timestamp to first SGLang decode batch."
            ),
            "sglang_ttft_ms_prefill_to_first_decode": (
                "sglang_ttft_ms_prefill_to_first_decode is the SGLang-log-only timing from first prefill batch "
                "to first decode batch for the phase window."
            ),
            "subrequest_metrics": (
                "subrequest_metrics splits worker [RUNTIME_JSON] records by runtime_context_id/sglang_request_id. "
                "Use subrequest_metrics.csv when a single AgentBench phase sends multiple model requests. "
                "transfer_request_id_matched means direct id attribution; transfer_time_window_matched is a weaker "
                "timestamp-window fallback."
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
        "subrequest_metrics": subrequest_rows,
        "worker_runtime_log": worker_runtime,
        "transfer_totals": transfer_totals,
        "transfer_by_function_direction": transfer_rows,
        "instrumentation_overhead": {
            "enabled_event_count": sum(1 for event in events if transfer_event_has_overhead(event)),
            "rows": overhead_rows,
            "note": "Overhead fields are present only when SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1.",
        },
    }
    behavior_summary = build_agent_behavior_summary(
        result_dir=result_dir,
        result=result,
        manifest=manifest,
        run_level=run_level,
        phase_rows=phase_rows,
        subrequest_rows=subrequest_rows,
    )
    agent_tool_calls = collect_agent_tool_calls(result_dir, result, run_id)
    metrics["agent_behavior_summary"] = behavior_summary
    metrics["agent_tool_calls"] = {
        "tool_call_count": len(agent_tool_calls),
        "execute_command_count": sum(1 for row in agent_tool_calls if row.get("tool_name") == "execute"),
        "source_note": (
            "Exact arguments come from step_results.tool_call_details on new runs. "
            "Older runs fall back to prompt-evolution or result response transcripts when available."
        ),
    }

    write_json(out_dir / "run_manifest.json", manifest)
    write_json(out_dir / "runtime_metrics.json", metrics)
    write_phase_csv(out_dir / "phase_runtime_metrics.csv", phase_rows, run_level)
    write_subrequest_csv(out_dir / "model_request_metrics.csv", subrequest_rows, run_level)
    write_transfer_csv(out_dir / "transfer_events_by_function.csv", transfer_rows)
    write_rows_csv(out_dir / "instrumentation_overhead_metrics.csv", overhead_rows, INSTRUMENTATION_OVERHEAD_FIELDS)
    write_instrumentation_overhead_md(
        out_dir / "instrumentation_overhead_summary.md",
        overhead_rows,
        title="Instrumentation Overhead",
    )
    write_json(out_dir / "phase_summary.json", behavior_summary)
    write_agent_behavior_csv(out_dir / "phase_summary.csv", behavior_summary)
    write_agent_behavior_md(out_dir / "phase_summary.md", behavior_summary)
    write_json(out_dir / "tool_call_details.json", agent_tool_calls)
    write_agent_tool_calls_csv(out_dir / "tool_call_details.csv", agent_tool_calls)
    write_agent_tool_calls_md(out_dir / "tool_call_details.md", agent_tool_calls)
    write_summary_md(out_dir / "run_overview.md", manifest, metrics)
    for legacy_name in (
        "run_metrics.json",
        "run_metrics.csv",
        "subrequest_metrics.csv",
        "transfer_summary.csv",
        "agent_behavior_summary.json",
        "agent_behavior_summary.csv",
        "agent_behavior_summary.md",
        "agent_tool_calls.json",
        "agent_tool_calls.csv",
        "agent_tool_calls.md",
        "summary.md",
    ):
        unlink_if_exists(out_dir / legacy_name)

    default_out_root = (root / "experiments/reports/runs").resolve()
    if out_root.resolve() == default_out_root:
        latest_behavior_csv = root / "experiments/reports/latest_run_phase_summary.csv"
        latest_behavior_csv.parent.mkdir(parents=True, exist_ok=True)
        write_agent_behavior_csv(latest_behavior_csv, behavior_summary)
        latest_tool_calls_csv = root / "experiments/reports/latest_run_tool_call_details.csv"
        write_agent_tool_calls_csv(latest_tool_calls_csv, agent_tool_calls)
        unlink_if_exists(root / "experiments/reports/latest_agent_behavior_summary.csv")
        unlink_if_exists(root / "experiments/reports/latest_agent_tool_calls.csv")
        refresh_aggregate_tool_summaries(root, default_out_root)
        refresh_execution_prompt_summaries(root, default_out_root)
        refresh_task_summaries(root, default_out_root)
        refresh_runtime_metric_summaries(root, default_out_root)

    for rel in [
        "others/run_summary_table.csv",
        "others/measurement_summary_table.csv",
        "others/runtime_events_table.csv",
        "others/cache_value_summary_table.csv",
        "others/kv_hierarchy_summary_table.csv",
    ]:
        source = result_dir / rel
        if source.exists():
            copy_report_csv(source, out_dir / source.name)

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
    print(f"metrics: {out_dir / 'runtime_metrics.json'}")
    print(f"csv: {out_dir / 'phase_runtime_metrics.csv'}")
    print(f"phase summary: {out_dir / 'phase_summary.md'}")
    print(f"tool call details: {out_dir / 'tool_call_details.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
