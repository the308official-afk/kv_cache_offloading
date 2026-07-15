#!/usr/bin/env python3
"""Generate slide-ready HTML table fragments for task-summary and run-overview slides."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from pathlib import Path
from typing import Iterable


TABLE_CSS = """
.generated-reference-block {
  margin: 0;
  color: #334155;
  font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif;
}

.generated-reference-block .table-context-line {
  font-size: 13px;
  line-height: 1.35;
  color: #334155;
  margin: 0 0 8px 0;
  font-weight: 600;
}

.generated-reference-block .table-context-line .label {
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 11px;
  font-weight: 700;
  margin-right: 6px;
}

.generated-reference-block .mono {
  font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
}

.generated-reference-block .table-wrap {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.generated-reference-block table.compact {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
}

.generated-reference-block table.compact th {
  background-color: #f1f5f9;
  text-align: left;
  padding: 9px 10px;
  font-weight: 700;
  border-bottom: 2px solid #cbd5e1;
  font-size: 11px;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  line-height: 1.2;
}

.generated-reference-block table.compact td {
  padding: 8px 10px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 11px;
  color: #334155;
  vertical-align: top;
  line-height: 1.35;
  word-break: break-word;
}

.generated-reference-block table.compact tr:nth-child(even) td {
  background-color: #fbfdff;
}

.generated-reference-block .repo-cell,
.generated-reference-block .run-cell,
.generated-reference-block .commit-cell,
.generated-reference-block .model-cell {
  font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
  font-size: 10.5px;
}

.generated-reference-block .task-cell {
  color: #1e293b;
  font-weight: 500;
}

.generated-reference-block .action-pill,
.generated-reference-block .yes-pill,
.generated-reference-block .no-pill {
  display: inline-block;
  border-radius: 999px;
  line-height: 1.25;
  white-space: normal;
}

.generated-reference-block .action-pill {
  padding: 4px 7px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 10px;
  font-weight: 700;
}

.generated-reference-block .yes-pill {
  padding: 4px 7px;
  background: #ecfdf5;
  color: #047857;
  font-size: 10px;
  font-weight: 800;
}

.generated-reference-block .no-pill {
  padding: 4px 7px;
  background: #f8fafc;
  color: #64748b;
  font-size: 10px;
  font-weight: 800;
}

.generated-reference-block .phase-cell {
  font-size: 10.5px;
  color: #334155;
}

.generated-reference-block .patch-good {
  color: #047857;
  font-weight: 800;
}

.generated-reference-block .patch-zero {
  color: #64748b;
  font-weight: 700;
}

.generated-reference-block table.compact.tight th {
  font-size: 10px;
  padding: 7px 8px;
  line-height: 1.15;
}

.generated-reference-block table.compact.tight td {
  font-size: 10px;
  padding: 7px 8px;
  line-height: 1.25;
}

.generated-reference-block table.compact.tight .repo-cell,
.generated-reference-block table.compact.tight .run-cell,
.generated-reference-block table.compact.tight .commit-cell,
.generated-reference-block table.compact.tight .model-cell {
  font-size: 10px;
}

.generated-reference-block table.compact.tight .phase-cell {
  font-size: 9.5px;
  line-height: 1.2;
}

.generated-reference-block table.compact.task-tall td {
  padding: 11px 9px;
  vertical-align: top;
}

.generated-reference-block table.compact.task-tall .task-cell {
  line-height: 1.35;
  font-size: 12px;
}

.generated-reference-block table.compact.task-tall th {
  font-size: 11px;
  padding: 8px 9px;
}

.generated-reference-block table.compact.task-tall .run-cell,
.generated-reference-block table.compact.task-tall .repo-cell,
.generated-reference-block table.compact.task-tall .commit-cell {
  font-size: 11.5px;
}

.generated-reference-block table.compact.task-tall .action-pill,
.generated-reference-block table.compact.task-tall .yes-pill,
.generated-reference-block table.compact.task-tall .no-pill {
  font-size: 10.5px;
  padding: 4px 7px;
}

.generated-reference-block table.compact.task-merge td {
  padding: 8px 8px;
  vertical-align: top;
}

.generated-reference-block table.compact.task-merge .task-cell {
  line-height: 1.28;
  font-size: 10.8px;
}

.generated-reference-block table.compact.task-merge th {
  font-size: 10px;
  padding: 7px 8px;
}

.generated-reference-block table.compact.task-merge .run-cell,
.generated-reference-block table.compact.task-merge .repo-cell,
.generated-reference-block table.compact.task-merge .commit-cell {
  font-size: 10.4px;
}

.generated-reference-block table.compact.task-merge .action-pill,
.generated-reference-block table.compact.task-merge .yes-pill,
.generated-reference-block table.compact.task-merge .no-pill {
  font-size: 9.6px;
  padding: 3px 6px;
  line-height: 1.2;
}

.generated-reference-block .patch-row td {
  background-color: #f0fdf4 !important;
}

.generated-reference-block .patch-row td:first-child {
  box-shadow: inset 3px 0 0 #16a34a;
}

.generated-reference-block .footline {
  margin-top: 8px;
  text-align: right;
  color: #64748b;
  font-size: 12px;
  line-height: 1.3;
}
""".strip()


PREVIEW_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Generated Reference Tables</title>
    <style>
      body {{
        margin: 0;
        padding: 32px;
        background: #f8fafc;
        color: #0f172a;
        font-family: 'IBM Plex Sans', Arial, sans-serif;
      }}
      .preview-slide {{
        width: 1280px;
        margin: 0 auto 28px auto;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        box-shadow: 0 16px 50px rgba(15, 23, 42, 0.08);
        padding: 36px 42px;
      }}
      .preview-title {{
        margin: 0 0 14px 0;
        font-size: 30px;
        line-height: 1.1;
        font-weight: 700;
        color: #0f172a;
      }}
      .preview-note {{
        margin: 0 0 20px 0;
        font-size: 14px;
        color: #475569;
      }}
      {css}
    </style>
  </head>
  <body>
    <section class="preview-slide">
      <h1 class="preview-title">Slide 9: Task Summary</h1>
      <p class="preview-note">Generated fragment preview</p>
      {task_html}
    </section>
    <section class="preview-slide">
      <h1 class="preview-title">Slide 10: Run Overview</h1>
      <p class="preview-note">Generated fragment preview</p>
      {run_html}
    </section>
  </body>
</html>
"""


JS_TEMPLATE = """window.{global_name} = {payload};\n"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate slide-ready HTML table fragments for task-summary and run-overview slides."
    )
    parser.add_argument("--task-summary-csv", type=Path, required=True, help="Path to the task-summary CSV.")
    parser.add_argument("--run-overview-csv", type=Path, required=True, help="Path to the run-overview CSV.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory where the HTML fragments and preview will be written. Defaults to the script directory.",
    )
    parser.add_argument("--benchmark", default="SWE-bench", help="Benchmark label shown above each table.")
    parser.add_argument("--model-label", default="", help="Optional fixed model label shown above each table.")
    parser.add_argument("--harness", default="Deepagents", help="Harness label shown above each table.")
    parser.add_argument("--task-summary-start-row", type=int, default=1, help="1-based start row for slide 9.")
    parser.add_argument("--task-summary-max-rows", type=int, default=14, help="Max rows for slide 9.")
    parser.add_argument("--run-overview-start-row", type=int, default=1, help="1-based start row for slide 10.")
    parser.add_argument("--run-overview-max-rows", type=int, default=14, help="Max rows for slide 10.")
    parser.add_argument(
        "--max-tools-per-cell",
        type=int,
        default=4,
        help="Maximum number of tool names shown inside each run-overview phase cell.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def html_text(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def boolish(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def first_present(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return str(row.get(key, ""))
    return ""


def repo_short(value: str) -> str:
    cleaned = (value or "").strip()
    if "/" in cleaned:
        parts = [part for part in cleaned.split("/") if part]
        if len(parts) >= 2 and parts[0] == parts[1]:
            return parts[0]
        return parts[-1]
    return cleaned


def run_short(row: dict[str, str]) -> str:
    if row.get("run_short"):
        return row["run_short"]
    run_id = row.get("run_id", "")
    match = re.search(r"(\d{6})$", run_id)
    return match.group(1) if match else run_id


def commit_short(value: str) -> str:
    return (value or "").strip()[:8]


def compact_model(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    base = cleaned.split("/")[-1]
    match = re.match(r"([A-Za-z]+)(\d+(?:\.\d+)?)", base)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    base = re.sub(r"-(Coder|Instruct|FP8|A3B).*$", "", base)
    return base.replace("-", " ")


def model_label_for_rows(rows: Iterable[dict[str, str]], override: str) -> str:
    if override:
        return override
    for row in rows:
        model = first_present(row, "model", "Model").strip()
        if model:
            return model
    return ""


TOOL_MAP = {
    "read_file": "read",
    "write_file": "write",
    "edit_file": "edit",
    "execute": "exec",
    "write_todos": "todos",
    "bash": "shell",
    "list_files": "ls",
    "search_files": "search",
    "grep_search": "grep",
    "apply_patch": "patch",
    "none": "--",
}


def compact_tools(value: str, max_items: int) -> str:
    items = [item.strip() for item in (value or "").split(",") if item.strip()]
    if not items:
        return "--"
    compacted = []
    for item in items:
        compacted.append(TOOL_MAP.get(item, item.replace("_", " ")))
    unique_items = []
    for item in compacted:
        if item not in unique_items:
            unique_items.append(item)
    shown = unique_items[:max_items]
    return ", ".join(shown)


def format_bytes_compact(raw_bytes: str, fallback_label: str) -> str:
    try:
        value = int(float(raw_bytes))
    except (TypeError, ValueError):
        cleaned = (fallback_label or "").strip()
        return cleaned or "--"
    if value <= 0:
        return "0 B"
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        amount = value / 1024
        return f"{amount:.1f} KB".replace(".0 ", " ")
    amount = value / (1024 * 1024)
    return f"{amount:.1f} MB".replace(".0 ", " ")


def context_line(benchmark: str, model_label: str, harness: str) -> str:
    return (
        '<div class="table-context-line">'
        f'<span class="label">Benchmark</span> {html_text(benchmark)} '
        '<span class="mono" style="margin: 0 14px;">&middot;</span> '
        f'<span class="label">Model</span> <span class="mono">{html_text(model_label)}</span> '
        '<span class="mono" style="margin: 0 14px;">&middot;</span> '
        f'<span class="label">Harness</span> {html_text(harness)}'
        "</div>"
    )


def phase_cell(row: dict[str, str], count_key: str, tools_key: str, max_items: int) -> str:
    count = (row.get(count_key) or "0").strip() or "0"
    tools = compact_tools(row.get(tools_key, ""), max_items)
    return f"{html_text(count)} &middot; {html_text(tools)}"


def is_task_summary_chart_schema(rows: list[dict[str, str]]) -> bool:
    return bool(rows) and "Task Summary" in rows[0]


def is_run_overview_chart_schema(rows: list[dict[str, str]]) -> bool:
    return bool(rows) and "Planning" in rows[0] and "Execution" in rows[0] and "Patch Gen" in rows[0]


def patch_nonempty_from_text(value: str) -> bool:
    cleaned = (value or "").strip().lower()
    return cleaned not in {"", "0 b", "0 bytes", "0 byte", "0"}


def slice_rows(rows: list[dict[str, str]], start_row: int, max_rows: int) -> tuple[list[dict[str, str]], int, int, int]:
    if start_row < 1:
        raise SystemExit("Start rows must be 1-based and >= 1.")
    if max_rows < 1:
        raise SystemExit("Max rows must be >= 1.")
    start_index = start_row - 1
    end_index = min(start_index + max_rows, len(rows))
    return rows[start_index:end_index], start_row, end_index, len(rows)


def task_summary_fragment(
    rows: list[dict[str, str]],
    benchmark: str,
    model_label: str,
    harness: str,
    start_row: int,
    max_rows: int,
) -> str:
    sliced_rows, row_start, row_end, total = slice_rows(rows, start_row, max_rows)
    body_rows = []
    chart_schema = is_task_summary_chart_schema(rows)
    for row in sliced_rows:
        patch_expected = boolish(first_present(row, "patch_expected", "Patch"))
        patch_pill = '<span class="yes-pill">Yes</span>' if patch_expected else '<span class="no-pill">No</span>'
        body_rows.append(
            "      <tr>\n"
            f'        <td class="run-cell">{html_text(first_present(row, "run_short", "Run") or run_short(row))}</td>\n'
            f'        <td class="repo-cell">{html_text(repo_short(first_present(row, "repo", "Repo")))}</td>\n'
            f'        <td class="task-cell">{html_text(first_present(row, "problem_statement_summary", "Task Summary"))}</td>\n'
            f'        <td><span class="action-pill">{html_text(first_present(row, "expected_agent_action", "Expected Action"))}</span></td>\n'
            f"        <td>{patch_pill}</td>\n"
            f'        <td class="commit-cell">{html_text(commit_short(first_present(row, "base_commit", "Base Commit")))}</td>\n'
            "      </tr>"
        )
    table_html = "\n".join(body_rows)
    return (
        '<div class="generated-reference-block generated-task-summary-block">\n'
        f"  {context_line(benchmark, model_label, harness)}\n"
        '  <div class="table-wrap">\n'
        '    <table class="compact tight task-tall task-merge">\n'
        "      <colgroup>\n"
        '        <col style="width:8%">\n'
        '        <col style="width:11%">\n'
        '        <col style="width:46%">\n'
        '        <col style="width:18%">\n'
        '        <col style="width:7%">\n'
        '        <col style="width:10%">\n'
        "      </colgroup>\n"
        "      <thead>\n"
        "        <tr>\n"
        "          <th>Run</th>\n"
        "          <th>Repo</th>\n"
        "          <th>Task Summary</th>\n"
        "          <th>Expected Action</th>\n"
        "          <th>Patch</th>\n"
        "          <th>Base Commit</th>\n"
        "        </tr>\n"
        "      </thead>\n"
        "      <tbody>\n"
        f"{table_html}\n"
        "      </tbody>\n"
        "    </table>\n"
        "  </div>\n"
        f'  <div class="footline mono">Rows {row_start}-{row_end} of {total}</div>\n'
        "</div>\n"
    )


def run_overview_fragment(
    rows: list[dict[str, str]],
    benchmark: str,
    model_label: str,
    harness: str,
    start_row: int,
    max_rows: int,
    max_tools_per_cell: int,
) -> str:
    sliced_rows, row_start, row_end, total = slice_rows(rows, start_row, max_rows)
    body_rows = []
    chart_schema = is_run_overview_chart_schema(rows)
    for row in sliced_rows:
        if chart_schema:
            patch_text = first_present(row, "Patch")
            patch_nonempty = patch_nonempty_from_text(patch_text)
            run_text = first_present(row, "Run")
            repo_text = first_present(row, "Repo")
            model_text = first_present(row, "Model")
            steps_text = first_present(row, "Steps")
            planning_text = first_present(row, "Planning")
            execution_text = first_present(row, "Execution")
            patch_gen_text = first_present(row, "Patch Gen")
            review_text = first_present(row, "Review")
            other_text = first_present(row, "Other")
            total_text = first_present(row, "Total")
        else:
            patch_nonempty = boolish(row.get("patch_nonempty")) or boolish(row.get("git_diff_nonempty"))
            patch_text = format_bytes_compact(row.get("patch_bytes", ""), row.get("patch", ""))
            run_text = run_short(row)
            repo_text = repo_short(row.get("repo", ""))
            model_text = compact_model(row.get("model", ""))
            steps_text = row.get("execution_steps", "")
            planning_text = phase_cell(row, "planning_tool_calls", "planning_tools", max_tools_per_cell)
            execution_text = phase_cell(row, "execution_phase_tool_calls", "execution_phase_tools", max_tools_per_cell)
            patch_gen_text = phase_cell(row, "patch_generation_tool_calls", "patch_generation_tools", max_tools_per_cell)
            review_text = phase_cell(row, "review_tool_calls", "review_tools", max_tools_per_cell)
            other_text = phase_cell(row, "other_phase_tool_calls", "other_phase_tools", max_tools_per_cell)
            total_text = row.get("total_tool_calls", "")
        patch_class = "patch-good" if patch_nonempty else "patch-zero"
        row_class = ' class="patch-row"' if patch_nonempty else ""
        body_rows.append(
            f"      <tr{row_class}>\n"
            f'        <td class="run-cell">{html_text(run_text)}</td>\n'
            f'        <td class="repo-cell">{html_text(repo_text)}</td>\n'
            f'        <td class="model-cell">{html_text(model_text)}</td>\n'
            f'        <td class="run-cell">{html_text(steps_text)}</td>\n'
            f'        <td class="phase-cell">{html_text(planning_text)}</td>\n'
            f'        <td class="phase-cell">{html_text(execution_text)}</td>\n'
            f'        <td class="phase-cell">{html_text(patch_gen_text)}</td>\n'
            f'        <td class="phase-cell">{html_text(review_text)}</td>\n'
            f'        <td class="phase-cell">{html_text(other_text)}</td>\n'
            f'        <td class="run-cell">{html_text(total_text)}</td>\n'
            f'        <td><span class="{patch_class}">{html_text(patch_text)}</span></td>\n'
            "      </tr>"
        )
    table_html = "\n".join(body_rows)
    return (
        '<div class="generated-reference-block generated-run-overview-block">\n'
        f"  {context_line(benchmark, model_label, harness)}\n"
        '  <div class="table-wrap">\n'
        '    <table class="compact tight">\n'
        "      <colgroup>\n"
        '        <col style="width:7%">\n'
        '        <col style="width:8%">\n'
        '        <col style="width:8%">\n'
        '        <col style="width:5%">\n'
        '        <col style="width:9%">\n'
        '        <col style="width:15%">\n'
        '        <col style="width:12%">\n'
        '        <col style="width:10%">\n'
        '        <col style="width:11%">\n'
        '        <col style="width:5%">\n'
        '        <col style="width:10%">\n'
        "      </colgroup>\n"
        "      <thead>\n"
        "        <tr>\n"
        "          <th>Run</th>\n"
        "          <th>Repo</th>\n"
        "          <th>Model</th>\n"
        "          <th>Steps</th>\n"
        "          <th>Planning</th>\n"
        "          <th>Execution</th>\n"
        "          <th>Patch Gen</th>\n"
        "          <th>Review</th>\n"
        "          <th>Other</th>\n"
        "          <th>Total</th>\n"
        "          <th>Patch</th>\n"
        "        </tr>\n"
        "      </thead>\n"
        "      <tbody>\n"
        f"{table_html}\n"
        "      </tbody>\n"
        "    </table>\n"
        "  </div>\n"
        f'  <div class="footline mono">Rows {row_start}-{row_end} of {total} | phase cells show tool-call count and dominant tools</div>\n'
        "</div>\n"
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fragment_document(content: str) -> str:
    return f"<style>\n{TABLE_CSS}\n</style>\n{content}"


def fragment_script(global_name: str, content: str) -> str:
    return JS_TEMPLATE.format(global_name=global_name, payload=json.dumps(content))


def main() -> None:
    args = parse_args()
    task_rows = read_rows(args.task_summary_csv)
    run_rows = read_rows(args.run_overview_csv)
    if not task_rows:
        raise SystemExit(f"No rows found in {args.task_summary_csv}")
    if not run_rows:
        raise SystemExit(f"No rows found in {args.run_overview_csv}")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    task_model_label = model_label_for_rows(task_rows, args.model_label)
    run_model_label = model_label_for_rows(run_rows, args.model_label)

    task_fragment = task_summary_fragment(
        rows=task_rows,
        benchmark=args.benchmark,
        model_label=task_model_label,
        harness=args.harness,
        start_row=args.task_summary_start_row,
        max_rows=args.task_summary_max_rows,
    )
    run_fragment = run_overview_fragment(
        rows=run_rows,
        benchmark=args.benchmark,
        model_label=run_model_label,
        harness=args.harness,
        start_row=args.run_overview_start_row,
        max_rows=args.run_overview_max_rows,
        max_tools_per_cell=args.max_tools_per_cell,
    )

    css_path = output_dir / "reference_tables.css"
    task_path = output_dir / "slide9_task_summary_fragment.html"
    run_path = output_dir / "slide10_run_overview_fragment.html"
    task_js_path = output_dir / "slide9_task_summary_fragment.js"
    run_js_path = output_dir / "slide10_run_overview_fragment.js"
    preview_path = output_dir / "reference_tables_preview.html"
    manifest_path = output_dir / "reference_tables_manifest.json"

    write_text(css_path, TABLE_CSS + "\n")
    write_text(task_path, fragment_document(task_fragment))
    write_text(run_path, fragment_document(run_fragment))
    write_text(task_js_path, fragment_script("SLIDE9_TASK_SUMMARY_FRAGMENT", task_fragment))
    write_text(run_js_path, fragment_script("SLIDE10_RUN_OVERVIEW_FRAGMENT", run_fragment))
    write_text(
        preview_path,
        PREVIEW_HTML.format(css=TABLE_CSS, task_html=task_fragment, run_html=run_fragment),
    )

    manifest = {
        "task_summary_csv": str(args.task_summary_csv),
        "run_overview_csv": str(args.run_overview_csv),
            "css": str(css_path),
            "task_summary_fragment": str(task_path),
            "run_overview_fragment": str(run_path),
            "task_summary_script": str(task_js_path),
            "run_overview_script": str(run_js_path),
            "preview_html": str(preview_path),
            "options": {
                "benchmark": args.benchmark,
            "task_summary_model_label": task_model_label,
            "run_overview_model_label": run_model_label,
            "harness": args.harness,
            "task_summary_start_row": args.task_summary_start_row,
            "task_summary_max_rows": args.task_summary_max_rows,
            "run_overview_start_row": args.run_overview_start_row,
            "run_overview_max_rows": args.run_overview_max_rows,
            "max_tools_per_cell": args.max_tools_per_cell,
        },
    }
    write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")

    print(f"css={css_path}")
    print(f"slide9={task_path}")
    print(f"slide10={run_path}")
    print(f"slide9_js={task_js_path}")
    print(f"slide10_js={run_js_path}")
    print(f"preview={preview_path}")
    print(f"manifest={manifest_path}")


if __name__ == "__main__":
    main()
