#!/usr/bin/env python3
"""Parse SGLang transfer JSON logs into JSONL and summary CSV outputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


PREFIX = "[SGLANG_TRANSFER_JSON] "


def direction_label(direction: str) -> str:
    if direction == "host_to_device":
        return "host->device"
    if direction == "device_to_host":
        return "device->host"
    return direction


def preview_to_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def kv_estimates(event: dict) -> tuple[float, float]:
    token_granular = event.get("kv_num_bytes_estimated_token_granular")
    page_granular = event.get("kv_num_bytes_estimated_page_granular")

    if token_granular is None:
        if event.get("kv_item_granularity_assumption") == "token":
            token_granular = event.get("kv_num_bytes_estimated")
        else:
            num_items = event.get("kv_num_items")
            bytes_per_token_per_layer = event.get("kv_bytes_per_token_per_layer_estimated")
            layer_count = event.get("kv_layer_count_estimated")
            if num_items is not None and bytes_per_token_per_layer is not None and layer_count is not None:
                token_granular = (
                    as_float(num_items)
                    * as_float(bytes_per_token_per_layer)
                    * as_float(layer_count)
                )
            else:
                token_granular = event.get("kv_num_bytes_estimated")

    if page_granular is None:
        if event.get("kv_item_granularity_assumption") != "token" and event.get("kv_num_bytes_estimated") is not None:
            page_granular = event.get("kv_num_bytes_estimated")
        else:
            page_size = event.get("kv_page_size")
            page_granular = as_float(token_granular) * as_float(page_size, 1.0)

    return as_float(token_granular), as_float(page_granular)


def iter_events(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if PREFIX not in line:
                continue
            payload = line.split(PREFIX, 1)[1].strip()
            try:
                event = json.loads(payload)
            except json.JSONDecodeError as exc:
                yield {
                    "event": "sglang.transfer_parse_error",
                    "source": str(path),
                    "line_number": line_number,
                    "error": str(exc),
                    "raw": payload,
                }
                continue
            event.setdefault("source", str(path))
            event.setdefault("line_number", line_number)
            yield event


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path, help="Worker logs or transfer JSONL files.")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    events_path = args.out_dir / "transfer_events.jsonl"
    event_rows_path = args.out_dir / "transfer_events.csv"
    summary_path = args.out_dir / "transfer_summary.csv"

    summaries: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {
            "count": 0,
            "num_bytes_observed": 0,
            "kv_num_bytes_estimated": 0,
            "kv_num_bytes_estimated_page_granular": 0,
            "elapsed_ms": 0.0,
            "elapsed_ms_wall": 0.0,
            "elapsed_ms_cuda_sync": 0.0,
            "cuda_sync_wait_ms": 0.0,
            "cuda_sync_timing_count": 0,
            "errors": 0,
        }
    )

    event_row_fields = [
        "source",
        "line_number",
        "timestamp_ns",
        "direction",
        "direction_label",
        "function",
        "semantic_context_function",
        "token_preview_source",
        "semantic_token_source",
        "semantic_token_count",
        "token_preview_count",
        "token_ids_preview",
        "num_bytes_observed",
        "num_mb_observed",
        "kv_num_bytes_estimated",
        "kv_num_mb_estimated",
        "elapsed_ms_wall",
        "elapsed_ms_cuda_sync",
        "cuda_sync_wait_ms",
        "error",
    ]

    with (
        events_path.open("w", encoding="utf-8") as event_out,
        event_rows_path.open("w", encoding="utf-8", newline="") as event_rows_out,
    ):
        event_rows = csv.DictWriter(event_rows_out, fieldnames=event_row_fields)
        event_rows.writeheader()
        for input_path in args.inputs:
            for event in iter_events(input_path):
                event_out.write(json.dumps(event, sort_keys=True, default=str) + "\n")
                if event.get("event") != "sglang.transfer":
                    continue
                token_granular, page_granular = kv_estimates(event)
                wall_ms = as_float(event.get("elapsed_ms_wall", event.get("elapsed_ms") or 0))
                event_rows.writerow(
                    {
                        "source": event.get("source", ""),
                        "line_number": event.get("line_number", ""),
                        "timestamp_ns": event.get("timestamp_ns", ""),
                        "direction": event.get("direction", ""),
                        "direction_label": direction_label(str(event.get("direction", ""))),
                        "function": event.get("function", ""),
                        "semantic_context_function": event.get("semantic_context_function", ""),
                        "token_preview_source": event.get("token_preview_source", ""),
                        "semantic_token_source": event.get("semantic_token_source", ""),
                        "semantic_token_count": event.get("semantic_token_count", ""),
                        "token_preview_count": event.get("token_preview_count", ""),
                        "token_ids_preview": preview_to_text(event.get("token_ids_preview")),
                        "num_bytes_observed": event.get("num_bytes_observed", ""),
                        "num_mb_observed": event.get("num_mb_observed", ""),
                        "kv_num_bytes_estimated": int(token_granular),
                        "kv_num_mb_estimated": token_granular / (1024.0 * 1024.0),
                        "elapsed_ms_wall": wall_ms,
                        "elapsed_ms_cuda_sync": event.get("elapsed_ms_cuda_sync", ""),
                        "cuda_sync_wait_ms": event.get("cuda_sync_wait_ms", ""),
                        "error": event.get("error", ""),
                    }
                )
                key = (str(event.get("function", "")), str(event.get("direction", "")))
                summary = summaries[key]
                summary["count"] += 1
                summary["num_bytes_observed"] += float(event.get("num_bytes_observed") or 0)
                summary["kv_num_bytes_estimated"] += token_granular
                summary["kv_num_bytes_estimated_page_granular"] += page_granular
                summary["elapsed_ms"] += float(event.get("elapsed_ms") or wall_ms)
                summary["elapsed_ms_wall"] += wall_ms
                if event.get("elapsed_ms_cuda_sync") is not None:
                    summary["elapsed_ms_cuda_sync"] += as_float(event.get("elapsed_ms_cuda_sync"))
                    summary["cuda_sync_wait_ms"] += as_float(event.get("cuda_sync_wait_ms"))
                    summary["cuda_sync_timing_count"] += 1
                if event.get("error"):
                    summary["errors"] += 1

    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "function",
                "direction",
                "count",
                "num_bytes_observed",
                "num_kb_observed",
                "num_mb_observed",
                "kv_num_bytes_estimated",
                "kv_num_kb_estimated",
                "kv_num_mb_estimated",
                "kv_num_bytes_estimated_page_granular",
                "kv_num_mb_estimated_page_granular",
                "elapsed_ms",
                "elapsed_ms_wall",
                "avg_elapsed_ms",
                "avg_elapsed_ms_wall",
                "elapsed_ms_cuda_sync",
                "avg_elapsed_ms_cuda_sync",
                "cuda_sync_wait_ms",
                "avg_cuda_sync_wait_ms",
                "cuda_sync_timing_count",
                "errors",
            ],
        )
        writer.writeheader()
        for (function, direction), summary in sorted(summaries.items()):
            count = summary["count"]
            elapsed_ms = summary["elapsed_ms"]
            elapsed_ms_wall = summary["elapsed_ms_wall"]
            elapsed_ms_cuda_sync = summary["elapsed_ms_cuda_sync"]
            cuda_sync_wait_ms = summary["cuda_sync_wait_ms"]
            cuda_sync_timing_count = summary["cuda_sync_timing_count"]
            bytes_observed = summary["num_bytes_observed"]
            kv_bytes_estimated = summary["kv_num_bytes_estimated"]
            kv_bytes_estimated_page_granular = summary["kv_num_bytes_estimated_page_granular"]
            writer.writerow(
                {
                    "function": function,
                    "direction": direction,
                    "count": int(count),
                    "num_bytes_observed": int(bytes_observed),
                    "num_kb_observed": bytes_observed / 1024.0,
                    "num_mb_observed": bytes_observed / (1024.0 * 1024.0),
                    "kv_num_bytes_estimated": int(kv_bytes_estimated),
                    "kv_num_kb_estimated": kv_bytes_estimated / 1024.0,
                    "kv_num_mb_estimated": kv_bytes_estimated / (1024.0 * 1024.0),
                    "kv_num_bytes_estimated_page_granular": int(kv_bytes_estimated_page_granular),
                    "kv_num_mb_estimated_page_granular": kv_bytes_estimated_page_granular / (1024.0 * 1024.0),
                    "elapsed_ms": elapsed_ms,
                    "elapsed_ms_wall": elapsed_ms_wall,
                    "avg_elapsed_ms": elapsed_ms / count if count else 0.0,
                    "avg_elapsed_ms_wall": elapsed_ms_wall / count if count else 0.0,
                    "elapsed_ms_cuda_sync": elapsed_ms_cuda_sync,
                    "avg_elapsed_ms_cuda_sync": (
                        elapsed_ms_cuda_sync / cuda_sync_timing_count if cuda_sync_timing_count else 0.0
                    ),
                    "cuda_sync_wait_ms": cuda_sync_wait_ms,
                    "avg_cuda_sync_wait_ms": (
                        cuda_sync_wait_ms / cuda_sync_timing_count if cuda_sync_timing_count else 0.0
                    ),
                    "cuda_sync_timing_count": int(cuda_sync_timing_count),
                    "errors": int(summary["errors"]),
                }
            )

    print(f"events:  {events_path}")
    print(f"rows:    {event_rows_path}")
    print(f"summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
