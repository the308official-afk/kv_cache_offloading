#!/usr/bin/env python3
"""Build a replayable prompt catalog from SWE-bench prompt-evolution runs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRACE_INDEX = REPO_ROOT / "experiments" / "reports" / "latest_prompt_evolution_trace_index.csv"
DEFAULT_OUT_ROOT = REPO_ROOT / "experiments" / "reports" / "swebench_trajectory_prompts"
DEFAULT_LATEST_CSV = REPO_ROOT / "experiments" / "reports" / "latest_swebench_trajectory_prompt_catalog.csv"
DEFAULT_LATEST_JSONL = REPO_ROOT / "experiments" / "reports" / "latest_swebench_trajectory_prompt_catalog.jsonl"
DEFAULT_STAGE_FILTER = "planning execution patch_generation review"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read Experiment 6 prompt-evolution traces and build a prompt catalog "
            "that Experiment 9 can replay without running tools again."
        )
    )
    parser.add_argument(
        "--trace-index",
        default=os.environ.get("SWEBENCH_TRAJECTORY_TRACE_INDEX", str(DEFAULT_TRACE_INDEX)),
        help="Experiment 6 task trace index CSV.",
    )
    parser.add_argument(
        "--catalog-id",
        default=os.environ.get(
            "SWEBENCH_TRAJECTORY_CATALOG_ID",
            f"swebench_trajectory_prompts_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        ),
    )
    parser.add_argument(
        "--out-root",
        default=os.environ.get("SWEBENCH_TRAJECTORY_CATALOG_ROOT", str(DEFAULT_OUT_ROOT)),
    )
    parser.add_argument(
        "--latest-csv",
        default=os.environ.get("SWEBENCH_TRAJECTORY_LATEST_CSV", str(DEFAULT_LATEST_CSV)),
    )
    parser.add_argument(
        "--latest-jsonl",
        default=os.environ.get("SWEBENCH_TRAJECTORY_LATEST_JSONL", str(DEFAULT_LATEST_JSONL)),
    )
    parser.add_argument(
        "--stage-filter",
        default=os.environ.get("SWEBENCH_TRAJECTORY_STAGE_FILTER", DEFAULT_STAGE_FILTER),
        help=(
            "Whitespace-separated phase names to include. Use all to include every "
            "phase_result prompt found in others/result.json."
        ),
    )
    parser.add_argument(
        "--min-prompt-chars",
        type=int,
        default=int(os.environ.get("SWEBENCH_TRAJECTORY_MIN_PROMPT_CHARS", "200")),
        help="Skip phase prompts shorter than this many characters.",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=int(os.environ.get("SWEBENCH_TRAJECTORY_MAX_TASKS", "0")),
        help="Optional cap on trace-index rows. 0 means no cap.",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(
            f"Trace index not found: {path}\n"
            "Run Experiment 6 first, then rerun this preparer."
        )
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def normalize_stage_filter(value: str) -> set[str] | None:
    normalized = value.strip()
    if not normalized or normalized.lower() == "all":
        return None
    return {item.strip() for item in normalized.split() if item.strip()}


def stable_task_index(row: dict[str, str], fallback: int) -> int:
    raw = row.get("task_index") or ""
    try:
        return int(raw)
    except ValueError:
        return fallback


def prompt_from_phase_result(phase_result: dict[str, Any]) -> str:
    prompt = phase_result.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt
    messages = phase_result.get("messages")
    if isinstance(messages, list):
        parts = [
            str(message.get("content") or "")
            for message in messages
            if isinstance(message, dict) and message.get("content")
        ]
        joined = "\n\n".join(parts).strip()
        if joined:
            return joined
    return ""


def phase_result_context(phase_result: dict[str, Any]) -> dict[str, Any]:
    context = phase_result.get("request_context")
    if isinstance(context, dict):
        return context
    measurement = phase_result.get("measurement")
    if isinstance(measurement, dict) and isinstance(measurement.get("request_context"), dict):
        return measurement["request_context"]
    return {}


def catalog_rows_for_trace_row(
    *,
    trace_row: dict[str, str],
    task_index: int,
    stage_filter: set[str] | None,
    min_prompt_chars: int,
    prompt_dir: Path,
) -> list[dict[str, Any]]:
    result_dir = Path(trace_row.get("result_dir") or "")
    if not result_dir.is_absolute():
        result_dir = REPO_ROOT / result_dir
    result_json = result_dir / "others" / "result.json"
    if not result_json.exists():
        return []

    body = load_json(result_json)
    task = body.get("task") if isinstance(body.get("task"), dict) else {}
    result = body.get("result") if isinstance(body.get("result"), dict) else {}
    phase_results = result.get("phase_results")
    if not isinstance(phase_results, list):
        phase_results = body.get("step_results") if isinstance(body.get("step_results"), list) else []

    rows: list[dict[str, Any]] = []
    stage_seen: dict[str, int] = {}
    for raw_index, phase_result in enumerate(phase_results):
        if not isinstance(phase_result, dict):
            continue
        context = phase_result_context(phase_result)
        phase = str(context.get("phase") or phase_result.get("phase") or f"stage_{raw_index}")
        if stage_filter is not None and phase not in stage_filter:
            continue
        prompt = prompt_from_phase_result(phase_result)
        if len(prompt) < min_prompt_chars:
            continue

        stage_seen[phase] = stage_seen.get(phase, 0) + 1
        stage_ordinal = stage_seen[phase] - 1
        stage_name = phase if stage_ordinal == 0 else f"{phase}_{stage_ordinal}"
        instance_id = str(task.get("instance_id") or context.get("task_instance_id") or trace_row.get("run_id") or "")
        repo = str(task.get("repo") or trace_row.get("repo") or "")
        prompt_hash = short_hash(prompt)
        prompt_file = prompt_dir / f"task{task_index:04d}__{stage_name}__{prompt_hash}.txt"
        prompt_file.write_text(prompt, encoding="utf-8")

        rows.append(
            {
                "catalog_id": "",
                "task_index": task_index,
                "run_id": trace_row.get("run_id", ""),
                "repo": repo,
                "instance_id": instance_id,
                "stage_name": stage_name,
                "phase": phase,
                "stage_index": raw_index,
                "phase_ordinal": stage_ordinal,
                "request_id": context.get("request_id", ""),
                "step_title": context.get("step_title", ""),
                "prompt_hash": prompt_hash,
                "prompt_chars": len(prompt),
                "prompt_words": len(prompt.split()),
                "prompt_text_path": str(prompt_file),
                "source_result_json": str(result_json),
                "source_trace_index": "",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    trace_index = Path(args.trace_index)
    out_dir = Path(args.out_root) / args.catalog_id
    prompt_dir = out_dir / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)

    trace_rows = read_csv_rows(trace_index)
    if args.max_tasks > 0:
        trace_rows = trace_rows[: args.max_tasks]
    stage_filter = normalize_stage_filter(args.stage_filter)

    rows: list[dict[str, Any]] = []
    for fallback_index, trace_row in enumerate(trace_rows):
        task_index = stable_task_index(trace_row, fallback_index)
        rows.extend(
            catalog_rows_for_trace_row(
                trace_row=trace_row,
                task_index=task_index,
                stage_filter=stage_filter,
                min_prompt_chars=args.min_prompt_chars,
                prompt_dir=prompt_dir,
            )
        )

    if not rows:
        raise SystemExit(
            "No trajectory prompts were found. Run Experiment 6 first and make sure "
            "the trace index points to result directories with others/result.json."
        )

    for row in rows:
        row["catalog_id"] = args.catalog_id
        row["source_trace_index"] = str(trace_index)

    fieldnames = [
        "catalog_id",
        "task_index",
        "run_id",
        "repo",
        "instance_id",
        "stage_name",
        "phase",
        "stage_index",
        "phase_ordinal",
        "request_id",
        "step_title",
        "prompt_hash",
        "prompt_chars",
        "prompt_words",
        "prompt_text_path",
        "source_result_json",
        "source_trace_index",
    ]
    catalog_csv = out_dir / "swebench_trajectory_prompt_catalog.csv"
    catalog_jsonl = out_dir / "swebench_trajectory_prompt_catalog.jsonl"
    write_csv(catalog_csv, rows, fieldnames)
    write_jsonl(catalog_jsonl, rows)
    write_csv(Path(args.latest_csv), rows, fieldnames)
    write_jsonl(Path(args.latest_jsonl), rows)

    summary = {
        "catalog_id": args.catalog_id,
        "trace_index": str(trace_index),
        "catalog_csv": str(catalog_csv),
        "catalog_jsonl": str(catalog_jsonl),
        "latest_csv": str(args.latest_csv),
        "latest_jsonl": str(args.latest_jsonl),
        "task_count": len({row["task_index"] for row in rows}),
        "prompt_count": len(rows),
        "stage_filter": args.stage_filter,
        "min_prompt_chars": args.min_prompt_chars,
    }
    (out_dir / "catalog_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("SWE-bench trajectory prompt catalog ready.")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
