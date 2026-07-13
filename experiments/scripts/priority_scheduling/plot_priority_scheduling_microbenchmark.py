#!/usr/bin/env python3
"""Generate slide-ready SVG charts from priority_scheduling microbenchmark_matrix.csv."""

from __future__ import annotations

import argparse
import csv
from html import escape
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-csv", required=True)
    parser.add_argument("--out-dir", required=True)
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
    width = 1260
    height = 560
    left = 92
    right = 60
    top = 96
    bottom = 110
    plot_width = width - left - right
    plot_height = height - top - bottom
    all_values = [value for _, _, values in series for value in values]
    min_y, max_y = series_bounds(all_values)
    if max_y > 0:
        max_y *= 1.12
    if min_y < 0:
        min_y *= 1.12
    grid_lines = 5
    y_ticks = [min_y + (max_y - min_y) * step / grid_lines for step in range(grid_lines + 1)]
    count = max(len(labels), 1)
    x_step = plot_width / max(count - 1, 1)

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
        x = left + (idx * x_step if count > 1 else plot_width / 2)
        parts.append(f'<text x="{x:.2f}" y="{top + plot_height + 24}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#475569">{escape(label)}</text>')

    legend_x = left
    legend_y = height - 34
    for idx, (name, color, values) in enumerate(series):
        points = []
        for value_idx, value in enumerate(values):
            x = left + (value_idx * x_step if count > 1 else plot_width / 2)
            y = top + plot_height - ((value - min_y) / (max_y - min_y)) * plot_height
            points.append(f"{x:.2f},{y:.2f}")
        if points:
            parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="4" points="{" ".join(points)}"/>')
            for point in points:
                x_str, y_str = point.split(",")
                parts.append(f'<circle cx="{x_str}" cy="{y_str}" r="5" fill="{color}"/>')
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
    width = 1260
    height = 560
    left = 92
    right = 60
    top = 96
    bottom = 118
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_y = max([100.0] + rates)
    grid_lines = 5
    y_ticks = [max_y * step / grid_lines for step in range(grid_lines + 1)]
    gap = plot_width / max(len(labels), 1)
    bar_width = min(86, int(gap * 0.58))

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

    for idx, (label, rate, count, max_count) in enumerate(zip(labels, rates, counts, max_counts)):
        center_x = left + gap * idx + gap / 2
        x0 = center_x - bar_width / 2
        bar_height = (rate / max_y) * plot_height if max_y else 0
        y0 = top + plot_height - bar_height
        color = "#2563eb" if count > 0 else "#cbd5e1"
        parts.append(f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{bar_width}" height="{bar_height:.2f}" rx="10" fill="{color}" opacity="0.94"/>')
        parts.append(f'<text x="{center_x:.2f}" y="{y0 - 26:.2f}" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="13" fill="#334155">{rate:.1f}%</text>')
        parts.append(f'<text x="{center_x:.2f}" y="{y0 - 8:.2f}" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="12" fill="#64748b">{count}/{max_count}</text>')
        parts.append(f'<text x="{center_x:.2f}" y="{top + plot_height + 24}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#475569">{escape(label)}</text>')

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
                title="Priority Scheduling: High-Priority Jump-Ahead Rate",
                subtitle="Higher bars mean high-priority requests were attached before more earlier-arriving low-priority requests.",
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
        low_wait_values = [parse_int(row.get("low_wait_ms")) or 0 for row in sweep_rows]
        high_wait_values = [parse_int(row.get("high_wait_ms")) or 0 for row in sweep_rows]
        low_latency_values = [parse_int(row.get("low_latency_ms")) or 0 for row in sweep_rows]
        high_latency_values = [parse_int(row.get("high_latency_ms")) or 0 for row in sweep_rows]
        wait_gain_values = [max(0, low - high) for low, high in zip(low_wait_values, high_wait_values)]
        latency_gain_values = [max(0, low - high) for low, high in zip(low_latency_values, high_latency_values)]

        write_svg(
            out_dir / "priority_wins.svg",
            build_bar_chart_svg(
                title="Priority Scheduling Sweep: Priority Wins",
                subtitle="More attached leapfrogs means late high-priority requests moved ahead more often.",
                labels=labels,
                values=attach_values,
                colors=["#2563eb"] * len(labels),
                y_label="High-Priority Wins",
            ),
        )

        write_svg(
            out_dir / "queue_wait.svg",
            build_line_chart_svg(
                title="Priority Scheduling Sweep: Queue Wait",
                subtitle="Lower high-priority wait than low-priority wait supports scheduling separation.",
                labels=labels,
                series=[
                    ("Low-priority wait", "#94a3b8", low_wait_values),
                    ("High-priority wait", "#2563eb", high_wait_values),
                ],
                y_label="Queue Wait (ms)",
            ),
        )
        write_svg(
            out_dir / "wait_gain.svg",
            build_line_chart_svg(
                title="Priority Scheduling Sweep: Wait Gain",
                subtitle="Positive values mean high-priority requests waited less than low-priority requests.",
                labels=labels,
                series=[("Wait gain", "#16a34a", wait_gain_values)],
                y_label="Wait Gain (ms)",
            ),
        )
        write_svg(
            out_dir / "latency_vs_arrival_gap.svg",
            build_line_chart_svg(
                title="Priority Scheduling Sweep: Request Latency",
                subtitle="Lower high-priority latency than low-priority latency supports scheduling separation.",
                labels=labels,
                series=[
                    ("Low-priority latency", "#94a3b8", low_latency_values),
                    ("High-priority latency", "#2563eb", high_latency_values),
                ],
                y_label="Latency (ms)",
            ),
        )
        write_svg(
            out_dir / "latency_gain.svg",
            build_line_chart_svg(
                title="Priority Scheduling Sweep: Latency Gain",
                subtitle="Positive values mean high-priority requests finished faster than low-priority requests.",
                labels=labels,
                series=[("Latency gain", "#16a34a", latency_gain_values)],
                y_label="Latency Gain (ms)",
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
