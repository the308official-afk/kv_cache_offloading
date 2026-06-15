#!/usr/bin/env python3
"""Aggregate retention-probe sweep batches into eviction-threshold reports."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--progress-csv", required=True)
    parser.add_argument("--out-matrix", required=True)
    parser.add_argument("--out-comparison", required=True)
    parser.add_argument("--out-summary-md", required=True)
    parser.add_argument("--control-hint-profile", default="none")
    parser.add_argument("--match-event-min", type=int, default=1)
    parser.add_argument("--min-speedup-ratio", type=float, default=1.05)
    parser.add_argument("--min-latency-gain-ms", type=float, default=100.0)
    parser.add_argument("--sweep-status", choices=("partial", "complete"), default="partial")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    number = as_float(value)
    return int(number) if number is not None else None


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def request_succeeded(status: Any) -> bool:
    return str(status).strip() in {"200", "201"}


def round_ms(value: float | None) -> str:
    if value is None:
        return ""
    return str(int(round(value)))


def round_ratio(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"


def request_rows_by_role(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows = read_csv(path)
    return {
        row.get("request_role", ""): row
        for row in rows
        if row.get("request_role")
    }


def parse_worker_capacity(path: Path) -> dict[str, int | None]:
    if not path.exists():
        return {
            "worker_kv_capacity_tokens": None,
            "worker_context_len": None,
        }
    kv_capacity = None
    context_len = None
    scheduler_re = re.compile(
        r"max_total_num_tokens=(?P<kv>\d+).*context_len=(?P<context>\d+)"
    )
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = scheduler_re.search(raw_line)
        if match:
            kv_capacity = as_int(match.group("kv"))
            context_len = as_int(match.group("context"))
    return {
        "worker_kv_capacity_tokens": kv_capacity,
        "worker_context_len": context_len,
    }


def derived_row(
    *,
    sweep_id: str,
    model: str,
    kv_tier_mode: str,
    distractor_count: int,
    retention_probe_id: str,
    summary: dict[str, str],
    control_hint_profile: str,
    match_event_min: int,
    min_speedup_ratio: float,
    min_latency_gain_ms: float,
    sweep_status: str,
) -> dict[str, Any]:
    requests_csv_path = Path(summary.get("requests_csv", ""))
    if not requests_csv_path.is_absolute():
        requests_csv_path = Path.cwd() / requests_csv_path
    request_rows = request_rows_by_role(requests_csv_path)

    worker_log_path = Path(summary.get("worker_runtime_log", ""))
    if not worker_log_path.is_absolute():
        worker_log_path = Path.cwd() / worker_log_path
    worker_capacity = parse_worker_capacity(worker_log_path)

    hint_profile = summary.get("protected_hint_profile", "")
    replay_status = summary.get("a_replay_status", "")
    replay_ok = request_succeeded(replay_status)
    speedup_ratio = as_float(summary.get("a_replay_speedup_ratio"))
    latency_delta_ms = as_float(summary.get("a_replay_latency_delta_ms"))
    a_first_prompt_tokens = as_int(summary.get("a_first_prompt_tokens"))
    if a_first_prompt_tokens is None:
        a_first_prompt_tokens = as_int(request_rows.get("a_first", {}).get("prompt_tokens"))
    first_distractor_prompt_tokens = as_int(summary.get("first_distractor_prompt_tokens"))
    if first_distractor_prompt_tokens is None:
        first_distractor_prompt_tokens = next(
            (
                as_int(row.get("prompt_tokens"))
                for role, row in request_rows.items()
                if role.startswith("distractor_")
            ),
            None,
        )
    worker_kv_capacity_tokens = as_int(summary.get("worker_kv_capacity_tokens"))
    if worker_kv_capacity_tokens is None:
        worker_kv_capacity_tokens = worker_capacity["worker_kv_capacity_tokens"]
    worker_context_len = as_int(summary.get("worker_context_len"))
    if worker_context_len is None:
        worker_context_len = worker_capacity["worker_context_len"]
    replay_cached_tokens = as_int(summary.get("a_replay_cached_tokens"))
    replay_prompt_tokens = as_int(summary.get("a_replay_prompt_tokens"))
    if replay_prompt_tokens is None:
        replay_prompt_tokens = as_int(request_rows.get("a_replay", {}).get("prompt_tokens"))
    replay_cache_reuse_ratio = as_float(summary.get("a_replay_cache_reuse_ratio"))
    cache_match_events = as_int(summary.get("a_replay_sglang_cache_match_events")) or 0
    cache_events = as_int(summary.get("a_replay_sglang_cache_events")) or 0
    cache_direct = truthy(summary.get("a_replay_sglang_cache_direct"))
    survived_by_events = replay_ok and cache_direct and cache_match_events >= match_event_min
    survived_by_usage = replay_ok and replay_cached_tokens is not None and replay_cached_tokens > 0
    survived_by_latency = replay_ok and (
        (speedup_ratio is not None and speedup_ratio >= min_speedup_ratio)
        or (latency_delta_ms is not None and latency_delta_ms <= -abs(min_latency_gain_ms))
    )
    if replay_cached_tokens is not None:
        survived_effective = survived_by_usage and survived_by_latency
        effective_survival_source = "response_usage_cached_tokens"
    else:
        survived_effective = survived_by_events and survived_by_latency
        effective_survival_source = "sglang_cache_events_fallback"

    kv_tokens_left_after_a = (
        worker_kv_capacity_tokens - a_first_prompt_tokens
        if worker_kv_capacity_tokens is not None and a_first_prompt_tokens is not None
        else None
    )
    kv_tokens_left_after_a_after_first_distractor = (
        worker_kv_capacity_tokens - a_first_prompt_tokens - first_distractor_prompt_tokens
        if worker_kv_capacity_tokens is not None
        and a_first_prompt_tokens is not None
        and first_distractor_prompt_tokens is not None
        else None
    )

    if survived_by_usage and survived_by_latency:
        reuse_signal = "true_reuse_hit"
    elif survived_by_usage:
        reuse_signal = "usage_hit_without_speedup"
    elif survived_by_events and survived_by_latency:
        reuse_signal = "event_match_with_speedup"
    elif survived_by_events:
        reuse_signal = "semantic_match_only"
    else:
        reuse_signal = "no_reuse_evidence"

    return {
        "sweep_status": sweep_status,
        "retention_sweep_id": sweep_id,
        "model": model,
        "kv_tier_mode": kv_tier_mode,
        "hint_profile": hint_profile,
        "is_control": str(hint_profile == control_hint_profile).lower(),
        "distractor_count": distractor_count,
        "retention_probe_id": retention_probe_id,
        "a_first_status": summary.get("a_first_status", ""),
        "a_replay_status": replay_status,
        "a_first_latency_ms": summary.get("a_first_latency_ms", ""),
        "a_replay_latency_ms": summary.get("a_replay_latency_ms", ""),
        "a_replay_latency_delta_ms": summary.get("a_replay_latency_delta_ms", ""),
        "a_replay_speedup_ratio": summary.get("a_replay_speedup_ratio", ""),
        "worker_kv_capacity_tokens": worker_kv_capacity_tokens if worker_kv_capacity_tokens is not None else "",
        "worker_context_len": worker_context_len if worker_context_len is not None else "",
        "a_first_prompt_tokens": a_first_prompt_tokens if a_first_prompt_tokens is not None else "",
        "first_distractor_prompt_tokens": first_distractor_prompt_tokens if first_distractor_prompt_tokens is not None else "",
        "kv_tokens_left_after_a": kv_tokens_left_after_a if kv_tokens_left_after_a is not None else "",
        "kv_tokens_left_after_a_after_first_distractor": (
            kv_tokens_left_after_a_after_first_distractor
            if kv_tokens_left_after_a_after_first_distractor is not None
            else ""
        ),
        "a_replay_cached_tokens": replay_cached_tokens if replay_cached_tokens is not None else "",
        "a_replay_prompt_tokens": replay_prompt_tokens if replay_prompt_tokens is not None else "",
        "a_replay_cache_reuse_ratio": round_ratio(replay_cache_reuse_ratio),
        "a_replay_sglang_cache_events": cache_events,
        "a_replay_sglang_cache_match_events": cache_match_events,
        "a_replay_sglang_cache_semantic_tokens": summary.get("a_replay_sglang_cache_semantic_tokens", ""),
        "a_replay_sglang_cache_direct": str(cache_direct).lower(),
        "survived_by_usage": str(survived_by_usage).lower(),
        "survived_by_events": str(survived_by_events).lower(),
        "survived_by_latency": str(survived_by_latency).lower(),
        "survived_effective": str(survived_effective).lower(),
        "effective_survival_source": effective_survival_source,
        "reuse_signal": reuse_signal,
        "requests_csv": summary.get("requests_csv", ""),
        "worker_runtime_log": summary.get("worker_runtime_log", ""),
    }


def build_comparison_rows(
    rows: list[dict[str, Any]],
    *,
    control_hint_profile: str,
    sweep_status: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        key = (row["model"], row["kv_tier_mode"])
        grouped.setdefault(key, {}).setdefault(row["hint_profile"], []).append(row)

    out: list[dict[str, Any]] = []
    for (model, kv_tier_mode), by_profile in sorted(grouped.items()):
        control_rows = sorted(
            by_profile.get(control_hint_profile, []),
            key=lambda item: int(item["distractor_count"]),
        )
        control_first_evict = next(
            (int(row["distractor_count"]) for row in control_rows if row["survived_effective"] == "false"),
            None,
        )
        control_last_survive = next(
            (int(row["distractor_count"]) for row in reversed(control_rows) if row["survived_effective"] == "true"),
            None,
        )

        for hint_profile, profile_rows in sorted(by_profile.items()):
            if hint_profile == control_hint_profile:
                continue
            profile_rows = sorted(profile_rows, key=lambda item: int(item["distractor_count"]))
            protected_first_evict = next(
                (int(row["distractor_count"]) for row in profile_rows if row["survived_effective"] == "false"),
                None,
            )
            protected_last_survive = next(
                (int(row["distractor_count"]) for row in reversed(profile_rows) if row["survived_effective"] == "true"),
                None,
            )
            threshold_gap = (
                protected_first_evict - control_first_evict
                if protected_first_evict is not None and control_first_evict is not None
                else None
            )
            if threshold_gap is None:
                interpretation = "inconclusive"
            elif threshold_gap > 0:
                interpretation = "protected_hint_survives_longer"
            elif threshold_gap == 0:
                interpretation = "same_eviction_threshold_question_hint_respected"
            else:
                interpretation = "protected_hint_evicts_earlier"
            out.append(
                {
                    "sweep_status": sweep_status,
                    "model": model,
                    "kv_tier_mode": kv_tier_mode,
                    "control_hint_profile": control_hint_profile,
                    "protected_hint_profile": hint_profile,
                    "control_last_survived_distractor_count": control_last_survive or "",
                    "control_first_evicted_distractor_count": control_first_evict or "",
                    "protected_last_survived_distractor_count": protected_last_survive or "",
                    "protected_first_evicted_distractor_count": protected_first_evict or "",
                    "threshold_gap_distractors": threshold_gap if threshold_gap is not None else "",
                    "interpretation": interpretation,
                }
            )
    return out


def write_summary_md(
    path: Path,
    matrix_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    *,
    control_hint_profile: str,
    match_event_min: int,
    min_speedup_ratio: float,
    min_latency_gain_ms: float,
    sweep_status: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    models = sorted({row["model"] for row in matrix_rows})
    tiers = sorted({row["kv_tier_mode"] for row in matrix_rows})
    profiles = sorted({row["hint_profile"] for row in matrix_rows})
    lines = [
        "# Retention Threshold Sweep Summary",
        "",
        "## Scope",
        "",
        f"- Models: {', '.join(models) if models else 'none'}",
        f"- KV tier modes: {', '.join(tiers) if tiers else 'none'}",
        f"- Hint profiles: {', '.join(profiles) if profiles else 'none'}",
        f"- Control hint profile: {control_hint_profile}",
        f"- Sweep status: {sweep_status}",
        "",
        "## Effective survival rule",
        "",
        f"- replay must succeed (`200`/`201`)",
        f"- if replay exposes cached prompt tokens, we treat that as the primary reuse signal",
        f"- otherwise we fall back to direct cache attribution plus at least `{match_event_min}` match event(s)",
        f"- replay must also show meaningful benefit: speedup ratio >= `{min_speedup_ratio}` or latency gain >= `{int(min_latency_gain_ms)}` ms",
        "",
        "## Comparison",
        "",
    ]
    if not comparison_rows:
        lines.append("- No comparison rows were generated.")
    else:
        for row in comparison_rows:
            lines.extend(
                [
                    f"- `{row['model']}` / `{row['kv_tier_mode']}` / `{row['protected_hint_profile']}`:",
                    f"  control first evicted at `{row['control_first_evicted_distractor_count'] or 'not observed'}`, "
                    f"protected first evicted at `{row['protected_first_evicted_distractor_count'] or 'not observed'}`, "
                    f"interpretation: `{row['interpretation']}`",
                ]
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    progress_rows = read_csv(Path(args.progress_csv))
    matrix_rows: list[dict[str, Any]] = []
    for progress in progress_rows:
        batch_matrix = Path(progress["batch_matrix"])
        summaries = read_csv(batch_matrix)
        if not summaries:
            continue
        for summary in summaries:
            matrix_rows.append(
                derived_row(
                    sweep_id=progress["retention_sweep_id"],
                    model=progress["model"],
                    kv_tier_mode=progress["kv_tier_mode"],
                    distractor_count=int(progress["distractor_count"]),
                    retention_probe_id=progress["retention_probe_id"],
                    summary=summary,
                    control_hint_profile=args.control_hint_profile,
                    match_event_min=args.match_event_min,
                    min_speedup_ratio=args.min_speedup_ratio,
                    min_latency_gain_ms=args.min_latency_gain_ms,
                    sweep_status=args.sweep_status,
                )
            )

    matrix_fields = [
        "sweep_status",
        "retention_sweep_id",
        "model",
        "kv_tier_mode",
        "hint_profile",
        "is_control",
        "distractor_count",
        "retention_probe_id",
        "a_first_status",
        "a_replay_status",
        "a_first_latency_ms",
        "a_replay_latency_ms",
        "a_replay_latency_delta_ms",
        "a_replay_speedup_ratio",
        "worker_kv_capacity_tokens",
        "worker_context_len",
        "a_first_prompt_tokens",
        "first_distractor_prompt_tokens",
        "kv_tokens_left_after_a",
        "kv_tokens_left_after_a_after_first_distractor",
        "a_replay_cached_tokens",
        "a_replay_prompt_tokens",
        "a_replay_cache_reuse_ratio",
        "a_replay_sglang_cache_events",
        "a_replay_sglang_cache_match_events",
        "a_replay_sglang_cache_semantic_tokens",
        "a_replay_sglang_cache_direct",
        "survived_by_usage",
        "survived_by_events",
        "survived_by_latency",
        "survived_effective",
        "effective_survival_source",
        "reuse_signal",
        "requests_csv",
        "worker_runtime_log",
    ]
    write_csv(Path(args.out_matrix), matrix_rows, matrix_fields)

    comparison_rows = build_comparison_rows(
        matrix_rows,
        control_hint_profile=args.control_hint_profile,
        sweep_status=args.sweep_status,
    )
    comparison_fields = [
        "sweep_status",
        "model",
        "kv_tier_mode",
        "control_hint_profile",
        "protected_hint_profile",
        "control_last_survived_distractor_count",
        "control_first_evicted_distractor_count",
        "protected_last_survived_distractor_count",
        "protected_first_evicted_distractor_count",
        "threshold_gap_distractors",
        "interpretation",
    ]
    write_csv(Path(args.out_comparison), comparison_rows, comparison_fields)
    write_summary_md(
        Path(args.out_summary_md),
        matrix_rows,
        comparison_rows,
        control_hint_profile=args.control_hint_profile,
        match_event_min=args.match_event_min,
        min_speedup_ratio=args.min_speedup_ratio,
        min_latency_gain_ms=args.min_latency_gain_ms,
        sweep_status=args.sweep_status,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
