#!/usr/bin/env python3

"""Classify Nsight Systems kernel time for GPU/LPU decode-split analysis."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


ATTENTION_KV_PATTERNS = [
    r"attention",
    r"flash(attn|attention)",
    r"flashinfer",
    r"paged",
    r"decode.*attn",
    r"attn.*decode",
    r"\bqkv\b",
    r"rotary",
    r"rope",
    r"\bkv\b",
    r"k_cache",
    r"v_cache",
]

FFN_MLP_PATTERNS = [
    r"gemm",
    r"matmul",
    r"cublas",
    r"cutlass",
    r"\bmlp\b",
    r"\bffn\b",
    r"feedforward",
    r"moe",
    r"expert",
    r"swiglu",
    r"gelu",
    r"silu",
]


def compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


ATTENTION_KV_RE = compile_patterns(ATTENTION_KV_PATTERNS)
FFN_MLP_RE = compile_patterns(FFN_MLP_PATTERNS)


def classify_kernel(name: str) -> str:
    if any(pattern.search(name) for pattern in ATTENTION_KV_RE):
        return "attention_kv"
    if any(pattern.search(name) for pattern in FFN_MLP_RE):
        return "ffn_mlp"
    return "other"


def table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [str(row[0]) for row in rows]


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]


def table_row_count(conn: sqlite3.Connection, table: str) -> int | None:
    try:
        return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    except sqlite3.Error:
        return None


def load_string_ids(conn: sqlite3.Connection) -> dict[int, str]:
    strings: dict[int, str] = {}
    if "StringIds" not in table_names(conn):
        return strings
    cols = table_columns(conn, "StringIds")
    id_col = "id" if "id" in cols else cols[0]
    value_col = "value" if "value" in cols else ("string" if "string" in cols else cols[-1])
    for row in conn.execute(f'SELECT "{id_col}", "{value_col}" FROM "StringIds"'):
        try:
            strings[int(row[0])] = str(row[1])
        except (TypeError, ValueError):
            continue
    return strings


def has_duration_columns(cols: list[str]) -> bool:
    colset = set(cols)
    return bool(
        {"start", "end"} <= colset
        or {"Start", "End"} <= colset
        or any(col in colset for col in ("duration", "Duration", "durationNs", "dur"))
    )


def describe_kernelish_tables(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    descriptions = []
    for name in table_names(conn):
        upper = name.upper()
        if "KERNEL" not in upper and "CUDA" not in upper:
            continue
        cols = table_columns(conn, name)
        descriptions.append(
            {
                "table": name,
                "row_count": table_row_count(conn, name),
                "columns": cols,
                "has_duration_columns": has_duration_columns(cols),
                "name_columns": pick_name_columns(cols),
            }
        )
    return descriptions


def pick_kernel_table(conn: sqlite3.Connection) -> str:
    tables = table_names(conn)
    exact_preferred = [
        "CUPTI_ACTIVITY_KIND_KERNEL",
        "CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL",
        "CUDA_GPU_KERNEL_EVENTS",
        "CUDA_KERNEL",
        "CUDA_KERNEL_EVENTS",
        "CUDA_GRAPH_EVENTS",
    ]
    candidates = []
    for table in exact_preferred:
        if table in tables:
            cols = table_columns(conn, table)
            if has_duration_columns(cols):
                candidates.append(table)

    for table in tables:
        upper = table.upper()
        if upper.startswith("ENUM_"):
            continue
        if "KERNEL" not in upper or table in candidates:
            continue
        cols = table_columns(conn, table)
        if not has_duration_columns(cols):
            continue
        candidates.append(table)

    for table in candidates:
        row_count = table_row_count(conn, table)
        if row_count and row_count > 0:
            return table
    if candidates:
        return candidates[0]

    descriptions = describe_kernelish_tables(conn)
    diagnostic = json.dumps(descriptions[:25], indent=2)
    raise SystemExit(
        "No CUDA kernel or CUDA graph event table found in Nsight SQLite export. "
        "Kernel/CUDA-like tables inspected:\n"
        f"{diagnostic}"
    )


def resolve_string_column(value: Any, strings: dict[int, str]) -> str:
    if value is None:
        return ""
    if isinstance(value, int) and value in strings:
        return strings[value]
    value_str = str(value)
    if value_str.isdigit() and int(value_str) in strings:
        return strings[int(value_str)]
    return value_str


def pick_name_columns(cols: list[str]) -> list[str]:
    ordered = [
        "demangledName",
        "shortName",
        "mangledName",
        "textId",
        "nameId",
        "demangledNameId",
        "shortNameId",
        "mangledNameId",
        "name",
        "Name",
        "kernelName",
        "KernelName",
    ]
    return [col for col in ordered if col in cols]


def time_bounds_ns_from_row(row: sqlite3.Row, cols: list[str]) -> tuple[int | None, int | None]:
    if "start" in cols and "end" in cols and row["start"] is not None and row["end"] is not None:
        return int(row["start"]), int(row["end"])
    if "Start" in cols and "End" in cols and row["Start"] is not None and row["End"] is not None:
        return int(row["Start"]), int(row["End"])
    return None, None


def duration_ns_from_row(row: sqlite3.Row, cols: list[str]) -> int | None:
    for col in ("duration", "Duration", "durationNs", "dur"):
        if col in cols and row[col] is not None:
            return int(row[col])
    start_ns, end_ns = time_bounds_ns_from_row(row, cols)
    if start_ns is not None and end_ns is not None:
        return end_ns - start_ns
    return None


def name_from_row(row: sqlite3.Row, name_cols: list[str], strings: dict[int, str]) -> str:
    for col in name_cols:
        value_str = resolve_string_column(row[col], strings)
        if value_str:
            return value_str
    return "<unknown>"


def read_kernel_rows(sqlite_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        strings = load_string_ids(conn)
        kernelish_tables = describe_kernelish_tables(conn)
        kernel_table = pick_kernel_table(conn)
        cols = table_columns(conn, kernel_table)
        name_cols = pick_name_columns(cols)
        if not name_cols:
            raise SystemExit(
                f"Kernel table {kernel_table!r} has no recognizable kernel name column. "
                f"Columns: {cols}"
            )

        rows: list[dict[str, Any]] = []
        query_cols = sorted(set(name_cols + [col for col in ("start", "end", "Start", "End", "duration", "Duration", "durationNs", "dur") if col in cols]))
        query = ", ".join(f'"{col}"' for col in query_cols)
        for raw in conn.execute(f'SELECT {query} FROM "{kernel_table}"'):
            duration_ns = duration_ns_from_row(raw, query_cols)
            if duration_ns is None or duration_ns < 0:
                continue
            start_ns, end_ns = time_bounds_ns_from_row(raw, query_cols)
            name = name_from_row(raw, name_cols, strings)
            rows.append(
                {
                    "kernel_name": name,
                    "bucket": classify_kernel(name),
                    "start_ns": start_ns,
                    "end_ns": end_ns,
                    "duration_ns": duration_ns,
                    "duration_ms": duration_ns / 1_000_000.0,
                }
            )
        meta = {
            "sqlite_path": str(sqlite_path),
            "kernel_table": kernel_table,
            "kernel_columns": cols,
            "name_columns": name_cols,
            "raw_table_row_count": table_row_count(conn, kernel_table),
            "kernel_row_count": len(rows),
            "kernelish_tables": kernelish_tables,
        }
        return rows, meta
    finally:
        conn.close()


def parse_log_timestamp(line: str) -> int | None:
    match = re.search(r"(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)", line)
    if not match:
        return None
    stamp = match.group("stamp").removesuffix("Z")
    try:
        dt = datetime.fromisoformat(stamp + "+00:00")
    except ValueError:
        return None
    return int(dt.timestamp() * 1_000_000_000)


def first_json_object(raw: str) -> str | None:
    start = raw.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for idx, char in enumerate(raw[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw[start : idx + 1]
    return None


def extract_runtime_json(line: str) -> dict[str, Any] | None:
    marker = "[RUNTIME_JSON]"
    if marker not in line:
        return None
    raw = first_json_object(line.split(marker, 1)[1])
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def parse_worker_phase_requests(
    worker_log: Path,
    hint_probe_id: str | None = None,
    agent_phase: str | None = None,
) -> list[dict[str, Any]]:
    if not worker_log.is_file():
        return []

    requests: dict[str, dict[str, Any]] = {}

    for line in worker_log.read_text(encoding="utf-8", errors="replace").splitlines():
        timestamp_ns = parse_log_timestamp(line)
        payload = extract_runtime_json(line)
        if timestamp_ns is None or payload is None:
            continue
        if payload.get("component") != "worker.decode":
            continue
        agent_hints = payload.get("agent_hints") or {}
        payload_probe_id = agent_hints.get("hint_probe_id")
        payload_phase = agent_hints.get("agent_phase")
        external_request_id = payload.get("external_request_id")
        if not external_request_id:
            continue
        request_id = str(external_request_id)

        if hint_probe_id:
            is_target = str(payload_probe_id) == hint_probe_id
        elif agent_phase:
            is_target = str(payload_phase) == agent_phase
        else:
            is_target = payload_probe_id is not None
        if not is_target and request_id not in requests:
            continue

        record = requests.setdefault(
            request_id,
            {
                "source": str(worker_log),
                "request_id": request_id,
                "hint_probe_id": None,
                "agent_phase": None,
            },
        )
        if payload_probe_id is not None:
            record["hint_probe_id"] = str(payload_probe_id)
        if payload_phase is not None:
            record["agent_phase"] = str(payload_phase)
        record.setdefault("agent_hints", agent_hints if isinstance(agent_hints, dict) else {})
        if isinstance(agent_hints, dict) and agent_hints:
            record["agent_hints"] = agent_hints

        event_type = str(payload.get("event_type") or "")
        if event_type.endswith("request_received"):
            record["request_received_ns"] = timestamp_ns
        elif event_type.endswith("request_attached"):
            record["request_attached_ns"] = timestamp_ns
        elif event_type.endswith("request_completed"):
            record["request_completed_ns"] = timestamp_ns

    required = {"request_received_ns", "request_attached_ns", "request_completed_ns"}
    complete = [record for record in requests.values() if required <= set(record)]
    complete.sort(key=lambda record: int(record["request_received_ns"]))
    return complete


def parse_worker_phase_hints(worker_log: Path, hint_probe_id: str | None = None) -> dict[str, Any] | None:
    requests = parse_worker_phase_requests(worker_log, hint_probe_id=hint_probe_id)
    if not requests:
        return None
    if hint_probe_id:
        return requests[-1]
    decode_sweep = [request for request in requests if request.get("agent_phase") == "decode_sweep"]
    return (decode_sweep or requests)[-1]


def kernel_time_range(rows: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    starts = [int(row["start_ns"]) for row in rows if row.get("start_ns") is not None]
    ends = [int(row["end_ns"]) for row in rows if row.get("end_ns") is not None]
    if not starts or not ends:
        return None, None
    return min(starts), max(ends)


def build_phase_windows_for_requests(
    rows: list[dict[str, Any]],
    phase_requests: list[dict[str, Any]],
    *,
    phase_mode: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not phase_requests or phase_mode == "none":
        return [], {"phase_assignment_mode": "none", "phase_hints": None, "phase_request_count": 0}

    min_kernel_ns, max_kernel_ns = kernel_time_range(rows)
    if min_kernel_ns is None or max_kernel_ns is None:
        return [], {"phase_assignment_mode": "missing_kernel_time_bounds", "phase_hints": phase_requests}

    epoch_like = min_kernel_ns > 1_500_000_000_000_000_000
    if phase_mode == "epoch-wall" or (phase_mode == "auto" and epoch_like):
        mode = "epoch_wall"
    elif phase_mode in ("auto", "relative-tail"):
        mode = "relative_tail_heuristic"
    else:
        raise SystemExit(f"Unsupported --phase-mode: {phase_mode}")

    requests = sorted(phase_requests, key=lambda request: int(request["request_received_ns"]))
    first_received_ns = int(requests[0]["request_received_ns"])
    last_completed_ns = int(requests[-1]["request_completed_ns"])
    total_request_span_ns = max(1, last_completed_ns - first_received_ns)
    kernel_span_ns = max(1, max_kernel_ns - min_kernel_ns)
    relative_time_scale = 1.0 if mode == "epoch_wall" else min(1.0, kernel_span_ns / total_request_span_ns)
    relative_span_ns = max(1, int(total_request_span_ns * relative_time_scale))
    relative_base_start = max_kernel_ns - relative_span_ns
    if mode == "relative_tail_heuristic" and relative_time_scale < 1.0:
        mode = "relative_tail_scaled_heuristic"

    windows = []
    for request_index, phase_hints in enumerate(requests):
        received_ns = int(phase_hints["request_received_ns"])
        attached_ns = int(phase_hints["request_attached_ns"])
        completed_ns = int(phase_hints["request_completed_ns"])
        prefill_duration_ns = max(1, int((attached_ns - received_ns) * relative_time_scale))
        decode_duration_ns = max(1, int((completed_ns - attached_ns) * relative_time_scale))
        if mode == "epoch_wall":
            base_start = received_ns
        else:
            base_start = relative_base_start + int((received_ns - first_received_ns) * relative_time_scale)
        common = {
            "request_index": request_index,
            "request_id": phase_hints.get("request_id"),
            "hint_probe_id": phase_hints.get("hint_probe_id"),
            "agent_phase": phase_hints.get("agent_phase") or "unknown",
        }
        windows.extend(
            [
                {
                    **common,
                    "phase": "prefill",
                    "start_ns": base_start,
                    "end_ns": base_start + prefill_duration_ns,
                    "duration_ms": round(prefill_duration_ns / 1_000_000.0, 3),
                },
                {
                    **common,
                    "phase": "decode",
                    "start_ns": base_start + prefill_duration_ns,
                    "end_ns": base_start + prefill_duration_ns + decode_duration_ns,
                    "duration_ms": round(decode_duration_ns / 1_000_000.0, 3),
                },
            ]
        )
    return windows, {
        "phase_assignment_mode": mode,
        "phase_hints": requests[-1] if requests else None,
        "phase_requests": requests,
        "phase_request_count": len(requests),
        "kernel_time_range_ns": {
            "min": min_kernel_ns,
            "max": max_kernel_ns,
            "epoch_like": epoch_like,
            "span_ns": kernel_span_ns,
        },
        "relative_time_scale": relative_time_scale,
        "phase_windows": windows,
    }


def build_phase_windows(
    rows: list[dict[str, Any]],
    phase_hints: dict[str, Any] | None,
    *,
    phase_mode: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return build_phase_windows_for_requests(rows, [phase_hints] if phase_hints else [], phase_mode=phase_mode)


def window_for_row(row: dict[str, Any], phase_windows: list[dict[str, Any]]) -> dict[str, Any] | None:
    start_ns = row.get("start_ns")
    end_ns = row.get("end_ns")
    if start_ns is None or end_ns is None:
        return None
    row_start = int(start_ns)
    row_end = int(end_ns)
    best_window = None
    best_overlap = 0
    for window in phase_windows:
        overlap = min(row_end, int(window["end_ns"])) - max(row_start, int(window["start_ns"]))
        if overlap > best_overlap:
            best_overlap = overlap
            best_window = window
    return best_window


def phase_for_row(row: dict[str, Any], phase_windows: list[dict[str, Any]]) -> str:
    window = window_for_row(row, phase_windows)
    return str(window["phase"]) if window else "unassigned"


def apply_phase_assignment(rows: list[dict[str, Any]], phase_windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assigned = []
    for row in rows:
        next_row = dict(row)
        window = window_for_row(next_row, phase_windows)
        if window:
            next_row["phase"] = str(window["phase"])
            next_row["agent_phase"] = str(window.get("agent_phase") or "unknown")
            next_row["hint_probe_id"] = window.get("hint_probe_id")
            next_row["request_id"] = window.get("request_id")
            next_row["request_index"] = window.get("request_index")
        else:
            next_row["phase"] = "unassigned"
            next_row["agent_phase"] = "unassigned"
            next_row["hint_probe_id"] = None
            next_row["request_id"] = None
            next_row["request_index"] = None
        assigned.append(next_row)
    return assigned


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_bucket: dict[str, dict[str, Any]] = {}
    by_phase_bucket: dict[tuple[str, str], dict[str, Any]] = {}
    by_phase_kernel: dict[tuple[str, str, str], dict[str, Any]] = {}
    by_agent_phase_bucket: dict[tuple[str, str], dict[str, Any]] = {}
    by_agent_phase_inference_bucket: dict[tuple[str, str, str], dict[str, Any]] = {}
    by_agent_phase_kernel: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    by_kernel: dict[tuple[str, str], dict[str, Any]] = {}
    total_ms = sum(float(row["duration_ms"]) for row in rows)
    for row in rows:
        bucket = str(row["bucket"])
        phase = str(row.get("phase") or "unassigned")
        agent_phase = str(row.get("agent_phase") or "unassigned")
        name = str(row["kernel_name"])
        duration_ms = float(row["duration_ms"])
        bucket_entry = by_bucket.setdefault(bucket, {"bucket": bucket, "kernel_count": 0, "duration_ms": 0.0})
        bucket_entry["kernel_count"] += 1
        bucket_entry["duration_ms"] += duration_ms
        phase_bucket_entry = by_phase_bucket.setdefault(
            (phase, bucket),
            {"phase": phase, "bucket": bucket, "kernel_count": 0, "duration_ms": 0.0},
        )
        phase_bucket_entry["kernel_count"] += 1
        phase_bucket_entry["duration_ms"] += duration_ms
        phase_kernel_entry = by_phase_kernel.setdefault(
            (phase, bucket, name),
            {"phase": phase, "bucket": bucket, "kernel_name": name, "kernel_count": 0, "duration_ms": 0.0},
        )
        phase_kernel_entry["kernel_count"] += 1
        phase_kernel_entry["duration_ms"] += duration_ms
        agent_phase_bucket_entry = by_agent_phase_bucket.setdefault(
            (agent_phase, bucket),
            {"agent_phase": agent_phase, "bucket": bucket, "kernel_count": 0, "duration_ms": 0.0},
        )
        agent_phase_bucket_entry["kernel_count"] += 1
        agent_phase_bucket_entry["duration_ms"] += duration_ms
        agent_phase_inference_bucket_entry = by_agent_phase_inference_bucket.setdefault(
            (agent_phase, phase, bucket),
            {
                "agent_phase": agent_phase,
                "inference_phase": phase,
                "bucket": bucket,
                "kernel_count": 0,
                "duration_ms": 0.0,
            },
        )
        agent_phase_inference_bucket_entry["kernel_count"] += 1
        agent_phase_inference_bucket_entry["duration_ms"] += duration_ms
        agent_phase_kernel_entry = by_agent_phase_kernel.setdefault(
            (agent_phase, phase, bucket, name),
            {
                "agent_phase": agent_phase,
                "inference_phase": phase,
                "bucket": bucket,
                "kernel_name": name,
                "kernel_count": 0,
                "duration_ms": 0.0,
            },
        )
        agent_phase_kernel_entry["kernel_count"] += 1
        agent_phase_kernel_entry["duration_ms"] += duration_ms
        kernel_entry = by_kernel.setdefault(
            (bucket, name),
            {"bucket": bucket, "kernel_name": name, "kernel_count": 0, "duration_ms": 0.0},
        )
        kernel_entry["kernel_count"] += 1
        kernel_entry["duration_ms"] += duration_ms

    bucket_rows = []
    for entry in by_bucket.values():
        duration_ms = float(entry["duration_ms"])
        entry["duration_ms"] = round(duration_ms, 3)
        entry["pct"] = round((duration_ms / total_ms * 100.0), 3) if total_ms else 0.0
        bucket_rows.append(entry)
    bucket_rows.sort(key=lambda item: float(item["duration_ms"]), reverse=True)

    phase_totals: dict[str, float] = {}
    for entry in by_phase_bucket.values():
        phase_totals[str(entry["phase"])] = phase_totals.get(str(entry["phase"]), 0.0) + float(entry["duration_ms"])

    phase_bucket_rows = []
    for entry in by_phase_bucket.values():
        duration_ms = float(entry["duration_ms"])
        phase_total = phase_totals.get(str(entry["phase"]), 0.0)
        entry["duration_ms"] = round(duration_ms, 3)
        entry["pct_of_phase"] = round((duration_ms / phase_total * 100.0), 3) if phase_total else 0.0
        entry["pct_total"] = round((duration_ms / total_ms * 100.0), 3) if total_ms else 0.0
        phase_bucket_rows.append(entry)
    phase_bucket_rows.sort(key=lambda item: (str(item["phase"]), -float(item["duration_ms"])))

    phase_kernel_rows = []
    for entry in by_phase_kernel.values():
        duration_ms = float(entry["duration_ms"])
        phase_total = phase_totals.get(str(entry["phase"]), 0.0)
        entry["duration_ms"] = round(duration_ms, 3)
        entry["pct_of_phase"] = round((duration_ms / phase_total * 100.0), 3) if phase_total else 0.0
        entry["pct_total"] = round((duration_ms / total_ms * 100.0), 3) if total_ms else 0.0
        phase_kernel_rows.append(entry)
    phase_kernel_rows.sort(key=lambda item: (str(item["phase"]), -float(item["duration_ms"])))

    phase_summary_rows = []
    for phase, duration_ms in phase_totals.items():
        phase_summary_rows.append(
            {
                "phase": phase,
                "kernel_count": sum(1 for row in rows if str(row.get("phase") or "unassigned") == phase),
                "duration_ms": round(duration_ms, 3),
                "pct_total": round((duration_ms / total_ms * 100.0), 3) if total_ms else 0.0,
            }
        )
    phase_summary_rows.sort(key=lambda item: float(item["duration_ms"]), reverse=True)

    agent_phase_totals: dict[str, float] = {}
    for entry in by_agent_phase_bucket.values():
        agent_phase_totals[str(entry["agent_phase"])] = (
            agent_phase_totals.get(str(entry["agent_phase"]), 0.0) + float(entry["duration_ms"])
        )

    agent_phase_bucket_rows = []
    for entry in by_agent_phase_bucket.values():
        duration_ms = float(entry["duration_ms"])
        agent_phase_total = agent_phase_totals.get(str(entry["agent_phase"]), 0.0)
        entry["duration_ms"] = round(duration_ms, 3)
        entry["pct_of_agent_phase"] = round((duration_ms / agent_phase_total * 100.0), 3) if agent_phase_total else 0.0
        entry["pct_total"] = round((duration_ms / total_ms * 100.0), 3) if total_ms else 0.0
        agent_phase_bucket_rows.append(entry)
    agent_phase_bucket_rows.sort(key=lambda item: (str(item["agent_phase"]), -float(item["duration_ms"])))

    agent_phase_inference_totals: dict[tuple[str, str], float] = {}
    for entry in by_agent_phase_inference_bucket.values():
        key = (str(entry["agent_phase"]), str(entry["inference_phase"]))
        agent_phase_inference_totals[key] = agent_phase_inference_totals.get(key, 0.0) + float(entry["duration_ms"])

    agent_phase_inference_bucket_rows = []
    for entry in by_agent_phase_inference_bucket.values():
        duration_ms = float(entry["duration_ms"])
        agent_phase_total = agent_phase_totals.get(str(entry["agent_phase"]), 0.0)
        inference_total = agent_phase_inference_totals.get(
            (str(entry["agent_phase"]), str(entry["inference_phase"])),
            0.0,
        )
        entry["duration_ms"] = round(duration_ms, 3)
        entry["pct_of_inference_phase"] = round((duration_ms / inference_total * 100.0), 3) if inference_total else 0.0
        entry["pct_of_agent_phase"] = round((duration_ms / agent_phase_total * 100.0), 3) if agent_phase_total else 0.0
        entry["pct_total"] = round((duration_ms / total_ms * 100.0), 3) if total_ms else 0.0
        agent_phase_inference_bucket_rows.append(entry)
    agent_phase_inference_bucket_rows.sort(
        key=lambda item: (str(item["agent_phase"]), str(item["inference_phase"]), -float(item["duration_ms"]))
    )

    agent_phase_summary_rows = []
    for agent_phase, duration_ms in agent_phase_totals.items():
        agent_phase_summary_rows.append(
            {
                "agent_phase": agent_phase,
                "kernel_count": sum(1 for row in rows if str(row.get("agent_phase") or "unassigned") == agent_phase),
                "duration_ms": round(duration_ms, 3),
                "pct_total": round((duration_ms / total_ms * 100.0), 3) if total_ms else 0.0,
            }
        )
    agent_phase_summary_rows.sort(key=lambda item: float(item["duration_ms"]), reverse=True)

    agent_phase_kernel_rows = []
    for entry in by_agent_phase_kernel.values():
        duration_ms = float(entry["duration_ms"])
        agent_phase_total = agent_phase_totals.get(str(entry["agent_phase"]), 0.0)
        inference_total = agent_phase_inference_totals.get(
            (str(entry["agent_phase"]), str(entry["inference_phase"])),
            0.0,
        )
        entry["duration_ms"] = round(duration_ms, 3)
        entry["pct_of_inference_phase"] = round((duration_ms / inference_total * 100.0), 3) if inference_total else 0.0
        entry["pct_of_agent_phase"] = round((duration_ms / agent_phase_total * 100.0), 3) if agent_phase_total else 0.0
        entry["pct_total"] = round((duration_ms / total_ms * 100.0), 3) if total_ms else 0.0
        agent_phase_kernel_rows.append(entry)
    agent_phase_kernel_rows.sort(
        key=lambda item: (str(item["agent_phase"]), str(item["inference_phase"]), -float(item["duration_ms"]))
    )

    kernel_rows = []
    for entry in by_kernel.values():
        duration_ms = float(entry["duration_ms"])
        entry["duration_ms"] = round(duration_ms, 3)
        entry["pct"] = round((duration_ms / total_ms * 100.0), 3) if total_ms else 0.0
        kernel_rows.append(entry)
    kernel_rows.sort(key=lambda item: float(item["duration_ms"]), reverse=True)

    return {
        "total_kernel_duration_ms": round(total_ms, 3),
        "total_kernel_count": len(rows),
        "bucket_summary": bucket_rows,
        "phase_summary": phase_summary_rows,
        "phase_bucket_summary": phase_bucket_rows,
        "top_phase_kernels": phase_kernel_rows[:100],
        "agent_phase_summary": agent_phase_summary_rows,
        "agent_phase_bucket_summary": agent_phase_bucket_rows,
        "agent_phase_inference_bucket_summary": agent_phase_inference_bucket_rows,
        "top_agent_phase_kernels": agent_phase_kernel_rows[:200],
        "top_kernels": kernel_rows[:50],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary: dict[str, Any], meta: dict[str, Any]) -> None:
    lines = [
        "# Nsight Decode Kernel Classification",
        "",
        f"SQLite: `{meta['sqlite_path']}`",
        f"Kernel table: `{meta['kernel_table']}`",
        f"Kernel rows: {summary['total_kernel_count']}",
        f"Total kernel duration ms: {summary['total_kernel_duration_ms']}",
        f"Phase assignment: `{meta.get('phase_assignment_mode', 'none')}`",
        "",
        "## Bucket Summary",
        "",
        "| bucket | kernel count | duration ms | pct |",
        "|---|---:|---:|---:|",
    ]
    for row in summary["bucket_summary"]:
        lines.append(f"| {row['bucket']} | {row['kernel_count']} | {row['duration_ms']} | {row['pct']} |")
    if summary.get("phase_bucket_summary"):
        lines.extend(
            [
                "",
                "## Phase Summary",
                "",
                "| phase | kernel count | duration ms | pct total |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in summary["phase_summary"]:
            lines.append(f"| {row['phase']} | {row['kernel_count']} | {row['duration_ms']} | {row['pct_total']} |")
        lines.extend(
            [
                "",
                "## Phase x Bucket Summary",
                "",
                "| phase | bucket | kernel count | duration ms | pct of phase | pct total |",
                "|---|---|---:|---:|---:|---:|",
            ]
        )
        for row in summary["phase_bucket_summary"]:
            lines.append(
                f"| {row['phase']} | {row['bucket']} | {row['kernel_count']} | "
                f"{row['duration_ms']} | {row['pct_of_phase']} | {row['pct_total']} |"
            )
        lines.extend(
            [
                "",
                "## Top Phase Kernels",
                "",
                "| phase | bucket | kernel name | count | duration ms | pct of phase | pct total |",
                "|---|---|---|---:|---:|---:|---:|",
            ]
        )
        for row in summary["top_phase_kernels"]:
            kernel_name = str(row["kernel_name"]).replace("|", "\\|")
            lines.append(
                f"| {row['phase']} | {row['bucket']} | `{kernel_name}` | {row['kernel_count']} | "
                f"{row['duration_ms']} | {row['pct_of_phase']} | {row['pct_total']} |"
            )
    if summary.get("agent_phase_summary"):
        lines.extend(
            [
                "",
                "## Agent Phase Summary",
                "",
                "| agent phase | kernel count | duration ms | pct total |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in summary["agent_phase_summary"]:
            lines.append(
                f"| {row['agent_phase']} | {row['kernel_count']} | {row['duration_ms']} | {row['pct_total']} |"
            )
        lines.extend(
            [
                "",
                "## Agent Phase x Bucket Summary",
                "",
                "| agent phase | bucket | kernel count | duration ms | pct of agent phase | pct total |",
                "|---|---|---:|---:|---:|---:|",
            ]
        )
        for row in summary["agent_phase_bucket_summary"]:
            lines.append(
                f"| {row['agent_phase']} | {row['bucket']} | {row['kernel_count']} | "
                f"{row['duration_ms']} | {row['pct_of_agent_phase']} | {row['pct_total']} |"
            )
        lines.extend(
            [
                "",
                "## Agent Phase x Inference Phase x Bucket Summary",
                "",
                "| agent phase | inference phase | bucket | kernel count | duration ms | pct of inference phase | pct of agent phase | pct total |",
                "|---|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for row in summary["agent_phase_inference_bucket_summary"]:
            lines.append(
                f"| {row['agent_phase']} | {row['inference_phase']} | {row['bucket']} | {row['kernel_count']} | "
                f"{row['duration_ms']} | {row['pct_of_inference_phase']} | "
                f"{row['pct_of_agent_phase']} | {row['pct_total']} |"
            )
        lines.extend(
            [
                "",
                "## Top Agent Phase Kernels",
                "",
                "| agent phase | inference phase | bucket | kernel name | count | duration ms | pct of inference phase | pct of agent phase | pct total |",
                "|---|---|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for row in summary["top_agent_phase_kernels"]:
            kernel_name = str(row["kernel_name"]).replace("|", "\\|")
            lines.append(
                f"| {row['agent_phase']} | {row['inference_phase']} | {row['bucket']} | `{kernel_name}` | "
                f"{row['kernel_count']} | {row['duration_ms']} | {row['pct_of_inference_phase']} | "
                f"{row['pct_of_agent_phase']} | {row['pct_total']} |"
            )
    lines.extend(
        [
            "",
            "## Top Kernels",
            "",
            "| bucket | kernel name | count | duration ms | pct |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in summary["top_kernels"]:
        kernel_name = str(row["kernel_name"]).replace("|", "\\|")
        lines.append(
            f"| {row['bucket']} | `{kernel_name}` | {row['kernel_count']} | {row['duration_ms']} | {row['pct']} |"
        )
    if not summary["total_kernel_count"] and meta.get("kernelish_tables"):
        lines.extend(
            [
                "",
                "## CUDA Table Diagnostic",
                "",
                "| table | rows | duration columns | name columns |",
                "|---|---:|---|---|",
            ]
        )
        for table in meta["kernelish_tables"]:
            name_columns = ", ".join(table.get("name_columns") or [])
            lines.append(
                f"| `{table['table']}` | {table.get('row_count')} | "
                f"{table.get('has_duration_columns')} | {name_columns or 'none'} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", required=True, type=Path, help="Nsight Systems SQLite export")
    parser.add_argument("--out-dir", type=Path, help="Output directory. Defaults beside SQLite file.")
    parser.add_argument("--worker-log", type=Path, help="Worker log containing worker.decode runtime JSON events.")
    parser.add_argument("--hint-probe-id", help="Specific measured request hint_probe_id to use for phase windows.")
    parser.add_argument("--agent-phase", help="Only use worker requests with this agent_phase for phase windows.")
    parser.add_argument(
        "--phase-mode",
        choices=["auto", "none", "epoch-wall", "relative-tail"],
        default="auto",
        help=(
            "How to map worker log phase timestamps onto kernel timestamps. "
            "auto uses epoch-wall when possible, otherwise relative-tail."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sqlite_path = args.sqlite.resolve()
    if not sqlite_path.is_file():
        raise SystemExit(
            f"Nsight SQLite export not found: {sqlite_path}\n"
            "Create it from a .nsys-rep first, for example:\n"
            f"  nsys export --type sqlite --output {sqlite_path} <profile>.nsys-rep"
        )

    out_dir = args.out_dir.resolve() if args.out_dir else sqlite_path.with_suffix("").with_name(sqlite_path.stem + "_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)

    rows, meta = read_kernel_rows(sqlite_path)
    phase_requests = (
        parse_worker_phase_requests(args.worker_log, hint_probe_id=args.hint_probe_id, agent_phase=args.agent_phase)
        if args.worker_log
        else []
    )
    phase_windows, phase_meta = build_phase_windows_for_requests(rows, phase_requests, phase_mode=args.phase_mode)
    rows = apply_phase_assignment(rows, phase_windows)
    meta.update(phase_meta)
    summary = summarize(rows)
    payload = {"metadata": meta, **summary}

    (out_dir / "kernel_classification.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_csv(out_dir / "bucket_summary.csv", summary["bucket_summary"])
    write_csv(out_dir / "phase_summary.csv", summary["phase_summary"])
    write_csv(out_dir / "phase_bucket_summary.csv", summary["phase_bucket_summary"])
    write_csv(out_dir / "top_phase_kernels.csv", summary["top_phase_kernels"])
    write_csv(out_dir / "agent_phase_summary.csv", summary["agent_phase_summary"])
    write_csv(out_dir / "agent_phase_bucket_summary.csv", summary["agent_phase_bucket_summary"])
    write_csv(out_dir / "agent_phase_inference_bucket_summary.csv", summary["agent_phase_inference_bucket_summary"])
    write_csv(out_dir / "top_agent_phase_kernels.csv", summary["top_agent_phase_kernels"])
    write_csv(out_dir / "top_kernels.csv", summary["top_kernels"])
    write_markdown(out_dir / "summary.md", summary, meta)

    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
