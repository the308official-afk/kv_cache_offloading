#!/usr/bin/env python3
"""Parse SGLang transfer JSON logs into JSONL and summary CSV outputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


PREFIX = "[SGLANG_TRANSFER_JSON] "


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
    summary_path = args.out_dir / "transfer_summary.csv"

    summaries: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {
            "count": 0,
            "num_bytes_observed": 0,
            "elapsed_ms": 0.0,
            "errors": 0,
        }
    )

    with events_path.open("w", encoding="utf-8") as event_out:
        for input_path in args.inputs:
            for event in iter_events(input_path):
                event_out.write(json.dumps(event, sort_keys=True, default=str) + "\n")
                if event.get("event") != "sglang.transfer":
                    continue
                key = (str(event.get("function", "")), str(event.get("direction", "")))
                summary = summaries[key]
                summary["count"] += 1
                summary["num_bytes_observed"] += float(event.get("num_bytes_observed") or 0)
                summary["elapsed_ms"] += float(event.get("elapsed_ms") or 0)
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
                "elapsed_ms",
                "avg_elapsed_ms",
                "errors",
            ],
        )
        writer.writeheader()
        for (function, direction), summary in sorted(summaries.items()):
            count = summary["count"]
            elapsed_ms = summary["elapsed_ms"]
            bytes_observed = summary["num_bytes_observed"]
            writer.writerow(
                {
                    "function": function,
                    "direction": direction,
                    "count": int(count),
                    "num_bytes_observed": int(bytes_observed),
                    "num_kb_observed": bytes_observed / 1024.0,
                    "num_mb_observed": bytes_observed / (1024.0 * 1024.0),
                    "elapsed_ms": elapsed_ms,
                    "avg_elapsed_ms": elapsed_ms / count if count else 0.0,
                    "errors": int(summary["errors"]),
                }
            )

    print(f"events:  {events_path}")
    print(f"summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
