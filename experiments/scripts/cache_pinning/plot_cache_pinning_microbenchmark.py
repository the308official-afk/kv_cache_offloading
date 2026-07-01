#!/usr/bin/env python3
"""Generate slide-ready SVG charts from cache-pinning microbenchmark_matrix.csv."""

from __future__ import annotations

import argparse
import csv
import json
import math
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


def parse_float(value: str | None) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_int(value: str | None) -> int | None:
    parsed = parse_float(value)
    return int(parsed) if parsed is not None else None


def data_segments(xs: list[int], ys: list[float | None]) -> list[list[tuple[int, float]]]:
    segments: list[list[tuple[int, float]]] = []
    current: list[tuple[int, float]] = []
    for x, y in zip(xs, ys):
        if y is None or (isinstance(y, float) and not math.isfinite(y)):
            if current:
                segments.append(current)
                current = []
            continue
        current.append((x, y))
    if current:
        segments.append(current)
    return segments


def series_stats(values: list[float | None]) -> tuple[float, float]:
    numeric = [value for value in values if value is not None and math.isfinite(value)]
    if not numeric:
        return 0.0, 1.0
    minimum = min(numeric)
    maximum = max(numeric)
    if minimum == maximum:
        if minimum == 0:
            maximum = 1.0
        else:
            minimum = 0.0
            maximum = maximum * 1.2
    return minimum, maximum


def x_position(value: int, min_x: int, max_x: int, left: int, width: int) -> float:
    if max_x == min_x:
        return left + width / 2
    return left + ((value - min_x) / (max_x - min_x)) * width


def y_position(value: float, min_y: float, max_y: float, top: int, height: int) -> float:
    if max_y == min_y:
        return top + height / 2
    normalized = (value - min_y) / (max_y - min_y)
    return top + height - normalized * height


def svg_polyline(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def build_line_chart_svg(
    *,
    title: str,
    subtitle: str | None,
    x_values: list[int],
    series: list[dict[str, object]],
    y_label: str,
) -> str:
    width = 1360
    height = 600
    left = 92
    right = 248
    top = 82 if not subtitle else 96
    bottom = 76
    plot_width = width - left - right
    plot_height = height - top - bottom

    numeric_values: list[float | None] = []
    for item in series:
        numeric_values.extend(item["values"])  # type: ignore[arg-type]
    min_y, max_y = series_stats(numeric_values)
    min_y = min(0.0, min_y)
    max_y = max_y * 1.12 if max_y > 0 else 1.0

    min_x = min(x_values) if x_values else 0
    max_x = max(x_values) if x_values else 1

    grid_lines = 5
    y_ticks = [min_y + (max_y - min_y) * step / grid_lines for step in range(grid_lines + 1)]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="42" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="700" fill="#0f172a">{escape(title)}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="{left}" y="70" font-family="Inter, Arial, sans-serif" font-size="14" fill="#64748b">{escape(subtitle)}</text>'
        )
    parts.append(
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" rx="14" fill="#f8fafc" stroke="#dbe4f0"/>'
    )

    for tick in y_ticks:
        y = y_position(tick, min_y, max_y, top, plot_height)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>'
        )
        label = f"{int(round(tick)):,}"
        parts.append(
            f'<text x="{left - 14}" y="{y + 5.5:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="13" fill="#64748b">{label}</text>'
        )

    for x in x_values:
        xpos = x_position(x, min_x, max_x, left, plot_width)
        parts.append(
            f'<line x1="{xpos:.2f}" y1="{top}" x2="{xpos:.2f}" y2="{top + plot_height}" stroke="#eef2f7" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{xpos:.2f}" y="{top + plot_height + 30}" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="13" fill="#475569">{x}</text>'
        )

    for item in series:
        values: list[float | None] = item["values"]  # type: ignore[assignment]
        color = str(item["color"])
        dash = str(item.get("dash") or "")
        stroke = f' stroke-dasharray="{dash}"' if dash else ""
        segments = data_segments(x_values, values)
        for segment in segments:
            points = [
                (
                    x_position(x, min_x, max_x, left, plot_width),
                    y_position(y, min_y, max_y, top, plot_height),
                )
                for x, y in segment
            ]
            if len(points) >= 2:
                parts.append(
                    f'<polyline fill="none" stroke="{color}" stroke-width="3.2"{stroke} points="{svg_polyline(points)}"/>'
                )
            for point_x, point_y in points:
                parts.append(
                    f'<circle cx="{point_x:.2f}" cy="{point_y:.2f}" r="4.8" fill="#ffffff" stroke="{color}" stroke-width="2.6"/>'
                )

    parts.append(
        f'<text x="28" y="{top + plot_height / 2:.2f}" transform="rotate(-90 28 {top + plot_height / 2:.2f})" font-family="Inter, Arial, sans-serif" font-size="16" font-weight="700" fill="#334155">{escape(y_label)}</text>'
    )
    parts.append(
        f'<text x="{left + plot_width / 2:.2f}" y="{height - 20}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="16" font-weight="700" fill="#334155">Distractor Count</text>'
    )

    legend_x = left + plot_width + 20
    legend_y = top + 92
    for index, item in enumerate(series):
        y0 = legend_y + index * 44
        color = str(item["color"])
        dash = str(item.get("dash") or "")
        stroke = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(
            f'<line x1="{legend_x}" y1="{y0}" x2="{legend_x + 28}" y2="{y0}" stroke="{color}" stroke-width="3.2"{stroke}/>'
        )
        parts.append(
            f'<circle cx="{legend_x + 14}" cy="{y0}" r="4.8" fill="#ffffff" stroke="{color}" stroke-width="2.6"/>'
        )
        parts.append(
            f'<text x="{legend_x + 38}" y="{y0 + 5.5}" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="600" fill="#334155">{escape(str(item["label"]))}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def build_bar_chart_svg(
    *,
    title: str,
    subtitle: str | None,
    labels: list[str],
    values: list[float | None],
    colors: list[str],
    y_label: str,
) -> str:
    width = 1100
    height = 560
    left = 92
    right = 80
    top = 82 if not subtitle else 96
    bottom = 100
    plot_width = width - left - right
    plot_height = height - top - bottom

    min_y, max_y = series_stats(values)
    min_y = min(0.0, min_y)
    max_y = max_y * 1.12 if max_y > 0 else 1.0
    grid_lines = 5
    y_ticks = [min_y + (max_y - min_y) * step / grid_lines for step in range(grid_lines + 1)]

    bar_width = min(120, int(plot_width / max(len(labels), 1) * 0.55))
    gap = plot_width / max(len(labels), 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="42" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="700" fill="#0f172a">{escape(title)}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="{left}" y="70" font-family="Inter, Arial, sans-serif" font-size="14" fill="#64748b">{escape(subtitle)}</text>'
        )
    parts.append(
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" rx="14" fill="#f8fafc" stroke="#dbe4f0"/>'
    )

    for tick in y_ticks:
        y = y_position(tick, min_y, max_y, top, plot_height)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>'
        )
        label = f"{int(round(tick)):,}"
        parts.append(
            f'<text x="{left - 14}" y="{y + 5.5:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="13" fill="#64748b">{label}</text>'
        )

    for idx, (label, value, color) in enumerate(zip(labels, values, colors)):
        center_x = left + gap * idx + gap / 2
        x0 = center_x - bar_width / 2
        y0 = y_position(value or 0.0, min_y, max_y, top, plot_height)
        height_px = top + plot_height - y0
        parts.append(
            f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{bar_width}" height="{height_px:.2f}" rx="12" fill="{color}" opacity="0.92"/>'
        )
        shown = "" if value is None else f"{int(round(value)):,}"
        parts.append(
            f'<text x="{center_x:.2f}" y="{y0 - 12:.2f}" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="13" fill="#334155">{escape(shown)}</text>'
        )
        parts.append(
            f'<text x="{center_x:.2f}" y="{top + plot_height + 28}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="600" fill="#334155">{escape(label)}</text>'
        )

    parts.append(
        f'<text x="28" y="{top + plot_height / 2:.2f}" transform="rotate(-90 28 {top + plot_height / 2:.2f})" font-family="Inter, Arial, sans-serif" font-size="16" font-weight="700" fill="#334155">{escape(y_label)}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def select_rows(rows: list[dict[str, str]], *, part: str, row_kind: str) -> list[dict[str, str]]:
    return [row for row in rows if row.get("part") == part and row.get("row_kind") == row_kind]


def build_validate_charts(rows: list[dict[str, str]], out_dir: Path) -> list[dict[str, str]]:
    validate_rows = select_rows(rows, part="validate", row_kind="validate_turn")
    if not validate_rows:
        return []

    labels = [row.get("turn", "") for row in validate_rows]
    latency_values = [parse_float(row.get("latency_ms")) for row in validate_rows]
    cached_values = [parse_float(row.get("cached_tokens")) or 0.0 for row in validate_rows]

    latency_svg = build_bar_chart_svg(
        title="Cache-Pinning Validation Latency",
        subtitle="Doc-style validation turns",
        labels=labels,
        values=latency_values,
        colors=["#2563eb", "#16a34a"],
        y_label="Latency (ms)",
    )
    cached_svg = build_bar_chart_svg(
        title="Cache-Pinning Validation Cached Tokens",
        subtitle="Doc-style validation turns",
        labels=labels,
        values=cached_values,
        colors=["#94a3b8", "#f59e0b"],
        y_label="Cached Tokens",
    )

    latency_path = out_dir / "validation_latency.svg"
    cached_path = out_dir / "validation_cached_tokens.svg"
    write_svg(latency_path, latency_svg)
    write_svg(cached_path, cached_svg)

    return [
        {"chart_key": "validation_latency", "path": str(latency_path), "part": "validate"},
        {"chart_key": "validation_cached_tokens", "path": str(cached_path), "part": "validate"},
    ]


def build_sweep_charts(rows: list[dict[str, str]], out_dir: Path) -> list[dict[str, str]]:
    sweep_rows = select_rows(rows, part="sweep", row_kind="sweep_arm")
    if not sweep_rows:
        return []

    distractors = sorted(
        {
            value
            for value in (parse_int(row.get("distractors")) for row in sweep_rows)
            if value is not None
        }
    )
    arms = ["control", "protected"]
    colors = {"control": "#2563eb", "protected": "#16a34a"}

    def series_for(metric: str) -> list[dict[str, object]]:
        built: list[dict[str, object]] = []
        for arm in arms:
            values: list[float | None] = []
            for distractor in distractors:
                match = next(
                    (
                        row
                        for row in sweep_rows
                        if row.get("arm") == arm and parse_int(row.get("distractors")) == distractor
                    ),
                    None,
                )
                values.append(parse_float(match.get(metric)) if match else None)
            built.append(
                {
                    "label": arm.title(),
                    "color": colors[arm],
                    "values": values,
                }
            )
        return built

    latency_svg = build_line_chart_svg(
        title="Cache-Pinning Replay Latency",
        subtitle="Replay latency versus distractor count",
        x_values=distractors,
        series=series_for("replay_ms"),
        y_label="Replay Latency (ms)",
    )
    cached_svg = build_line_chart_svg(
        title="Cache-Pinning Replay Cached Tokens",
        subtitle="Replay cached tokens versus distractor count",
        x_values=distractors,
        series=series_for("cached_tokens"),
        y_label="Replay Cached Tokens",
    )

    latency_path = out_dir / "sweep_replay_latency.svg"
    cached_path = out_dir / "sweep_replay_cached_tokens.svg"
    write_svg(latency_path, latency_svg)
    write_svg(cached_path, cached_svg)

    return [
        {"chart_key": "sweep_replay_latency", "path": str(latency_path), "part": "sweep"},
        {"chart_key": "sweep_replay_cached_tokens", "path": str(cached_path), "part": "sweep"},
    ]


def main() -> int:
    args = parse_args()
    matrix_path = Path(args.matrix_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_csv(matrix_path)

    manifest = {
        "matrix_csv": str(matrix_path.resolve()),
        "generated_files": [],
    }
    manifest["generated_files"].extend(build_validate_charts(rows, out_dir))
    manifest["generated_files"].extend(build_sweep_charts(rows, out_dir))

    (out_dir / "chart_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
