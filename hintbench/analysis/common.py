#!/usr/bin/env python3

"""Shared helpers for HintBench analysis scripts."""

from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def format_num(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}"


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(value))

    def fmt_line(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[i]) for i, value in enumerate(values))

    divider = "-+-".join("-" * width for width in widths)
    lines = [fmt_line(headers), divider]
    lines.extend(fmt_line(row) for row in rows)
    return "\n".join(lines)


def load_run(run_dir: Path) -> dict:
    metadata = load_json(run_dir / "metadata.json")
    summary = load_json(run_dir / "summary.json")
    results = load_jsonl(run_dir / "results.jsonl")
    return {
        "run_dir": str(run_dir),
        "metadata": metadata,
        "summary": summary,
        "results": results,
    }
