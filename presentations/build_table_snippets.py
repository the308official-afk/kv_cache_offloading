#!/usr/bin/env python3
"""Build simple paste-ready HTML table snippets from the presentation CSV reports."""

from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path


BASE_CSS = """
<style>
.report-table-snippet {
  margin: 0;
  color: #334155;
  font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif;
}

.report-table-snippet table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: #ffffff;
  border: 1px solid #dbe4f0;
}

.report-table-snippet thead th {
  background: #f4f7fb;
  color: #334155;
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  padding: 8px 9px;
  border-bottom: 2px solid #d6deea;
}

.report-table-snippet td {
  color: #334155;
  font-size: 10px;
  line-height: 1.28;
  padding: 7px 8px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
  word-break: break-word;
}

.report-table-snippet tbody tr:nth-child(even) td {
  background: #fbfdff;
}

.report-table-snippet .mono {
  font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
}

.report-table-snippet .patch-row td {
  background: #f0fdf4 !important;
}

.report-table-snippet .patch-row td:first-child {
  box-shadow: inset 3px 0 0 #16a34a;
}

.report-table-snippet .patch-good {
  color: #047857;
  font-weight: 700;
}

.report-table-snippet .patch-zero {
  color: #64748b;
  font-weight: 600;
}

.report-table-snippet.task-summary th:nth-child(1),
.report-table-snippet.task-summary td:nth-child(1) { width: 8%; }
.report-table-snippet.task-summary th:nth-child(2),
.report-table-snippet.task-summary td:nth-child(2) { width: 11%; }
.report-table-snippet.task-summary th:nth-child(3),
.report-table-snippet.task-summary td:nth-child(3) { width: 44%; }
.report-table-snippet.task-summary th:nth-child(4),
.report-table-snippet.task-summary td:nth-child(4) { width: 18%; }
.report-table-snippet.task-summary th:nth-child(5),
.report-table-snippet.task-summary td:nth-child(5) { width: 8%; }
.report-table-snippet.task-summary th:nth-child(6),
.report-table-snippet.task-summary td:nth-child(6) { width: 11%; }

.report-table-snippet.run-overview th,
.report-table-snippet.run-overview td {
  font-size: 9.4px;
  line-height: 1.2;
  padding: 6px 7px;
}

.report-table-snippet.run-overview th:nth-child(1),
.report-table-snippet.run-overview td:nth-child(1) { width: 6%; }
.report-table-snippet.run-overview th:nth-child(2),
.report-table-snippet.run-overview td:nth-child(2) { width: 7%; }
.report-table-snippet.run-overview th:nth-child(3),
.report-table-snippet.run-overview td:nth-child(3) { width: 11%; }
.report-table-snippet.run-overview th:nth-child(4),
.report-table-snippet.run-overview td:nth-child(4) { width: 5%; }
.report-table-snippet.run-overview th:nth-child(5),
.report-table-snippet.run-overview td:nth-child(5) { width: 11%; }
.report-table-snippet.run-overview th:nth-child(6),
.report-table-snippet.run-overview td:nth-child(6) { width: 11%; }
.report-table-snippet.run-overview th:nth-child(7),
.report-table-snippet.run-overview td:nth-child(7) { width: 7%; }
.report-table-snippet.run-overview th:nth-child(8),
.report-table-snippet.run-overview td:nth-child(8) { width: 10%; }
.report-table-snippet.run-overview th:nth-child(9),
.report-table-snippet.run-overview td:nth-child(9) { width: 8%; }
.report-table-snippet.run-overview th:nth-child(10),
.report-table-snippet.run-overview td:nth-child(10) { width: 8%; }
.report-table-snippet.run-overview th:nth-child(11),
.report-table-snippet.run-overview td:nth-child(11) { width: 5%; }
.report-table-snippet.run-overview th:nth-child(12),
.report-table-snippet.run-overview td:nth-child(12) { width: 11%; }
</style>
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert the task-summary and run-overview CSV reports into simple paste-ready HTML snippets."
    )
    parser.add_argument("--task-summary-csv", type=Path, required=True, help="Path to exp6_prompt_evolution_task_summary.csv.")
    parser.add_argument("--run-overview-csv", type=Path, required=True, help="Path to exp6_prompt_evolution_run_overview.csv.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory where the snippet HTML files will be written.")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def html_text(value: object) -> str:
    return html.escape("" if value is None else str(value))


def patch_nonempty(value: str) -> bool:
    cleaned = (value or "").strip().lower()
    return cleaned not in {"", "0", "0 b", "0 bytes", "0 byte"}


def cell_classes(header: str, value: str, table_kind: str) -> str:
    classes: list[str] = []
    if header in {"Run", "Repo", "Model", "Base Commit"}:
        classes.append("mono")
    if header == "Patch":
        classes.append("patch-good" if patch_nonempty(value) else "patch-zero")
    if table_kind == "run-overview" and header in {"Planning", "Execution", "Exec Size Δ", "Patch Gen", "Review", "Other"}:
        classes.append("mono")
    return " ".join(classes)


def render_table(rows: list[dict[str, str]], table_kind: str) -> str:
    if not rows:
        raise SystemExit(f"No rows found for {table_kind}.")

    headers = list(rows[0].keys())
    thead = "\n".join(f"        <th>{html_text(header)}</th>" for header in headers)

    body_rows: list[str] = []
    for row in rows:
        row_class = ' class="patch-row"' if patch_nonempty(row.get("Patch", "")) else ""
        cells = []
        for header in headers:
            value = row.get(header, "")
            classes = cell_classes(header, value, table_kind)
            class_attr = f' class="{classes}"' if classes else ""
            cells.append(f"        <td{class_attr}>{html_text(value)}</td>")
        body_rows.append("      <tr" + row_class + ">\n" + "\n".join(cells) + "\n      </tr>")

    return (
        f"{BASE_CSS}\n"
        f'<div class="report-table-snippet {table_kind}">\n'
        "  <table>\n"
        "    <thead>\n"
        "      <tr>\n"
        f"{thead}\n"
        "      </tr>\n"
        "    </thead>\n"
        "    <tbody>\n"
        f"{chr(10).join(body_rows)}\n"
        "    </tbody>\n"
        "  </table>\n"
        "</div>\n"
    )


def write_snippet(input_csv: Path, rows: list[dict[str, str]], table_kind: str, output_dir: Path) -> Path:
    output_path = output_dir / f"{input_csv.stem}.snippet.html"
    output_path.write_text(render_table(rows, table_kind), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    task_rows = read_csv(args.task_summary_csv)
    run_rows = read_csv(args.run_overview_csv)

    task_out = write_snippet(args.task_summary_csv, task_rows, "task-summary", output_dir)
    run_out = write_snippet(args.run_overview_csv, run_rows, "run-overview", output_dir)

    print(f"task_summary_snippet={task_out}")
    print(f"run_overview_snippet={run_out}")


if __name__ == "__main__":
    main()
