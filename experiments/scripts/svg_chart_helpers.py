"""Small SVG chart layout helpers shared by microbenchmark plotters."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def visible_tick_indexes(count: int, *, max_labels: int = 11) -> set[int]:
    """Return evenly spaced tick indexes, always keeping first and last."""
    if count <= 0:
        return set()
    if count <= max_labels:
        return set(range(count))
    if max_labels <= 1:
        return {0}

    indexes = {0, count - 1}
    span = count - 1
    for step in range(1, max_labels - 1):
        indexes.add(round(step * span / (max_labels - 1)))
    return indexes


def numeric_tick_indexes_for_values(
    values: list[object],
    *,
    preferred_step: float | None = None,
    max_labels: int = 11,
) -> set[int]:
    """Return readable tick indexes for numeric axes, falling back to sparse indexes."""
    parsed: list[float] = []
    for value in values:
        try:
            parsed.append(float(str(value).replace(",", "")))
        except ValueError:
            return visible_tick_indexes(len(values), max_labels=max_labels)
    if not parsed:
        return set()
    if len(parsed) <= max_labels:
        return set(range(len(parsed)))

    if preferred_step and preferred_step > 0:
        indexes = {0, len(parsed) - 1}
        for idx, value in enumerate(parsed):
            nearest = round(value / preferred_step) * preferred_step
            if abs(value - nearest) < 1e-6:
                indexes.add(idx)
        if len(indexes) <= max_labels:
            return indexes

    return visible_tick_indexes(len(values), max_labels=max_labels)


def visible_point_label_indexes(values: list[float], *, max_labels: int = 7) -> set[int]:
    """Return sparse point-label indexes, emphasizing endpoints and extremes."""
    count = len(values)
    if count <= 0:
        return set()
    if count <= max_labels:
        return set(range(count))

    indexes = {0, count - 1}
    numeric = [(idx, value) for idx, value in enumerate(values)]
    if numeric:
        indexes.add(max(numeric, key=lambda item: item[1])[0])
        indexes.add(min(numeric, key=lambda item: item[1])[0])

    for idx in visible_tick_indexes(count, max_labels=max_labels):
        indexes.add(idx)
        if len(indexes) >= max_labels:
            break
    return indexes


def numeric_label_positions(labels: list[str]) -> list[float] | None:
    """Parse labels into numeric x-axis positions when all labels are numeric."""
    parsed: list[float] = []
    for label in labels:
        try:
            parsed.append(float(str(label).replace(",", "")))
        except ValueError:
            return None
    if not parsed or min(parsed) == max(parsed):
        return None
    return parsed


def x_position_from_index(
    *,
    index: int,
    count: int,
    labels: list[str],
    left: int,
    plot_width: int,
) -> float:
    numeric_positions = numeric_label_positions(labels)
    if numeric_positions is not None:
        min_x = min(numeric_positions)
        max_x = max(numeric_positions)
        return left + ((numeric_positions[index] - min_x) / (max_x - min_x)) * plot_width
    return left + (index * (plot_width / max(count - 1, 1)) if count > 1 else plot_width / 2)


def render_png_if_possible(svg_path: Path, *, width: int | None = None) -> Path | None:
    """Best-effort SVG-to-PNG export for slide decks. Never fails the experiment."""
    if os.environ.get("CHART_EXPORT_PNG", "1").strip().lower() in {"0", "false", "no", "off"}:
        return None
    png_path = svg_path.with_suffix(".png")
    try:
        if shutil.which("rsvg-convert"):
            cmd = ["rsvg-convert", str(svg_path), "-o", str(png_path)]
            if width:
                cmd.extend(["-w", str(width)])
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return png_path if png_path.exists() else None
        if shutil.which("inkscape"):
            cmd = ["inkscape", str(svg_path), "--export-type=png", f"--export-filename={png_path}"]
            if width:
                cmd.append(f"--export-width={width}")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return png_path if png_path.exists() else None
        try:
            import cairosvg  # type: ignore
        except Exception:
            return None
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=width)
        return png_path if png_path.exists() else None
    except Exception as exc:
        print(f"warning: could not export PNG for {svg_path}: {exc}", file=sys.stderr)
        return None


def write_svg_with_png(path: Path, content: str, *, png_width: int | None = 2400) -> None:
    """Write SVG and, when tooling is available, a high-resolution PNG sibling."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    render_png_if_possible(path, width=png_width)
