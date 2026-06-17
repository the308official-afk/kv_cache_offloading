#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SVG + story data assets for the KV retention hint slides."
    )
    parser.add_argument(
        "--input",
        default="experiments/reports/retention_threshold_matrix.csv",
        help="Path to retention_threshold_matrix.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="presentations/generated/retention_kv_hint_story",
        help="Directory for generated SVG and story data assets",
    )
    parser.add_argument("--model", default=None, help="Optional model filter")
    parser.add_argument(
        "--kv-tier-mode",
        default=None,
        help="Optional kv_tier_mode filter (defaults to the first available mode after filtering)",
    )
    parser.add_argument("--control-profile", default="none")
    parser.add_argument("--protected-profile", default="high-priority")
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def choose_default(values: list[str]) -> str | None:
    cleaned = [value for value in values if value]
    if not cleaned:
        return None
    counts = Counter(cleaned)
    return counts.most_common(1)[0][0]


def parse_int(value: str | None) -> int | None:
    if value in (None, "", "null"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_float(value: str | None) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    return None


def titleize_hint(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def fmt_int(value: int | None, fallback: str = "--") -> str:
    return fallback if value is None else f"{value:,}"


def fmt_float(value: float | None, digits: int = 1, fallback: str = "--") -> str:
    return fallback if value is None else f"{value:.{digits}f}"


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
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" rx="14" fill="#f8fafc" stroke="#dbe4f0"/>',
    )

    for tick in y_ticks:
        y = y_position(tick, min_y, max_y, top, plot_height)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>'
        )
        label = f"{int(round(tick)):,}"
        parts.append(
            f'<text x="{left - 14}" y="{y + 5:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="12" fill="#64748b">{label}</text>'
        )

    for x in x_values:
        xpos = x_position(x, min_x, max_x, left, plot_width)
        parts.append(
            f'<line x1="{xpos:.2f}" y1="{top}" x2="{xpos:.2f}" y2="{top + plot_height}" stroke="#eef2f7" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{xpos:.2f}" y="{top + plot_height + 28}" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="12" fill="#475569">{x}</text>'
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
        f'<text x="26" y="{top + plot_height / 2:.2f}" transform="rotate(-90 26 {top + plot_height / 2:.2f})" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="600" fill="#334155">{escape(y_label)}</text>'
    )
    parts.append(
        f'<text x="{left + plot_width / 2:.2f}" y="{height - 22}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="600" fill="#334155">Distractor Count</text>'
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
            f'<text x="{legend_x + 38}" y="{y0 + 5}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#334155">{escape(str(item["label"]))}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def threshold_summary(rows: list[dict[str, str]], hint_profile: str) -> dict[str, int | None]:
    filtered = sorted(
        (row for row in rows if row.get("hint_profile") == hint_profile),
        key=lambda row: parse_int(row.get("distractor_count")) or 0,
    )
    survived_counts = [
        parse_int(row.get("distractor_count"))
        for row in filtered
        if parse_bool(row.get("survived_effective")) is True
    ]
    evicted_counts = [
        parse_int(row.get("distractor_count"))
        for row in filtered
        if parse_bool(row.get("survived_effective")) is False
    ]
    return {
        "last_survived_distractor_count": max((value for value in survived_counts if value is not None), default=None),
        "first_evicted_distractor_count": min((value for value in evicted_counts if value is not None), default=None),
    }


def build_story_data(
    rows: list[dict[str, str]],
    report_path: Path,
    *,
    model: str,
    kv_tier_mode: str,
    control_profile: str,
    protected_profile: str,
) -> dict[str, object]:
    ordered_rows = sorted(
        rows,
        key=lambda row: (
            parse_int(row.get("distractor_count")) or 0,
            row.get("hint_profile") or "",
        ),
    )
    x_values = sorted(
        {
            parse_int(row.get("distractor_count"))
            for row in ordered_rows
            if parse_int(row.get("distractor_count")) is not None
        }
    )
    profile_rows = {
        control_profile: {parse_int(row.get("distractor_count")): row for row in ordered_rows if row.get("hint_profile") == control_profile},
        protected_profile: {parse_int(row.get("distractor_count")): row for row in ordered_rows if row.get("hint_profile") == protected_profile},
    }

    zero_fill_keys = {"a_replay_cached_tokens"}

    def values(profile: str, key: str) -> list[float | None]:
        series: list[float | None] = []
        for x in x_values:
            parsed = parse_float(profile_rows[profile].get(x, {}).get(key))
            if parsed is None and key in zero_fill_keys:
                parsed = 0.0
            series.append(parsed)
        return series

    def first_non_empty(key: str, profiles: list[str] | None = None) -> str | None:
        active_profiles = profiles or [control_profile, protected_profile]
        for profile in active_profiles:
            for x in x_values:
                row = profile_rows[profile].get(x)
                if not row:
                    continue
                value = row.get(key)
                if value not in (None, ""):
                    return value
        return None

    thresholds = {
        control_profile: threshold_summary(ordered_rows, control_profile),
        protected_profile: threshold_summary(ordered_rows, protected_profile),
    }

    effect_counts = [
        parse_int(row.get("distractor_count"))
        for row in ordered_rows
        if row.get("hint_profile") == protected_profile
        and row.get("hint_runtime_effect_status") == "effect_observed"
        and parse_int(row.get("distractor_count")) is not None
    ]

    story = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report_path": str(report_path),
        "model": model,
        "kv_tier_mode": kv_tier_mode,
        "control_profile": control_profile,
        "protected_profile": protected_profile,
        "profiles": {
            control_profile: {
                "label": titleize_hint(control_profile),
                "is_control": True,
                "distractor_counts": x_values,
                "a_first_latency_ms": values(control_profile, "a_first_latency_ms"),
                "a_replay_latency_ms": values(control_profile, "a_replay_latency_ms"),
                "a_first_prompt_tokens": values(control_profile, "a_first_prompt_tokens"),
                "a_replay_cached_tokens": values(control_profile, "a_replay_cached_tokens"),
                "thresholds": thresholds[control_profile],
            },
            protected_profile: {
                "label": titleize_hint(protected_profile),
                "is_control": False,
                "distractor_counts": x_values,
                "a_first_latency_ms": values(protected_profile, "a_first_latency_ms"),
                "a_replay_latency_ms": values(protected_profile, "a_replay_latency_ms"),
                "a_first_prompt_tokens": values(protected_profile, "a_first_prompt_tokens"),
                "a_replay_cached_tokens": values(protected_profile, "a_replay_cached_tokens"),
                "thresholds": thresholds[protected_profile],
            },
        },
        "capacity": {
            "worker_kv_capacity_tokens": parse_int(first_non_empty("worker_kv_capacity_tokens")),
            "worker_context_len": parse_int(first_non_empty("worker_context_len")),
            "a_prompt_tokens": parse_int(first_non_empty("a_first_prompt_tokens")),
            "distractor_prompt_tokens": parse_int(first_non_empty("first_distractor_prompt_tokens")),
            "max_distractor_count_tested": max(x_values) if x_values else None,
        },
        "attribution": {
            "worker_hint_status": first_non_empty("worker_hint_status", [protected_profile]),
            "worker_hint_profile_seen": first_non_empty("worker_hint_profile_seen", [protected_profile]),
            "worker_priority_mechanism_ready": parse_bool(
                first_non_empty("worker_priority_mechanism_ready", [protected_profile])
            ),
            "worker_priority_scheduling_enabled": parse_bool(
                first_non_empty("worker_priority_scheduling_enabled", [protected_profile])
            ),
            "worker_radix_eviction_policy": first_non_empty("worker_radix_eviction_policy", [protected_profile]),
            "request_top_level_priority_status": first_non_empty(
                "request_top_level_priority_status", [protected_profile]
            ),
            "worker_top_level_priority_status": first_non_empty(
                "worker_top_level_priority_status", [protected_profile]
            ),
            "request_agent_hints_priority_status": first_non_empty(
                "request_agent_hints_priority_status", [protected_profile]
            ),
            "hint_runtime_effect_first_observed_at": min(
                (value for value in effect_counts if value is not None),
                default=None,
            ),
        },
    }
    return story


def write_story_assets(story: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    control_profile = str(story["control_profile"])
    protected_profile = str(story["protected_profile"])
    x_values = story["profiles"][control_profile]["distractor_counts"]  # type: ignore[index]

    latency_svg = build_line_chart_svg(
        title="Replay Latency vs. Distractor Pressure",
        subtitle=None,
        x_values=x_values,  # type: ignore[arg-type]
        y_label="Latency (ms)",
        series=[
            {
                "label": f"{titleize_hint(control_profile)} • A first",
                "color": "#94a3b8",
                "dash": "8 6",
                "values": story["profiles"][control_profile]["a_first_latency_ms"],  # type: ignore[index]
            },
            {
                "label": f"{titleize_hint(control_profile)} • A replay",
                "color": "#2563eb",
                "values": story["profiles"][control_profile]["a_replay_latency_ms"],  # type: ignore[index]
            },
            {
                "label": f"{titleize_hint(protected_profile)} • A first",
                "color": "#f59e0b",
                "dash": "8 6",
                "values": story["profiles"][protected_profile]["a_first_latency_ms"],  # type: ignore[index]
            },
            {
                "label": f"{titleize_hint(protected_profile)} • A replay",
                "color": "#16a34a",
                "values": story["profiles"][protected_profile]["a_replay_latency_ms"],  # type: ignore[index]
            },
        ],
    )

    tokens_svg = build_line_chart_svg(
        title="Cached Tokens vs. Distractor Pressure",
        subtitle="Dashed lines show prompt size for A. Solid lines show cached tokens available on replay A.",
        x_values=x_values,  # type: ignore[arg-type]
        y_label="Tokens",
        series=[
            {
                "label": f"{titleize_hint(control_profile)} • A prompt",
                "color": "#94a3b8",
                "dash": "8 6",
                "values": story["profiles"][control_profile]["a_first_prompt_tokens"],  # type: ignore[index]
            },
            {
                "label": f"{titleize_hint(control_profile)} • Replay cached",
                "color": "#2563eb",
                "values": story["profiles"][control_profile]["a_replay_cached_tokens"],  # type: ignore[index]
            },
            {
                "label": f"{titleize_hint(protected_profile)} • A prompt",
                "color": "#f59e0b",
                "dash": "8 6",
                "values": story["profiles"][protected_profile]["a_first_prompt_tokens"],  # type: ignore[index]
            },
            {
                "label": f"{titleize_hint(protected_profile)} • Replay cached",
                "color": "#16a34a",
                "values": story["profiles"][protected_profile]["a_replay_cached_tokens"],  # type: ignore[index]
            },
        ],
    )

    (output_dir / "latency_vs_distractors.svg").write_text(latency_svg)
    (output_dir / "cached_tokens_vs_distractors.svg").write_text(tokens_svg)
    (output_dir / "story_metrics.json").write_text(json.dumps(story, indent=2))
    (output_dir / "story_data.js").write_text(
        "window.RETENTION_STORY_DATA = " + json.dumps(story, indent=2) + ";\n"
    )


def main() -> int:
    args = parse_args()
    report_path = Path(args.input)
    output_dir = Path(args.output_dir)

    rows = load_rows(report_path)
    if not rows:
        raise SystemExit(f"No rows found in {report_path}")

    model = args.model or choose_default([row.get("model", "") for row in rows])
    if not model:
        raise SystemExit("Could not determine a model from the report.")
    filtered = [row for row in rows if row.get("model") == model]

    kv_tier_mode = args.kv_tier_mode or choose_default([row.get("kv_tier_mode", "") for row in filtered])
    if kv_tier_mode:
        filtered = [row for row in filtered if row.get("kv_tier_mode") == kv_tier_mode]

    profiles = {row.get("hint_profile") for row in filtered}
    missing_profiles = [profile for profile in [args.control_profile, args.protected_profile] if profile not in profiles]
    if missing_profiles:
        raise SystemExit(
            f"Missing expected hint profiles in filtered report: {', '.join(missing_profiles)}"
        )

    story = build_story_data(
        filtered,
        report_path,
        model=model,
        kv_tier_mode=kv_tier_mode or "",
        control_profile=args.control_profile,
        protected_profile=args.protected_profile,
    )
    write_story_assets(story, output_dir)

    print(f"Generated retention story assets in {output_dir}")
    print(f"model={model}")
    if kv_tier_mode:
        print(f"kv_tier_mode={kv_tier_mode}")
    print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
