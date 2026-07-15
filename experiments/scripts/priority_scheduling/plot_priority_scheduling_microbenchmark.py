#!/usr/bin/env python3
"""Generate slide-ready SVG charts from priority_scheduling microbenchmark_matrix.csv."""

from __future__ import annotations

import argparse
import csv
import sys
from html import escape
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from svg_chart_helpers import visible_tick_indexes, x_position_from_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-csv", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--title", default="Priority Scheduling Microbenchmark")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_int(value: str | None) -> int | None:
    if value in (None, "", "null"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_percent(value: str | None) -> float | None:
    if value in (None, "", "null"):
        return None
    text = str(value).strip()
    try:
        if text.endswith("%"):
            return float(text[:-1])
        raw = float(text)
        return raw * 100 if 0 <= raw <= 1 else raw
    except (TypeError, ValueError):
        return None


def series_bounds(values: list[int]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    min_y = float(min(values))
    max_y = float(max(values))
    if min_y == max_y:
        if min_y == 0:
            max_y = 1.0
        else:
            min_y = min(0.0, min_y * 0.8)
            max_y = max(0.0, max_y * 1.2)
    if min_y > 0:
        min_y = 0.0
    if max_y < 0:
        max_y = 0.0
    if min_y == max_y:
        max_y = min_y + 1.0
    return min_y, max_y


def prio_color(value: str) -> str:
    return "#2563eb" if value == "high-priority" else "#94a3b8"


def write_svg(path: Path, svg: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def build_bar_chart_svg(
    *,
    title: str,
    subtitle: str,
    labels: list[str],
    values: list[int],
    colors: list[str],
    y_label: str,
) -> str:
    width = 1260
    height = 560
    left = 92
    right = 60
    top = 96
    bottom = 110
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_y = max(values) if values else 1
    if max_y <= 0:
        max_y = 1
    max_y = int(max_y * 1.12) or 1

    grid_lines = 5
    y_ticks = [round(max_y * step / grid_lines) for step in range(grid_lines + 1)]
    gap = plot_width / max(len(labels), 1)
    bar_width = min(68, int(gap * 0.65))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="42" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="700" fill="#0f172a">{escape(title)}</text>',
        f'<text x="{left}" y="70" font-family="Inter, Arial, sans-serif" font-size="14" fill="#64748b">{escape(subtitle)}</text>',
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" rx="14" fill="#f8fafc" stroke="#dbe4f0"/>',
    ]

    for tick in y_ticks:
        y = top + plot_height - (tick / max_y) * plot_height
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 5.5:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="13" fill="#64748b">{tick}</text>')

    for idx, (label, value, color) in enumerate(zip(labels, values, colors)):
        center_x = left + gap * idx + gap / 2
        x0 = center_x - bar_width / 2
        bar_height = (value / max_y) * plot_height
        y0 = top + plot_height - bar_height
        parts.append(f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{bar_width}" height="{bar_height:.2f}" rx="10" fill="{color}" opacity="0.92"/>')
        parts.append(f'<text x="{center_x:.2f}" y="{y0 - 8:.2f}" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="12" fill="#334155">{value}</text>')
        parts.append(f'<text x="{center_x:.2f}" y="{top + plot_height + 24}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#475569">{escape(label)}</text>')

    parts.append(f'<text x="28" y="{top + plot_height / 2:.2f}" transform="rotate(-90 28 {top + plot_height / 2:.2f})" font-family="Inter, Arial, sans-serif" font-size="16" font-weight="700" fill="#334155">{escape(y_label)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def build_line_chart_svg(
    *,
    title: str,
    subtitle: str,
    labels: list[str],
    series: list[tuple[str, str, list[int]]],
    y_label: str,
) -> str:
    width = 1600
    height = 720
    left = 92
    right = 60
    top = 96
    bottom = 128
    plot_width = width - left - right
    plot_height = height - top - bottom
    dense = len(labels) > 14
    tick_indexes = visible_tick_indexes(len(labels), max_labels=11)
    point_radius = 3.8 if dense else 5.0
    line_width = 3.0 if dense else 4.0
    all_values = [value for _, _, values in series for value in values]
    min_y, max_y = series_bounds(all_values)
    if max_y > 0:
        max_y *= 1.12
    if min_y < 0:
        min_y *= 1.12
    grid_lines = 5
    y_ticks = [min_y + (max_y - min_y) * step / grid_lines for step in range(grid_lines + 1)]
    count = max(len(labels), 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="42" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="700" fill="#0f172a">{escape(title)}</text>',
        f'<text x="{left}" y="70" font-family="Inter, Arial, sans-serif" font-size="14" fill="#64748b">{escape(subtitle)}</text>',
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" rx="14" fill="#f8fafc" stroke="#dbe4f0"/>',
    ]

    for tick in y_ticks:
        y = top + plot_height - ((tick - min_y) / (max_y - min_y)) * plot_height
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 5.5:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="13" fill="#64748b">{int(round(tick))}</text>')

    for idx, label in enumerate(labels):
        if idx not in tick_indexes:
            continue
        x = x_position_from_index(index=idx, count=count, labels=labels, left=left, plot_width=plot_width)
        parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_height}" stroke="#eef2f7" stroke-width="1"/>')
        parts.append(f'<text x="{x:.2f}" y="{top + plot_height + 30}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#475569">{escape(label)}</text>')

    legend_x = left
    legend_y = height - 34
    for idx, (name, color, values) in enumerate(series):
        points = []
        for value_idx, value in enumerate(values):
            x = x_position_from_index(index=value_idx, count=count, labels=labels, left=left, plot_width=plot_width)
            y = top + plot_height - ((value - min_y) / (max_y - min_y)) * plot_height
            points.append(f"{x:.2f},{y:.2f}")
        if points:
            parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="{line_width:.1f}" points="{" ".join(points)}"/>')
            for point in points:
                x_str, y_str = point.split(",")
                parts.append(f'<circle cx="{x_str}" cy="{y_str}" r="{point_radius:.1f}" fill="{color}"/>')
        lx = legend_x + idx * 220
        parts.append(f'<rect x="{lx}" y="{legend_y - 11}" width="18" height="18" rx="5" fill="{color}"/>')
        parts.append(f'<text x="{lx + 26}" y="{legend_y + 3}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#334155">{escape(name)}</text>')

    parts.append(f'<text x="28" y="{top + plot_height / 2:.2f}" transform="rotate(-90 28 {top + plot_height / 2:.2f})" font-family="Inter, Arial, sans-serif" font-size="16" font-weight="700" fill="#334155">{escape(y_label)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def build_jump_ahead_chart_svg(
    *,
    title: str,
    subtitle: str,
    labels: list[str],
    rates: list[float],
    counts: list[int],
    max_counts: list[int],
) -> str:
    width = 1600
    height = 720
    left = 92
    right = 60
    top = 96
    bottom = 132
    plot_width = width - left - right
    plot_height = height - top - bottom
    dense = len(labels) > 14
    tick_indexes = visible_tick_indexes(len(labels), max_labels=11)
    point_radius = 4.0 if dense else 6.0
    point_stroke = 1.7 if dense else 2.0
    line_width = 3.0 if dense else 4.0
    max_y = max([100.0] + rates)
    grid_lines = 5
    y_ticks = [max_y * step / grid_lines for step in range(grid_lines + 1)]
    count = max(len(labels), 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="42" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="700" fill="#0f172a">{escape(title)}</text>',
        f'<text x="{left}" y="70" font-family="Inter, Arial, sans-serif" font-size="14" fill="#64748b">{escape(subtitle)}</text>',
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" rx="14" fill="#f8fafc" stroke="#dbe4f0"/>',
    ]

    for tick in y_ticks:
        y = top + plot_height - (tick / max_y) * plot_height
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 5.5:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="13" fill="#64748b">{tick:.0f}%</text>')

    points = []
    for idx, (label, rate) in enumerate(zip(labels, rates)):
        x = x_position_from_index(index=idx, count=count, labels=labels, left=left, plot_width=plot_width)
        y = top + plot_height - (rate / max_y) * plot_height if max_y else top + plot_height
        points.append((x, y))
        if idx in tick_indexes:
            parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_height}" stroke="#eef2f7" stroke-width="1"/>')
            parts.append(f'<text x="{x:.2f}" y="{top + plot_height + 30}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#475569">{escape(label)}</text>')

    if points:
        path_points = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        parts.append(f'<polyline fill="none" stroke="#2563eb" stroke-width="{line_width:.1f}" stroke-linejoin="round" stroke-linecap="round" points="{path_points}"/>')

    for (x, y), jump_count in zip(points, counts):
        color = "#2563eb" if jump_count > 0 else "#94a3b8"
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{point_radius:.1f}" fill="{color}" stroke="#ffffff" stroke-width="{point_stroke:.1f}"/>')

    legend_x = left
    legend_y = height - 34
    parts.append(f'<line x1="{legend_x}" y1="{legend_y - 3}" x2="{legend_x + 32}" y2="{legend_y - 3}" stroke="#2563eb" stroke-width="4" stroke-linecap="round"/>')
    parts.append(f'<circle cx="{legend_x + 16}" cy="{legend_y - 3}" r="5" fill="#2563eb" stroke="#ffffff" stroke-width="2"/>')
    parts.append(f'<text x="{legend_x + 44}" y="{legend_y + 2}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#334155">High-urgency jump-ahead rate</text>')

    parts.append(f'<text x="28" y="{top + plot_height / 2:.2f}" transform="rotate(-90 28 {top + plot_height / 2:.2f})" font-family="Inter, Arial, sans-serif" font-size="16" font-weight="700" fill="#334155">Jump-Ahead Rate</text>')
    parts.append(f'<text x="{left + plot_width / 2:.2f}" y="{height - 40}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="700" fill="#334155">Arrival Gap (ms)</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    args = parse_args()
    rows = read_csv(Path(args.matrix_csv))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    compact_rows = [row for row in rows if row.get("high_jump_ahead_count", "") != ""]
    if compact_rows:
        labels = [row.get("gap_ms", "") for row in compact_rows]
        counts = [parse_int(row.get("high_jump_ahead_count")) or 0 for row in compact_rows]
        max_counts = [parse_int(row.get("max_jump_ahead")) or 0 for row in compact_rows]
        rates = [
            parse_percent(row.get("high_jump_ahead_rate"))
            if parse_percent(row.get("high_jump_ahead_rate")) is not None
            else ((count / max_count) * 100 if max_count else 0)
            for row, count, max_count in zip(compact_rows, counts, max_counts)
        ]
        write_svg(
            out_dir / "jump_ahead.svg",
            build_jump_ahead_chart_svg(
                title=f"{args.title}: High-Urgency Jump-Ahead Rate",
                subtitle="Higher points mean high-urgency requests were attached before more earlier-arriving low-priority requests.",
                labels=labels,
                rates=rates,
                counts=counts,
                max_counts=max_counts,
            ),
        )
        return

    sweep_rows = [row for row in rows if row.get("part") == "sweep"]
    if sweep_rows:
        labels = [row.get("sweep_value", "") for row in sweep_rows]
        attach_values = [max(0, parse_int(row.get("high_attach_leapfrogs")) or 0) for row in sweep_rows]

        write_svg(
            out_dir / "jump_ahead.svg",
            build_line_chart_svg(
                title=f"{args.title}: High-Urgency Jump-Ahead Events",
                subtitle="Higher points mean high-urgency requests attached before more earlier-arriving low-priority requests.",
                labels=labels,
                series=[("Jump-ahead events", "#2563eb", attach_values)],
                y_label="Jump-Ahead Events",
            ),
        )

        return

    labels = [row.get("request", "") for row in rows]
    colors = [prio_color(row.get("prio_class", "")) for row in rows]

    attach_values = [max(0, parse_int(row.get("attach_gain")) or 0) for row in rows]
    queue_values = [parse_int(row.get("queue_ms")) or 0 for row in rows]

    write_svg(
        out_dir / "attach_gain.svg",
        build_bar_chart_svg(
            title="Priority Scheduling: Attach Gain",
            subtitle="Higher bars on later high-priority requests mean they moved forward in attach order.",
            labels=labels,
            values=attach_values,
            colors=colors,
            y_label="Attach Gain",
        ),
    )

    write_svg(
        out_dir / "queue_wait.svg",
        build_bar_chart_svg(
            title="Priority Scheduling: Worker Queue Wait",
            subtitle="Lower queue wait for high-priority requests supports the scheduling effect.",
            labels=labels,
            values=queue_values,
            colors=colors,
            y_label="Queue Wait (ms)",
        ),
    )


if __name__ == "__main__":
    main()
