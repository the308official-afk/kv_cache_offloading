#!/usr/bin/env python3
"""Build a consolidated priority-scheduling microbenchmark report."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MATRIX_COLUMNS = [
    "benchmark_id",
    "part",
    "sweep_axis",
    "sweep_value",
    "run_id",
    "model",
    "request_source",
    "source_instance_id",
    "source_task_index",
    "request",
    "prio_class",
    "arrival",
    "attach",
    "complete",
    "attach_gain",
    "complete_gain",
    "beat_low_attach",
    "beat_low_complete",
    "queue_ms",
    "latency_ms",
    "low_wait_ms",
    "high_wait_ms",
    "low_latency_ms",
    "high_latency_ms",
    "high_attach_leapfrogs",
    "high_complete_leapfrogs",
    "top_prio_compat",
    "worker_hint_status",
    "worker_top_prio_status",
    "sglang_prio_status",
    "worker_hint_prio",
    "sent_top_prio",
    "worker_top_prio",
    "sglang_prio",
    "runtime_match",
    "effect",
]

SUMMARY_COLUMNS = [
    "benchmark_id",
    "mode",
    "run_id",
    "model",
    "request_source",
    "swebench_dataset",
    "swebench_split",
    "swebench_start_index",
    "probe_run_id",
    "sweep_axis",
    "sweep_values",
    "sweep_run_count",
    "low_n",
    "high_n",
    "input_words",
    "output_tokens",
    "arrival_gap_ms",
    "inter_gap_ms",
    "top_prio_compat",
    "worker_hint_status",
    "worker_top_prio_status",
    "sglang_prio_status",
    "runtime_cov",
    "attach_cov",
    "complete_cov",
    "low_wait_ms",
    "high_wait_ms",
    "low_latency_ms",
    "high_latency_ms",
    "high_attach_leapfrogs",
    "high_complete_leapfrogs",
    "effect",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", required=True, choices=("probe", "sweep", "all", "plot"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--contract-sh", required=True)
    parser.add_argument("--contract-md", default="")
    parser.add_argument("--probe-run-id", default="")
    parser.add_argument("--sweep-run-ids", default="")
    parser.add_argument("--sweep-axis", default="")
    parser.add_argument("--sweep-values", default="")
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


def pick(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        if key in row and row.get(key, "") != "":
            return row.get(key, "")
    return ""


def load_contract_env(contract_path: Path) -> dict[str, str]:
    shell = f"""
set -a
source {json.dumps(str(contract_path))}
env
"""
    completed = subprocess.run(
        ["bash", "-lc", shell],
        check=True,
        text=True,
        capture_output=True,
    )
    env_map: dict[str, str] = {}
    prefixes = (
        "PRIORITY_SCHEDULING_",
        "PRIORITY_REQUEST_CONTEXT_MODE",
        "PRIORITY_TOP_LEVEL_PRIORITY_MODE",
        "LOW_PRIORITY_",
        "HIGH_PRIORITY_",
        "WORKER_BASE_ARGS",
        "MODEL_READY_",
        "MODEL_SMOKE_",
        "MODEL_COOLDOWN_SECS",
    )
    for line in completed.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.startswith(prefixes):
            env_map[key] = value
    return env_map


def build_run_contract(args: argparse.Namespace, contract_env: dict[str, str]) -> dict[str, Any]:
    return {
        "benchmark_id": args.run_id,
        "mode": args.mode,
        "model": args.model,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_sh": str(Path(args.contract_sh).resolve()),
        "contract_md": str(Path(args.contract_md).resolve()) if args.contract_md else "",
        "probe_run_id": args.probe_run_id,
        "sweep_run_ids": [item for item in args.sweep_run_ids.split(",") if item],
        "sweep_axis": args.sweep_axis,
        "sweep_values": [item for item in args.sweep_values.split() if item],
        "contract_env": contract_env,
    }


def probe_paths(run_id: str) -> dict[str, Path]:
    root = Path("experiments/reports/priority_scheduling") / run_id
    return {
        "root": root,
        "matrix": root / "priority_scheduling_readable.csv",
        "summary": root / "priority_scheduling_summary.csv",
        "summary_md": root / "priority_scheduling_summary.md",
    }


def normalize_matrix_rows(benchmark_id: str, probe_run_id: str, model: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "benchmark_id": benchmark_id,
                "part": "probe",
                "sweep_axis": "",
                "sweep_value": "",
                "run_id": probe_run_id,
                "model": model,
                "request_source": pick(row, "request_source"),
                "source_instance_id": pick(row, "source_instance_id"),
                "source_task_index": pick(row, "source_task_index"),
                "request": pick(row, "request", "request_role"),
                "prio_class": pick(row, "prio_class", "priority_class"),
                "arrival": pick(row, "arrival", "arrival_index"),
                "attach": pick(row, "attach", "attached_rank"),
                "complete": pick(row, "complete", "completed_rank"),
                "attach_gain": pick(row, "attach_priority_gain"),
                "complete_gain": pick(row, "completion_priority_gain"),
                "beat_low_attach": pick(row, "beat_low_attach", "overtook_earlier_low_attached_count"),
                "beat_low_complete": pick(row, "beat_low_complete", "overtook_earlier_low_completed_count"),
                "queue_ms": pick(row, "queue_ms", "worker_queue_wait_ms"),
                "latency_ms": pick(row, "latency_ms", "client_latency_ms"),
                "low_wait_ms": "",
                "high_wait_ms": "",
                "low_latency_ms": "",
                "high_latency_ms": "",
                "high_attach_leapfrogs": "",
                "high_complete_leapfrogs": "",
                "top_prio_compat": "",
                "worker_hint_status": "",
                "worker_top_prio_status": "",
                "sglang_prio_status": "",
                "worker_hint_prio": pick(row, "worker_hint_prio", "worker_agent_hints_priority"),
                "sent_top_prio": pick(row, "sent_top_prio", "top_level_priority_sent"),
                "worker_top_prio": pick(row, "worker_top_prio", "worker_top_level_priority"),
                "sglang_prio": pick(row, "sglang_prio", "sglang_scheduler_priority_applied"),
                "runtime_match": pick(row, "runtime_match", "worker_runtime_matched"),
                "effect": pick(row, "effect", "scheduling_success_signal"),
            }
        )
    return normalized


def normalize_summary(benchmark_id: str, summary_row: dict[str, str]) -> dict[str, Any]:
    return {
        "benchmark_id": benchmark_id,
        "mode": pick(summary_row, "attribution_mode", "mode"),
        "run_id": pick(summary_row, "run_id"),
        "model": pick(summary_row, "model"),
        "request_source": pick(summary_row, "request_source"),
        "swebench_dataset": pick(summary_row, "swebench_dataset"),
        "swebench_split": pick(summary_row, "swebench_split"),
        "swebench_start_index": pick(summary_row, "swebench_start_index"),
        "low_n": pick(summary_row, "low_priority_count", "low_n"),
        "high_n": pick(summary_row, "high_priority_count", "high_n"),
        "input_words": pick(summary_row, "input_len_words", "input_words"),
        "output_tokens": pick(summary_row, "output_len_tokens", "output_tokens"),
        "arrival_gap_ms": pick(summary_row, "arrival_gap_ms"),
        "inter_gap_ms": pick(summary_row, "inter_request_gap_ms"),
        "top_prio_compat": pick(summary_row, "frontend_top_level_priority_compatibility", "top_prio_compat"),
        "worker_hint_status": pick(summary_row, "worker_high_hint_received_status", "worker_hint_status"),
        "worker_top_prio_status": pick(summary_row, "worker_high_top_level_priority_status", "worker_top_prio_status"),
        "sglang_prio_status": pick(summary_row, "worker_priority_path_status", "sglang_prio_status"),
        "runtime_cov": pick(summary_row, "worker_runtime_event_coverage", "runtime_cov"),
        "attach_cov": pick(summary_row, "worker_attached_event_coverage", "attach_cov"),
        "complete_cov": pick(summary_row, "worker_completed_event_coverage", "complete_cov"),
        "low_wait_ms": pick(summary_row, "mean_low_queue_wait_ms", "low_wait_ms"),
        "high_wait_ms": pick(summary_row, "mean_high_queue_wait_ms", "high_wait_ms"),
        "low_latency_ms": pick(summary_row, "mean_low_client_latency_ms", "low_latency_ms"),
        "high_latency_ms": pick(summary_row, "mean_high_client_latency_ms", "high_latency_ms"),
        "high_attach_leapfrogs": pick(summary_row, "high_priority_attached_leapfrogs", "high_attach_leapfrogs"),
        "high_complete_leapfrogs": pick(summary_row, "high_priority_completed_leapfrogs", "high_complete_leapfrogs"),
        "effect": "yes" if str(pick(summary_row, "scheduling_effect_observed", "effect_status")).lower() in {"true", "yes"} else pick(summary_row, "effect_status", "scheduling_effect_observed"),
    }


def normalize_sweep_row(
    benchmark_id: str,
    run_id: str,
    model: str,
    sweep_axis: str,
    sweep_value: str,
    summary_row: dict[str, str],
) -> dict[str, Any]:
    summary = normalize_summary(benchmark_id, summary_row)
    return {
        "benchmark_id": benchmark_id,
        "part": "sweep",
        "sweep_axis": sweep_axis,
        "sweep_value": sweep_value,
        "run_id": run_id,
        "model": model,
        "request_source": summary["request_source"],
        "source_instance_id": "",
        "source_task_index": "",
        "request": "",
        "prio_class": "",
        "arrival": "",
        "attach": "",
        "complete": "",
        "attach_gain": "",
        "complete_gain": "",
        "beat_low_attach": "",
        "beat_low_complete": "",
        "queue_ms": "",
        "latency_ms": "",
        "low_wait_ms": summary["low_wait_ms"],
        "high_wait_ms": summary["high_wait_ms"],
        "low_latency_ms": summary["low_latency_ms"],
        "high_latency_ms": summary["high_latency_ms"],
        "high_attach_leapfrogs": summary["high_attach_leapfrogs"],
        "high_complete_leapfrogs": summary["high_complete_leapfrogs"],
        "top_prio_compat": summary["top_prio_compat"],
        "worker_hint_status": summary["worker_hint_status"],
        "worker_top_prio_status": summary["worker_top_prio_status"],
        "sglang_prio_status": summary["sglang_prio_status"],
        "worker_hint_prio": "",
        "sent_top_prio": "",
        "worker_top_prio": "",
        "sglang_prio": "",
        "runtime_match": "",
        "effect": summary["effect"],
    }


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Priority Scheduling Microbenchmark",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- model: `{summary['model']}`",
        f"- request_source: `{summary['request_source']}`",
        f"- swebench_dataset: `{summary['swebench_dataset']}`",
        f"- swebench_split: `{summary['swebench_split']}`",
        f"- swebench_start_index: `{summary['swebench_start_index']}`",
        f"- probe_run_id: `{summary['probe_run_id']}`",
        f"- sweep_axis: `{summary['sweep_axis']}`",
        f"- sweep_values: `{summary['sweep_values']}`",
        f"- sweep_run_count: `{summary['sweep_run_count']}`",
        f"- low_n: `{summary['low_n']}`",
        f"- high_n: `{summary['high_n']}`",
        f"- top_prio_compat: `{summary['top_prio_compat']}`",
        f"- worker_hint_status: `{summary['worker_hint_status']}`",
        f"- worker_top_prio_status: `{summary['worker_top_prio_status']}`",
        f"- sglang_prio_status: `{summary['sglang_prio_status']}`",
        f"- low_wait_ms: `{summary['low_wait_ms']}`",
        f"- high_wait_ms: `{summary['high_wait_ms']}`",
        f"- high_attach_leapfrogs: `{summary['high_attach_leapfrogs']}`",
        f"- high_complete_leapfrogs: `{summary['high_complete_leapfrogs']}`",
        f"- effect: `{summary['effect']}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    contract_env = load_contract_env(Path(args.contract_sh))
    run_contract = build_run_contract(args, contract_env)

    matrix_rows: list[dict[str, Any]] = []
    summary_row = {column: "" for column in SUMMARY_COLUMNS}
    summary_row["benchmark_id"] = args.run_id
    summary_row["mode"] = args.mode
    summary_row["model"] = args.model
    summary_row["probe_run_id"] = args.probe_run_id
    summary_row["sweep_axis"] = args.sweep_axis
    summary_row["sweep_values"] = args.sweep_values

    sweep_run_ids = [item for item in args.sweep_run_ids.split(",") if item]
    summary_row["sweep_run_count"] = str(len(sweep_run_ids)) if sweep_run_ids else ""

    if args.probe_run_id:
        paths = probe_paths(args.probe_run_id)
        readable_rows = read_csv(paths["matrix"])
        summary_rows = read_csv(paths["summary"])
        matrix_rows.extend(normalize_matrix_rows(args.run_id, args.probe_run_id, args.model, readable_rows))
        if summary_rows:
            summary_row = normalize_summary(args.run_id, summary_rows[0])
            summary_row["probe_run_id"] = args.probe_run_id
            summary_row["sweep_axis"] = args.sweep_axis
            summary_row["sweep_values"] = args.sweep_values
            summary_row["sweep_run_count"] = str(len(sweep_run_ids)) if sweep_run_ids else ""

    if sweep_run_ids:
        sweep_values = [item for item in args.sweep_values.split() if item]
        for idx, run_id in enumerate(sweep_run_ids):
            paths = probe_paths(run_id)
            summary_rows = read_csv(paths["summary"])
            if not summary_rows:
                continue
            sweep_value = sweep_values[idx] if idx < len(sweep_values) else str(idx + 1)
            matrix_rows.append(
                normalize_sweep_row(
                    args.run_id,
                    run_id,
                    args.model,
                    args.sweep_axis,
                    sweep_value,
                    summary_rows[0],
                )
            )

    write_csv(out_dir / "microbenchmark_matrix.csv", matrix_rows, MATRIX_COLUMNS)
    write_csv(out_dir / "microbenchmark_summary.csv", [summary_row], SUMMARY_COLUMNS)
    write_summary_md(out_dir / "microbenchmark_summary.md", summary_row)
    with (out_dir / "run_contract.json").open("w", encoding="utf-8") as fh:
        json.dump(run_contract, fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
