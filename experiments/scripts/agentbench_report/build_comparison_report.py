#!/usr/bin/env python3
"""Build a multi-run comparison report from curated AgentBench run reports."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def discover_run_dirs(root: Path, *, latest: int | None, explicit: list[Path]) -> list[Path]:
    if explicit:
        return [path.resolve() for path in explicit]
    runs_root = root / "experiments/reports/runs"
    candidates = [path for path in runs_root.glob("*") if (path / "run_metrics.json").exists()]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if latest and latest > 0:
        return candidates[:latest]
    return candidates


def run_record(run_dir: Path, manifest: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    transfer = metrics.get("transfer_totals") or {}
    transfer_by_direction = transfer.get("by_direction") or {}
    device_to_host = transfer_by_direction.get("device_to_host") or {}
    host_to_device = transfer_by_direction.get("host_to_device") or {}
    phase_rows = metrics.get("phase_metrics") or []
    outcome = metrics.get("agent_outcome") or {}
    worker_summary = ((metrics.get("worker_runtime_log") or {}).get("summary") or {})
    prompt_total = sum(as_int(row.get("prompt_tokens")) for row in phase_rows)
    completion_total = sum(as_int(row.get("completion_tokens")) for row in phase_rows)
    latency_values = [as_float(row.get("latency_ms")) for row in phase_rows if row.get("latency_ms") not in (None, "")]
    ttft_values = [as_float(row.get("ttft_ms")) for row in phase_rows if row.get("ttft_ms") not in (None, "")]
    reuse_values = [as_float(row.get("cache_reuse_ratio")) for row in phase_rows if row.get("cache_reuse_ratio") not in (None, "")]
    resolved_hints = manifest.get("resolved_hints") or {}
    env = manifest.get("environment_snapshot") or {}
    return {
        "run_id": manifest.get("run_id") or run_dir.name,
        "hint_profile": manifest.get("hint_profile") or resolved_hints.get("hint_profile") or "unknown",
        "model": manifest.get("model"),
        "app_variant": manifest.get("app_variant"),
        "task_instance_id": (manifest.get("task") or {}).get("instance_id"),
        "task_repo": (manifest.get("task") or {}).get("repo"),
        "base_commit": (manifest.get("task") or {}).get("base_commit"),
        "run_started_at": manifest.get("run_started_at"),
        "report_dir": str(run_dir),
        "agentbench_result_dir": (manifest.get("paths") or {}).get("agentbench_result_dir"),
        "sglang_transfer_log": (manifest.get("paths") or {}).get("sglang_transfer_log"),
        "worker_extra_args": env.get("WORKER_EXTRA_ARGS"),
        "priority": resolved_hints.get("priority"),
        "reuse_likelihood": resolved_hints.get("reuse_likelihood"),
        "latency_sensitivity": resolved_hints.get("latency_sensitivity"),
        "expected_output_tokens": resolved_hints.get("expected_output_tokens"),
        "patch_nonempty": outcome.get("patch_nonempty"),
        "git_diff_nonempty": outcome.get("git_diff_nonempty"),
        "workspace_patch_bytes": outcome.get("workspace_patch_bytes"),
        "phase_count": len(phase_rows),
        "total_latency_ms": sum(latency_values),
        "avg_ttft_ms": sum(ttft_values) / len(ttft_values) if ttft_values else 0.0,
        "avg_cache_reuse_ratio": sum(reuse_values) / len(reuse_values) if reuse_values else 0.0,
        "max_cached_token_count": max((as_int(row.get("cached_token_count")) for row in phase_rows), default=0),
        "max_sglang_cached_token_count": max((as_int(row.get("sglang_cached_token_count")) for row in phase_rows), default=0),
        "prompt_tokens_total": prompt_total,
        "completion_tokens_total": completion_total,
        "transfer_event_count": transfer.get("event_count", 0),
        "transfer_device_to_host_kv_mb": device_to_host.get("kv_num_mb_estimated", 0.0),
        "transfer_host_to_device_kv_mb": host_to_device.get("kv_num_mb_estimated", 0.0),
        "transfer_cuda_sync_ms": transfer.get("elapsed_ms_cuda_sync", 0.0),
        "transfer_has_device_to_host": transfer.get("has_device_to_host"),
        "transfer_has_host_to_device": transfer.get("has_host_to_device"),
        "worker_runtime_json_matched_phase_count": sum(
            1 for row in phase_rows if str(row.get("worker_runtime_json_matched")).lower() == "true"
        ),
        "transfer_request_id_matched_phase_count": sum(
            1 for row in phase_rows if str(row.get("transfer_request_id_matched")).lower() == "true"
        ),
        "worker_prefill_event_count": worker_summary.get("prefill_event_count", 0),
        "worker_prefill_cached_token_max": worker_summary.get("prefill_cached_token_max", 0),
    }


def phase_records(run_base: dict[str, Any], metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for phase in metrics.get("phase_metrics") or []:
        rows.append(
            {
                "run_id": run_base["run_id"],
                "hint_profile": run_base["hint_profile"],
                "model": run_base["model"],
                "app_variant": run_base["app_variant"],
                "phase": phase.get("phase"),
                "request_id": phase.get("request_id"),
                "priority": phase.get("hint_priority"),
                "reuse_likelihood": phase.get("hint_reuse_likelihood"),
                "latency_sensitivity": phase.get("hint_latency_sensitivity"),
                "expected_output_tokens": phase.get("hint_expected_output_tokens"),
                "latency_ms": phase.get("latency_ms"),
                "ttft_ms": phase.get("ttft_ms"),
                "ttft_source": phase.get("ttft_source"),
                "sglang_ttft_ms_prefill_to_first_decode": phase.get("sglang_ttft_ms_prefill_to_first_decode"),
                "prompt_tokens": phase.get("prompt_tokens"),
                "completion_tokens": phase.get("completion_tokens"),
                "cache_hit": phase.get("cache_hit"),
                "cache_hit_source": phase.get("cache_hit_source"),
                "cached_token_count": phase.get("cached_token_count"),
                "recomputed_prefix_tokens": phase.get("recomputed_prefix_tokens"),
                "cache_reuse_ratio": phase.get("cache_reuse_ratio"),
                "sglang_cache_hit": phase.get("sglang_cache_hit"),
                "sglang_cached_token_count": phase.get("sglang_cached_token_count"),
                "sglang_new_token_count": phase.get("sglang_new_token_count"),
                "worker_runtime_json_matched": phase.get("worker_runtime_json_matched"),
                "worker_runtime_json_event_count": phase.get("worker_runtime_json_event_count"),
                "worker_runtime_json_request_id_source": phase.get("worker_runtime_json_request_id_source"),
                "worker_runtime_json_sglang_request_id": phase.get("worker_runtime_json_sglang_request_id"),
                "worker_runtime_json_cached_tokens": phase.get("worker_runtime_json_cached_tokens"),
                "worker_runtime_json_request_received_to_attached_ms": phase.get("worker_runtime_json_request_received_to_attached_ms"),
                "scheduler_cached_blocks": phase.get("scheduler_cached_blocks"),
                "worker_first_prefill_timestamp": phase.get("worker_first_prefill_timestamp"),
                "worker_first_decode_timestamp": phase.get("worker_first_decode_timestamp"),
                "transfer_request_id_matched": phase.get("transfer_request_id_matched"),
                "transfer_event_count_for_request": phase.get("transfer_event_count_for_request"),
                "transfer_device_to_host_kv_mb_for_request": phase.get("transfer_device_to_host_kv_mb_for_request"),
                "transfer_host_to_device_kv_mb_for_request": phase.get("transfer_host_to_device_kv_mb_for_request"),
                "transfer_cuda_sync_ms_for_request": phase.get("transfer_cuda_sync_ms_for_request"),
                "transfer_device_to_host_kv_mb": run_base["transfer_device_to_host_kv_mb"],
                "transfer_host_to_device_kv_mb": run_base["transfer_host_to_device_kv_mb"],
                "transfer_cuda_sync_ms": run_base["transfer_cuda_sync_ms"],
                "patch_nonempty": run_base["patch_nonempty"],
                "git_diff_nonempty": run_base["git_diff_nonempty"],
            }
        )
    return rows


def transfer_records(run_base: dict[str, Any], metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics.get("transfer_by_function_direction") or []:
        rows.append(
            {
                "run_id": run_base["run_id"],
                "hint_profile": run_base["hint_profile"],
                "model": run_base["model"],
                "app_variant": run_base["app_variant"],
                "function": row.get("function"),
                "direction": row.get("direction"),
                "direction_label": row.get("direction_label"),
                "count": row.get("count"),
                "num_mb_observed": row.get("num_mb_observed"),
                "kv_num_mb_estimated": row.get("kv_num_mb_estimated"),
                "kv_num_mb_estimated_page_granular": row.get("kv_num_mb_estimated_page_granular"),
                "elapsed_ms_wall": row.get("elapsed_ms_wall"),
                "elapsed_ms_cuda_sync": row.get("elapsed_ms_cuda_sync"),
                "cuda_sync_wait_ms": row.get("cuda_sync_wait_ms"),
                "semantic_token_count": row.get("semantic_token_count"),
                "error_count": row.get("error_count"),
            }
        )
    return rows


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def group_phase_summary(phase_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in phase_rows:
        groups[(row.get("hint_profile"), row.get("phase"), row.get("model"), row.get("app_variant"))].append(row)

    summary = []
    for (hint_profile, phase, model, app_variant), rows in sorted(groups.items()):
        summary.append(
            {
                "hint_profile": hint_profile,
                "phase": phase,
                "model": model,
                "app_variant": app_variant,
                "run_count": len({row.get("run_id") for row in rows}),
                "row_count": len(rows),
                "avg_latency_ms": average([as_float(row.get("latency_ms")) for row in rows]),
                "avg_ttft_ms": average([as_float(row.get("ttft_ms")) for row in rows]),
                "avg_sglang_ttft_ms_prefill_to_first_decode": average(
                    [as_float(row.get("sglang_ttft_ms_prefill_to_first_decode")) for row in rows]
                ),
                "avg_cache_reuse_ratio": average([as_float(row.get("cache_reuse_ratio")) for row in rows]),
                "avg_cached_token_count": average([as_float(row.get("cached_token_count")) for row in rows]),
                "avg_sglang_cached_token_count": average([as_float(row.get("sglang_cached_token_count")) for row in rows]),
                "avg_prompt_tokens": average([as_float(row.get("prompt_tokens")) for row in rows]),
                "avg_completion_tokens": average([as_float(row.get("completion_tokens")) for row in rows]),
                "avg_device_to_host_kv_mb": average([as_float(row.get("transfer_device_to_host_kv_mb")) for row in rows]),
                "avg_host_to_device_kv_mb": average([as_float(row.get("transfer_host_to_device_kv_mb")) for row in rows]),
                "host_to_device_seen": any(as_float(row.get("transfer_host_to_device_kv_mb")) > 0 for row in rows),
                "patch_seen": any(str(row.get("patch_nonempty")).lower() == "true" for row in rows),
            }
        )
    return summary


def write_summary_md(path: Path, comparison_id: str, run_rows: list[dict[str, Any]], group_rows: list[dict[str, Any]]) -> None:
    lines = [
        f"# Comparison Report: {comparison_id}",
        "",
        f"- Runs: `{len(run_rows)}`",
        "",
        "## Runs",
        "",
        "| Run | Profile | Patch | D2H KV MB | H2D KV MB | Avg TTFT ms | Avg Reuse |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in run_rows:
        lines.append(
            "| {run_id} | {profile} | {patch} | {d2h:.3f} | {h2d:.3f} | {ttft:.3f} | {reuse:.4f} |".format(
                run_id=row.get("run_id"),
                profile=row.get("hint_profile"),
                patch=row.get("patch_nonempty"),
                d2h=as_float(row.get("transfer_device_to_host_kv_mb")),
                h2d=as_float(row.get("transfer_host_to_device_kv_mb")),
                ttft=as_float(row.get("avg_ttft_ms")),
                reuse=as_float(row.get("avg_cache_reuse_ratio")),
            )
        )

    lines.extend(
        [
            "",
            "## Profile/Phase Averages",
            "",
            "| Profile | Phase | Runs | TTFT ms | SGLang TTFT ms | Reuse | Cached Tokens | H2D Seen |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in group_rows:
        lines.append(
            "| {profile} | {phase} | {runs} | {ttft:.3f} | {sgttft:.3f} | {reuse:.4f} | {cached:.1f} | {h2d} |".format(
                profile=row.get("hint_profile"),
                phase=row.get("phase"),
                runs=row.get("run_count"),
                ttft=as_float(row.get("avg_ttft_ms")),
                sgttft=as_float(row.get("avg_sglang_ttft_ms_prefill_to_first_decode")),
                reuse=as_float(row.get("avg_cache_reuse_ratio")),
                cached=as_float(row.get("avg_cached_token_count")),
                h2d=row.get("host_to_device_seen"),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_comparison(root: Path, run_dirs: list[Path], out_root: Path, comparison_id: str | None) -> Path:
    if not run_dirs:
        raise FileNotFoundError("No curated run reports found. Build per-run reports first.")
    comparison_id = comparison_id or f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = (out_root / comparison_id).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    run_rows: list[dict[str, Any]] = []
    phase_rows: list[dict[str, Any]] = []
    transfer_rows: list[dict[str, Any]] = []
    source_runs = []
    for run_dir in run_dirs:
        manifest = load_json(run_dir / "run_manifest.json", {})
        metrics = load_json(run_dir / "run_metrics.json", {})
        if not manifest or not metrics:
            continue
        base = run_record(run_dir, manifest, metrics)
        run_rows.append(base)
        phase_rows.extend(phase_records(base, metrics))
        transfer_rows.extend(transfer_records(base, metrics))
        source_runs.append(str(run_dir.resolve()))

    group_rows = group_phase_summary(phase_rows)
    manifest = {
        "comparison_id": comparison_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_count": len(run_rows),
        "source_runs": source_runs,
    }
    write_json(out_dir / "comparison_manifest.json", manifest)
    write_json(
        out_dir / "comparison_metrics.json",
        {
            "runs": run_rows,
            "phase_metrics": phase_rows,
            "transfer_metrics": transfer_rows,
            "profile_phase_summary": group_rows,
        },
    )

    run_fields = [
        "run_id",
        "hint_profile",
        "model",
        "app_variant",
        "task_instance_id",
        "task_repo",
        "run_started_at",
        "priority",
        "reuse_likelihood",
        "latency_sensitivity",
        "expected_output_tokens",
        "patch_nonempty",
        "git_diff_nonempty",
        "workspace_patch_bytes",
        "phase_count",
        "total_latency_ms",
        "avg_ttft_ms",
        "avg_cache_reuse_ratio",
        "max_cached_token_count",
        "max_sglang_cached_token_count",
        "prompt_tokens_total",
        "completion_tokens_total",
        "transfer_event_count",
        "transfer_device_to_host_kv_mb",
        "transfer_host_to_device_kv_mb",
        "transfer_cuda_sync_ms",
        "transfer_has_device_to_host",
        "transfer_has_host_to_device",
        "worker_runtime_json_matched_phase_count",
        "transfer_request_id_matched_phase_count",
        "worker_prefill_event_count",
        "worker_prefill_cached_token_max",
        "worker_extra_args",
        "report_dir",
        "agentbench_result_dir",
        "sglang_transfer_log",
    ]
    phase_fields = [
        "run_id",
        "hint_profile",
        "model",
        "app_variant",
        "phase",
        "request_id",
        "priority",
        "reuse_likelihood",
        "latency_sensitivity",
        "expected_output_tokens",
        "latency_ms",
        "ttft_ms",
        "ttft_source",
        "sglang_ttft_ms_prefill_to_first_decode",
        "prompt_tokens",
        "completion_tokens",
        "cache_hit",
        "cache_hit_source",
        "cached_token_count",
        "recomputed_prefix_tokens",
        "cache_reuse_ratio",
        "sglang_cache_hit",
        "sglang_cached_token_count",
        "sglang_new_token_count",
        "worker_runtime_json_matched",
        "worker_runtime_json_event_count",
        "worker_runtime_json_request_id_source",
        "worker_runtime_json_sglang_request_id",
        "worker_runtime_json_cached_tokens",
        "worker_runtime_json_request_received_to_attached_ms",
        "scheduler_cached_blocks",
        "transfer_request_id_matched",
        "transfer_event_count_for_request",
        "transfer_device_to_host_kv_mb_for_request",
        "transfer_host_to_device_kv_mb_for_request",
        "transfer_cuda_sync_ms_for_request",
        "transfer_device_to_host_kv_mb",
        "transfer_host_to_device_kv_mb",
        "transfer_cuda_sync_ms",
        "patch_nonempty",
        "git_diff_nonempty",
    ]
    transfer_fields = [
        "run_id",
        "hint_profile",
        "model",
        "app_variant",
        "function",
        "direction",
        "direction_label",
        "count",
        "num_mb_observed",
        "kv_num_mb_estimated",
        "kv_num_mb_estimated_page_granular",
        "elapsed_ms_wall",
        "elapsed_ms_cuda_sync",
        "cuda_sync_wait_ms",
        "semantic_token_count",
        "error_count",
    ]
    group_fields = [
        "hint_profile",
        "phase",
        "model",
        "app_variant",
        "run_count",
        "row_count",
        "avg_latency_ms",
        "avg_ttft_ms",
        "avg_sglang_ttft_ms_prefill_to_first_decode",
        "avg_cache_reuse_ratio",
        "avg_cached_token_count",
        "avg_sglang_cached_token_count",
        "avg_prompt_tokens",
        "avg_completion_tokens",
        "avg_device_to_host_kv_mb",
        "avg_host_to_device_kv_mb",
        "host_to_device_seen",
        "patch_seen",
    ]
    write_csv(out_dir / "runs.csv", run_rows, run_fields)
    write_csv(out_dir / "phase_metrics.csv", phase_rows, phase_fields)
    write_csv(out_dir / "transfer_metrics.csv", transfer_rows, transfer_fields)
    write_csv(out_dir / "profile_phase_summary.csv", group_rows, group_fields)
    write_summary_md(out_dir / "summary.md", comparison_id, run_rows, group_rows)
    return out_dir


def main() -> int:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        action="append",
        default=[],
        help="Curated run report directory. May be passed multiple times. Defaults to all reports.",
    )
    parser.add_argument(
        "--latest",
        type=int,
        default=0,
        help="Use the latest N curated run reports when --run-dir is not provided. Default 0 means all.",
    )
    parser.add_argument("--comparison-id", default=None, help="Output comparison id. Defaults to a timestamp.")
    parser.add_argument(
        "--out-root",
        type=Path,
        default=root / "experiments/reports/comparisons",
        help="Comparison report root directory.",
    )
    args = parser.parse_args()

    run_dirs = discover_run_dirs(root, latest=args.latest, explicit=args.run_dir)
    out_dir = build_comparison(root, run_dirs, args.out_root, args.comparison_id)
    print(f"comparison: {out_dir}")
    print(f"summary: {out_dir / 'summary.md'}")
    print(f"runs: {out_dir / 'runs.csv'}")
    print(f"phases: {out_dir / 'phase_metrics.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
