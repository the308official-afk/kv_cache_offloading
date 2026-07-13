#!/usr/bin/env python3
"""Build normalized real-task request units from finished SWE-bench runs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


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


def fallback_trace_rows() -> list[dict[str, str]]:
    root = repo_root()
    overview_csv = root / "experiments/reports/all_runs_overview.csv"
    rows = read_csv_rows(overview_csv)
    fallback_rows: list[dict[str, str]] = []
    for row in rows:
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        fallback_rows.append(
            {
                "task_index": row.get("task_index", ""),
                "run_id": run_id,
                "repo": row.get("repo", ""),
                "model": row.get("model", ""),
                "hint_profile": row.get("hint_profile", ""),
                "result_dir": str(root / "experiments/raw/agentbench/results" / run_id),
                "report_dir": str(root / "experiments/reports/runs" / run_id),
            }
        )
    return fallback_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def copy_text(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def short_list(items: list[str]) -> str:
    if not items:
        return ""
    unique: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return "|".join(unique)


def phase_group(phase: str) -> str:
    value = (phase or "").strip().lower()
    if value == "planning":
        return "plan"
    if value in {"execution", "execution_retry"}:
        return "act"
    if value == "patch_generation":
        return "patch"
    if value == "review":
        return "review"
    return "other"


def request_kind(phase: str, tool_call_count: int) -> str:
    group = phase_group(phase)
    if group == "plan":
        return "plan_request"
    if group == "review":
        return "review_request"
    if group == "patch":
        return "patch_request"
    if tool_call_count > 0:
        return "tool_using_request"
    return "plain_request"


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


def bool_label(value: bool) -> str:
    return "yes" if value else "no"


def build_unit_rows(trace_rows: list[dict[str, str]], out_dir: Path) -> list[dict[str, Any]]:
    value_dir = out_dir / "request_unit_values"
    value_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for trace_row in trace_rows:
        run_id = trace_row.get("run_id", "").strip()
        if not run_id:
            continue
        result_dir = Path(trace_row.get("result_dir", "")).expanduser()
        report_dir = Path(trace_row.get("report_dir", "")).expanduser()
        result_payload = load_json(result_dir / "others" / "result.json", {})
        task = result_payload.get("task") or {}
        task_result = result_payload.get("result") or {}
        phase_results = task_result.get("phase_results") or []
        workspace_patch = result_dir / "workspace.patch"
        patch_nonempty = workspace_patch.exists() and workspace_patch.stat().st_size > 0

        for item in phase_results:
            phase = str(item.get("phase") or "").strip()
            request_context = item.get("request_context") or {}
            measurement = item.get("measurement") or {}
            execution_guard = item.get("execution_guard") or {}
            tool_call_details = item.get("tool_call_details") or []
            hints = item.get("hints") or {}
            prompt_text = str(item.get("prompt") or "")
            response_text = str(item.get("response_text") or "")
            tool_names = [
                str(detail.get("tool_name") or "").strip()
                for detail in tool_call_details
                if str(detail.get("tool_name") or "").strip()
            ]

            sequence_index = to_int(item.get("sequence_index"), default=0)
            phase_attempt = to_int(execution_guard.get("attempt_index"), default=sequence_index)
            step_index = to_int(request_context.get("step_index"), default=sequence_index)
            unit_id = f"{run_id}__{phase or 'unknown'}__step{step_index}__attempt{phase_attempt}"

            prompt_hash = text_hash(prompt_text)
            prompt_path = value_dir / f"{unit_id}__prompt.txt"
            prompt_path.write_text(prompt_text, encoding="utf-8")

            unit_payload = {
                "request_unit_id": unit_id,
                "run_id": run_id,
                "task_index": trace_row.get("task_index", ""),
                "repo": task.get("repo", ""),
                "instance_id": task.get("instance_id", ""),
                "phase": phase,
                "sequence_index": sequence_index,
                "phase_attempt": phase_attempt,
                "step_index": step_index,
                "step_title": request_context.get("step_title", ""),
                "request_context": request_context,
                "hints": hints,
                "measurement": measurement,
                "tool_call_details": tool_call_details,
                "execution_guard": execution_guard,
                "prompt_text": prompt_text,
                "response_text": response_text,
                "selected_test_files_to_run": task.get("selected_test_files_to_run", ""),
            }
            unit_json_path = value_dir / f"{unit_id}.json"
            unit_json_path.write_text(json.dumps(unit_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            prompt_tokens = to_int(measurement.get("prompt_tokens"))
            latency_ms = to_float(measurement.get("latency_ms"))
            tool_call_count = len(tool_call_details)
            group = phase_group(phase)
            row = {
                "request_unit_id": unit_id,
                "task_index": trace_row.get("task_index", ""),
                "run_id": run_id,
                "repo": task.get("repo", ""),
                "instance_id": task.get("instance_id", ""),
                "model": result_payload.get("model", ""),
                "app_variant": result_payload.get("app_variant", ""),
                "hint_profile": result_payload.get("hint_profile", ""),
                "hint_provider": result_payload.get("hint_provider", ""),
                "phase": phase,
                "phase_group": group,
                "phase_attempt": phase_attempt,
                "sequence_index": sequence_index,
                "step_index": step_index,
                "step_title": request_context.get("step_title", ""),
                "request_id": request_context.get("request_id", ""),
                "parent_run_id": request_context.get("parent_run_id", ""),
                "request_family": task.get("instance_id", "") or run_id,
                "request_kind": request_kind(phase, tool_call_count),
                "prompt_hash": prompt_hash,
                "prompt_chars": len(prompt_text),
                "prompt_tokens": prompt_tokens,
                "cached_prompt_tokens": to_int(measurement.get("cached_prompt_tokens")),
                "completion_tokens": to_int(measurement.get("completion_tokens")),
                "latency_ms": f"{latency_ms:.3f}",
                "finish_reason": measurement.get("finish_reason", ""),
                "tool_call_count": tool_call_count,
                "observed_tool_names": short_list(tool_names),
                "workspace_patch_nonempty": bool_label(patch_nonempty),
                "selected_test_files_to_run": str(task.get("selected_test_files_to_run", "")),
                "request_unit_json": str(unit_json_path),
                "prompt_text_path": str(prompt_path),
                "source_result_dir": str(result_dir),
                "source_report_dir": str(report_dir),
                "suitable_for_exp9": bool_label(prompt_tokens >= 512 and group in {"plan", "act", "patch", "review"}),
                "suitable_for_exp11": bool_label(tool_call_count > 0 or latency_ms >= 1000.0),
                "suitable_for_exp12": bool_label(group in {"plan", "act", "patch"}),
            }
            rows.append(row)

    rows.sort(key=lambda row: (to_int(row.get("task_index", 0)), row.get("run_id", ""), to_int(row.get("sequence_index", 0))))
    return rows


def build_summary(rows: list[dict[str, Any]], latest_trace_index: Path) -> str:
    runs = {row["run_id"] for row in rows}
    repos = {row["repo"] for row in rows}
    phases = {row["phase"] for row in rows}
    exp9 = sum(1 for row in rows if row["suitable_for_exp9"] == "yes")
    exp11 = sum(1 for row in rows if row["suitable_for_exp11"] == "yes")
    exp12 = sum(1 for row in rows if row["suitable_for_exp12"] == "yes")
    lines = [
        "# SWE-bench Real Request Units",
        "",
        f"- request_units: `{len(rows)}`",
        f"- runs: `{len(runs)}`",
        f"- repos: `{len(repos)}`",
        f"- phases_seen: `{', '.join(sorted(phases))}`",
        f"- suitable_for_exp9: `{exp9}`",
        f"- suitable_for_exp11: `{exp11}`",
        f"- suitable_for_exp12: `{exp12}`",
        f"- source_trace_index: `{latest_trace_index}`",
        "",
        "Each row is one real SWE-bench phase request normalized into a reusable",
        "request unit for downstream experiments.",
        "",
        "Important columns:",
        "",
        "- `phase`: planning / execution / patch_generation / review",
        "- `prompt_text_path`: exact prompt text for this request unit",
        "- `request_unit_json`: structured payload with prompt, hints, context, and measurements",
        "- `suitable_for_exp9|11|12`: quick screening flags for downstream use",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace-index-csv",
        default="experiments/reports/latest_prompt_evolution_trace_index.csv",
        help="Trace index CSV from finished SWE-bench runs.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory where per-run request-unit artifacts should be written.",
    )
    parser.add_argument(
        "--latest-csv",
        default="experiments/reports/latest_swebench_real_request_units.csv",
        help="Top-level latest request-units CSV.",
    )
    parser.add_argument(
        "--latest-summary-md",
        default="experiments/reports/latest_swebench_real_request_units_summary.md",
        help="Top-level latest summary markdown.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    trace_index_csv = Path(args.trace_index_csv)
    out_dir = Path(args.out_dir)
    latest_csv = Path(args.latest_csv)
    latest_summary_md = Path(args.latest_summary_md)

    trace_rows = read_csv_rows(trace_index_csv)
    if not trace_rows:
        trace_rows = fallback_trace_rows()
    rows = build_unit_rows(trace_rows, out_dir)
    fieldnames = [
        "request_unit_id",
        "task_index",
        "run_id",
        "repo",
        "instance_id",
        "model",
        "app_variant",
        "hint_profile",
        "hint_provider",
        "phase",
        "phase_group",
        "phase_attempt",
        "sequence_index",
        "step_index",
        "step_title",
        "request_id",
        "parent_run_id",
        "request_family",
        "request_kind",
        "prompt_hash",
        "prompt_chars",
        "prompt_tokens",
        "cached_prompt_tokens",
        "completion_tokens",
        "latency_ms",
        "finish_reason",
        "tool_call_count",
        "observed_tool_names",
        "workspace_patch_nonempty",
        "selected_test_files_to_run",
        "request_unit_json",
        "prompt_text_path",
        "source_result_dir",
        "source_report_dir",
        "suitable_for_exp9",
        "suitable_for_exp11",
        "suitable_for_exp12",
    ]
    batch_csv = out_dir / "request_units.csv"
    batch_summary_md = out_dir / "request_units_summary.md"
    write_csv(batch_csv, rows, fieldnames)
    summary_text = build_summary(rows, trace_index_csv)
    batch_summary_md.write_text(summary_text, encoding="utf-8")
    copy_text(batch_csv, latest_csv)
    latest_summary_md.parent.mkdir(parents=True, exist_ok=True)
    latest_summary_md.write_text(summary_text, encoding="utf-8")

    print(f"request units csv: {batch_csv}")
    print(f"request units summary: {batch_summary_md}")
    print(f"latest request units csv: {latest_csv}")
    print(f"latest request units summary: {latest_summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
