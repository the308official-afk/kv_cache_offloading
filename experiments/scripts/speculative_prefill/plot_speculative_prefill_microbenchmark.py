#!/usr/bin/env python3
"""Generate slide-ready SVG charts from speculative-prefill microbenchmark_matrix.csv."""

from __future__ import annotations

import argparse
import csv
import json
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


def color_for_arm(arm: str) -> str:
    return "#16a34a" if arm == "protected" else "#94a3b8"


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
    width = 980
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
    bar_width = min(120, int(gap * 0.6))

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
    width = 980
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


def main() -> None:
    args = parse_args()
    rows = read_csv(Path(args.matrix_csv))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sweep_rows = [row for row in rows if row.get("part") == "sweep"]
    if sweep_rows:
        by_arm: dict[str, list[dict[str, str]]] = {"control": [], "protected": []}
        for row in sweep_rows:
            arm = row.get("arm", "")
            if arm in by_arm:
                by_arm[arm].append(row)
        for arm_rows in by_arm.values():
            arm_rows.sort(key=lambda row: parse_int(row.get("sweep_value")) or 0)

        labels = [row.get("sweep_value", "") for row in by_arm["control"] or by_arm["protected"]]
        control_latency = [parse_int(row.get("turn_b_ms")) or 0 for row in by_arm["control"]]
        protected_latency = [parse_int(row.get("turn_b_ms")) or 0 for row in by_arm["protected"]]
        control_cached = [parse_int(row.get("turn_b_cached")) or 0 for row in by_arm["control"]]
        protected_cached = [parse_int(row.get("turn_b_cached")) or 0 for row in by_arm["protected"]]
        latency_gain = [max(0, control - protected) for control, protected in zip(control_latency, protected_latency)]
        cache_gain = [max(0, protected - control) for control, protected in zip(control_cached, protected_cached)]

        write_svg(
            out_dir / "turnb_latency.svg",
            build_line_chart_svg(
                title="Speculative Prefill Sweep: Turn B Latency",
                subtitle="If background prefill helps, the protected curve should sit below control.",
                labels=labels,
                series=[
                    ("Control", "#94a3b8", control_latency),
                    ("Protected", "#16a34a", protected_latency),
                ],
                y_label="Turn B Latency (ms)",
            ),
        )

        write_svg(
            out_dir / "turnb_cached.svg",
            build_line_chart_svg(
                title="Speculative Prefill Sweep: Turn B Cached Tokens",
                subtitle="If speculative prefill helps, the protected curve should stay above control.",
                labels=labels,
                series=[
                    ("Control", "#94a3b8", control_cached),
                    ("Protected", "#16a34a", protected_cached),
                ],
                y_label="Turn B Cached Tokens",
            ),
        )
        write_svg(
            out_dir / "latency_gain.svg",
            build_line_chart_svg(
                title="Speculative Prefill Sweep: Latency Gain",
                subtitle="Positive values mean the protected arm replayed turn B faster than control.",
                labels=labels,
                series=[("Latency gain", "#16a34a", latency_gain)],
                y_label="Latency Gain (ms)",
            ),
        )
        write_svg(
            out_dir / "cache_gain.svg",
            build_line_chart_svg(
                title="Speculative Prefill Sweep: Cache Gain",
                subtitle="Positive values mean the protected arm replayed turn B with more cached tokens than control.",
                labels=labels,
                series=[("Cache gain", "#16a34a", cache_gain)],
                y_label="Cached-Token Gain",
            ),
        )

        manifest = {
            "matrix_csv": str(Path(args.matrix_csv).resolve()),
            "chart_mode": "sweep",
            "charts": {
                "turnb_latency": str((out_dir / "turnb_latency.svg").resolve()),
                "turnb_cached": str((out_dir / "turnb_cached.svg").resolve()),
                "latency_gain": str((out_dir / "latency_gain.svg").resolve()),
                "cache_gain": str((out_dir / "cache_gain.svg").resolve()),
            },
        }
        (out_dir / "chart_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return

    labels = [row.get("arm", "") for row in rows]
    colors = [color_for_arm(row.get("arm", "")) for row in rows]
    latency_values = [parse_int(row.get("turn_b_ms")) or 0 for row in rows]
    cached_values = [parse_int(row.get("turn_b_cached")) or 0 for row in rows]

    write_svg(
        out_dir / "turnb_latency.svg",
        build_bar_chart_svg(
            title="Speculative Prefill: Turn B Latency",
            subtitle="Protected turn B should drop if speculative prefill helped.",
            labels=labels,
            values=latency_values,
            colors=colors,
            y_label="Turn B Latency (ms)",
        ),
    )

    write_svg(
        out_dir / "turnb_cached.svg",
        build_bar_chart_svg(
            title="Speculative Prefill: Turn B Cached Tokens",
            subtitle="Protected turn B should arrive warmer if the background prefill succeeded.",
            labels=labels,
            values=cached_values,
            colors=colors,
            y_label="Turn B Cached Tokens",
        ),
    )

    manifest = {
        "matrix_csv": str(Path(args.matrix_csv).resolve()),
        "chart_mode": "probe",
        "charts": {
            "turnb_latency": str((out_dir / "turnb_latency.svg").resolve()),
            "turnb_cached": str((out_dir / "turnb_cached.svg").resolve()),
        },
    }
    (out_dir / "chart_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
