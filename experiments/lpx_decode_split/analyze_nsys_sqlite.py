#!/usr/bin/env python3

"""Classify Nsight Systems kernel time for GPU/LPU decode-split analysis."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
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


def duration_ns_from_row(row: sqlite3.Row, cols: list[str]) -> int | None:
    for col in ("duration", "Duration", "durationNs", "dur"):
        if col in cols and row[col] is not None:
            return int(row[col])
    if "start" in cols and "end" in cols and row["start"] is not None and row["end"] is not None:
        return int(row["end"]) - int(row["start"])
    if "Start" in cols and "End" in cols and row["Start"] is not None and row["End"] is not None:
        return int(row["End"]) - int(row["Start"])
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
            name = name_from_row(raw, name_cols, strings)
            rows.append(
                {
                    "kernel_name": name,
                    "bucket": classify_kernel(name),
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


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_bucket: dict[str, dict[str, Any]] = {}
    by_kernel: dict[tuple[str, str], dict[str, Any]] = {}
    total_ms = sum(float(row["duration_ms"]) for row in rows)
    for row in rows:
        bucket = str(row["bucket"])
        name = str(row["kernel_name"])
        duration_ms = float(row["duration_ms"])
        bucket_entry = by_bucket.setdefault(bucket, {"bucket": bucket, "kernel_count": 0, "duration_ms": 0.0})
        bucket_entry["kernel_count"] += 1
        bucket_entry["duration_ms"] += duration_ms
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
        "",
        "## Bucket Summary",
        "",
        "| bucket | kernel count | duration ms | pct |",
        "|---|---:|---:|---:|",
    ]
    for row in summary["bucket_summary"]:
        lines.append(f"| {row['bucket']} | {row['kernel_count']} | {row['duration_ms']} | {row['pct']} |")
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
    summary = summarize(rows)
    payload = {"metadata": meta, **summary}

    (out_dir / "kernel_classification.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_csv(out_dir / "bucket_summary.csv", summary["bucket_summary"])
    write_csv(out_dir / "top_kernels.csv", summary["top_kernels"])
    write_markdown(out_dir / "summary.md", summary, meta)

    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
