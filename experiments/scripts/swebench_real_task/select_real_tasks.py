#!/usr/bin/env python3
"""Summarize which real SWE-bench tasks are good candidates for Experiments 9, 11, and 12."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def short_join(values: list[str]) -> str:
    seen: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return "|".join(seen)


def build_task_rows(request_units: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in request_units:
        grouped[(row.get("run_id", ""), row.get("instance_id", ""))].append(row)

    task_rows: list[dict[str, Any]] = []
    for (run_id, instance_id), rows in grouped.items():
        rows.sort(key=lambda row: to_int(row.get("sequence_index", 0)))
        phases = [row.get("phase", "") for row in rows]
        phase_groups = [row.get("phase_group", "") for row in rows]
        tool_call_counts = [to_int(row.get("tool_call_count", 0)) for row in rows]
        latency_values = [to_float(row.get("latency_ms", 0.0)) for row in rows]
        prompt_tokens = [to_int(row.get("prompt_tokens", 0)) for row in rows]
        exp9_pairs = []
        exp12_pairs = []
        for left, right in zip(rows, rows[1:]):
            left_phase = left.get("phase", "")
            right_phase = right.get("phase", "")
            if left_phase and right_phase:
                exp9_pairs.append(f"{left_phase}->{right_phase}")
                if left.get("suitable_for_exp12") == "yes":
                    exp12_pairs.append(f"{left_phase}->{right_phase}")

        has_heavy = any(count >= 3 for count in tool_call_counts)
        has_light = any(count == 0 for count in tool_call_counts)
        task_rows.append(
            {
                "task_index": rows[0].get("task_index", ""),
                "run_id": run_id,
                "repo": rows[0].get("repo", ""),
                "instance_id": instance_id,
                "model": rows[0].get("model", ""),
                "hint_profile": rows[0].get("hint_profile", ""),
                "phase_count": len(rows),
                "phases_seen": short_join(phases),
                "phase_groups_seen": short_join(phase_groups),
                "tool_calls_total": sum(tool_call_counts),
                "max_tool_calls_in_one_phase": max(tool_call_counts) if tool_call_counts else 0,
                "max_prompt_tokens": max(prompt_tokens) if prompt_tokens else 0,
                "max_latency_ms": f"{max(latency_values):.3f}" if latency_values else "0.000",
                "exp9_candidate": "yes" if len(rows) >= 2 else "no",
                "exp11_candidate": "yes" if has_heavy and has_light else "no",
                "exp12_candidate": "yes" if len(exp12_pairs) >= 1 else "no",
                "exp9_phase_pairs": short_join(exp9_pairs),
                "exp12_phase_pairs": short_join(exp12_pairs),
                "request_units_csv_source": rows[0].get("source_result_dir", ""),
            }
        )

    task_rows.sort(key=lambda row: (to_int(row.get("task_index", 0)), row.get("run_id", "")))
    return task_rows


def build_summary(rows: list[dict[str, Any]], request_units_csv: Path) -> str:
    exp9 = sum(1 for row in rows if row["exp9_candidate"] == "yes")
    exp11 = sum(1 for row in rows if row["exp11_candidate"] == "yes")
    exp12 = sum(1 for row in rows if row["exp12_candidate"] == "yes")
    lines = [
        "# SWE-bench Real Task Selection",
        "",
        f"- tasks: `{len(rows)}`",
        f"- exp9_candidates: `{exp9}`",
        f"- exp11_candidates: `{exp11}`",
        f"- exp12_candidates: `{exp12}`",
        f"- source_request_units_csv: `{request_units_csv}`",
        "",
        "This table is the task-level screening view on top of the per-phase",
        "request units.",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-units-csv", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument(
        "--latest-csv",
        default="experiments/reports/latest_swebench_real_task_selection.csv",
    )
    parser.add_argument(
        "--latest-md",
        default="experiments/reports/latest_swebench_real_task_selection.md",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_units_csv = Path(args.request_units_csv)
    out_csv = Path(args.out_csv)
    out_md = Path(args.out_md)
    latest_csv = Path(args.latest_csv)
    latest_md = Path(args.latest_md)

    request_units = read_csv_rows(request_units_csv)
    rows = build_task_rows(request_units)
    fieldnames = [
        "task_index",
        "run_id",
        "repo",
        "instance_id",
        "model",
        "hint_profile",
        "phase_count",
        "phases_seen",
        "phase_groups_seen",
        "tool_calls_total",
        "max_tool_calls_in_one_phase",
        "max_prompt_tokens",
        "max_latency_ms",
        "exp9_candidate",
        "exp11_candidate",
        "exp12_candidate",
        "exp9_phase_pairs",
        "exp12_phase_pairs",
        "request_units_csv_source",
    ]
    write_csv(out_csv, rows, fieldnames)
    latest_csv.parent.mkdir(parents=True, exist_ok=True)
    latest_csv.write_text(out_csv.read_text(encoding="utf-8"), encoding="utf-8")
    summary_text = build_summary(rows, request_units_csv)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(summary_text, encoding="utf-8")
    latest_md.parent.mkdir(parents=True, exist_ok=True)
    latest_md.write_text(summary_text, encoding="utf-8")

    print(f"task selection csv: {out_csv}")
    print(f"task selection summary: {out_md}")
    print(f"latest task selection csv: {latest_csv}")
    print(f"latest task selection summary: {latest_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
