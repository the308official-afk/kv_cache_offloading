#!/usr/bin/env python3
"""Build a slide-ready chart from the prompt-evolution run overview."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


PHASE_COLUMNS = ["Planning", "Execution", "Patch Gen", "Review", "Other"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overview-csv", required=True, help="prompt_evolution_run_overview.csv")
    parser.add_argument("--out-svg", required=True, help="Output SVG path")
    return parser.parse_args()


def parse_count(value: str) -> int:
    match = re.match(r"\s*(-?\d+)", value or "")
    return int(match.group(1)) if match else 0


def parse_patch_bytes(value: str) -> int:
    text = (value or "").strip().upper()
    if not text or text == "0 B":
        return 0
    match = re.match(r"([0-9.]+)\s*([KMG]?B)", text)
    if not match:
        return 0
    amount = float(match.group(1))
    unit = match.group(2)
    scale = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}.get(unit, 1)
    return int(amount * scale)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if row.get("Run")]


def main() -> int:
    args = parse_args()
    overview_csv = Path(args.overview_csv)
    out_svg = Path(args.out_svg)
    rows = load_rows(overview_csv)
    if not rows:
        raise SystemExit(f"No rows found in {overview_csv}")

    runs = [row["Run"] for row in rows]
    phase_counts = {
        phase: [parse_count(row.get(phase, "")) for row in rows]
        for phase in PHASE_COLUMNS
    }
    patch_bytes = [parse_patch_bytes(row.get("Patch", "")) for row in rows]
    patch_flags = [value > 0 for value in patch_bytes]

    colors = {
        "Planning": "#7c3aed",
        "Execution": "#2563eb",
        "Patch Gen": "#059669",
        "Review": "#f59e0b",
        "Other": "#64748b",
    }
    totals = [
        sum(phase_counts[phase][idx] for phase in PHASE_COLUMNS)
        for idx in range(len(rows))
    ]
    patched_count = sum(patch_flags)
    total_tool_calls = sum(totals)

    width = max(1200, 260 + len(rows) * 46)
    height = 720
    margin_left = 82
    margin_right = 36
    chart_top = 120
    chart_height = 360
    patch_top = 535
    patch_height = 78
    x_step = (width - margin_left - margin_right) / max(1, len(rows))
    bar_width = min(34, x_step * 0.72)
    max_total = max(totals + [1])
    max_patch_kb = max([value / 1024 for value in patch_bytes] + [1])

    def esc(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="32" y="52" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#0f172a">Experiment 6 Prompt Evolution: Run Overview</text>',
        f'<text x="32" y="82" font-family="Arial, sans-serif" font-size="15" fill="#475569">Rows: {len(rows)} | Patch-producing runs: {patched_count} | Total tool calls: {total_tool_calls}</text>',
    ]

    legend_x = width - margin_right - 520
    for idx, phase in enumerate(PHASE_COLUMNS):
        x = legend_x + idx * 104
        parts.append(f'<rect x="{x}" y="46" width="14" height="14" rx="3" fill="{colors[phase]}"/>')
        parts.append(f'<text x="{x + 20}" y="58" font-family="Arial, sans-serif" font-size="13" fill="#334155">{esc(phase)}</text>')

    for tick in range(0, max_total + 1, max(1, max_total // 5 or 1)):
        y = chart_top + chart_height - (tick / max_total) * chart_height
        parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{margin_left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">{tick}</text>')

    parts.append(f'<text x="24" y="{chart_top + 12}" font-family="Arial, sans-serif" font-size="13" fill="#475569" transform="rotate(-90 24,{chart_top + 12})">Tool calls</text>')
    for idx, run in enumerate(runs):
        x = margin_left + idx * x_step + (x_step - bar_width) / 2
        if patch_flags[idx]:
            parts.append(f'<rect x="{x - 4:.1f}" y="{chart_top}" width="{bar_width + 8:.1f}" height="{chart_height}" fill="#dcfce7" opacity="0.45"/>')
        y_cursor = chart_top + chart_height
        for phase in PHASE_COLUMNS:
            value = phase_counts[phase][idx]
            if value <= 0:
                continue
            h = (value / max_total) * chart_height
            y_cursor -= h
            parts.append(f'<rect x="{x:.1f}" y="{y_cursor:.1f}" width="{bar_width:.1f}" height="{h:.1f}" fill="{colors[phase]}"/>')
        parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{chart_top + chart_height + 18}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#334155" transform="rotate(-65 {x + bar_width / 2:.1f},{chart_top + chart_height + 18})">{esc(run)}</text>')

    parts.append(f'<text x="{margin_left}" y="{patch_top - 18}" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#0f172a">Patch output size</text>')
    for tick in range(0, int(max_patch_kb) + 2):
        if tick > max_patch_kb and tick != 1:
            continue
        y = patch_top + patch_height - (tick / max_patch_kb) * patch_height
        parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{margin_left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">{tick} KB</text>')

    for idx, value in enumerate(patch_bytes):
        x = margin_left + idx * x_step + (x_step - bar_width) / 2
        h = ((value / 1024) / max_patch_kb) * patch_height if value else 0
        y = patch_top + patch_height - h
        fill = "#059669" if value else "#cbd5e1"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{h:.1f}" fill="{fill}"/>')

    parts.append(f'<text x="{margin_left}" y="{height - 24}" font-family="Arial, sans-serif" font-size="13" fill="#475569">Green background marks runs that produced a nonzero patch.</text>')
    parts.append("</svg>")

    out_svg.parent.mkdir(parents=True, exist_ok=True)
    out_svg.write_text("\n".join(parts), encoding="utf-8")
    print(f"chart: {out_svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
