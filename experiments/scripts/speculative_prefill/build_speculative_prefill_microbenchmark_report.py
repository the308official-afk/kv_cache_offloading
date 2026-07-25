#!/usr/bin/env python3
"""Build a consolidated speculative-prefill microbenchmark report."""

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
    "arm",
    "spec_prefill",
    "prompt_isolation_mode",
    "request_source",
    "real_turn_b_mode",
    "comparison_mode",
    "turn_a_status",
    "turn_a_error",
    "turn_a_ms",
    "turn_a_ttft_ms",
    "turn_b_status",
    "turn_b_error",
    "turn_b_ms",
    "turn_b_ttft_ms",
    "turn_b_gain_ms",
    "turn_b_ttft_gain_ms",
    "turn_b_cached",
    "turn_b_reuse",
    "interturn_distractor_count",
    "interturn_distractor_success_count",
    "interturn_distractor_ms_total",
    "interturn_distractor_cached_total",
    "turn_a_prompt_family",
    "turn_b_prompt_family",
    "turn_a_prompt_hash",
    "turn_b_prompt_hash",
    "turn_a_source_instance_id",
    "turn_a_source_task_index",
    "turn_b_source_instance_id",
    "turn_b_source_task_index",
    "hint_status",
    "prefill_wrap",
    "prefill_spawned",
    "prefill_sent",
    "prefill_done",
    "prefill_target_seen",
    "prefill_tokens",
    "effect",
]

SUMMARY_COLUMNS = [
    "benchmark_id",
    "mode",
    "run_id",
    "model",
    "request_source",
    "real_turn_b_mode",
    "swebench_dataset",
    "swebench_split",
    "swebench_turn_a_index",
    "swebench_turn_b_index",
    "swebench_protected_offset",
    "comparison_mode",
    "probe_run_id",
    "sweep_axis",
    "sweep_values",
    "sweep_run_count",
    "prompt_isolation_mode",
    "turn_a_words",
    "turn_b_words",
    "output_tokens",
    "turn_a_output_tokens",
    "turn_b_output_tokens",
    "warmup_wait_ms",
    "stream_responses",
    "interturn_distractor_count",
    "interturn_distractor_start_index",
    "interturn_distractor_output_tokens",
    "control_turn_b_ms",
    "control_turn_b_ttft_ms",
    "protected_turn_b_ms",
    "protected_turn_b_ttft_ms",
    "turn_b_gain_ms",
    "turn_b_ttft_gain_ms",
    "control_turn_b_cached",
    "protected_turn_b_cached",
    "turn_b_cached_delta",
    "protected_prefill_done",
    "protected_prefill_target_seen",
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
        "SPEC_PREFILL_",
        "RETENTION_PROMPT_ISOLATION_MODE",
        "MODEL_READY_",
        "MODEL_SMOKE_",
        "MODEL_COOLDOWN_SECS",
        "WORKER_BASE_ARGS",
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
    root = Path("experiments/reports/speculative_prefill") / run_id
    return {
        "root": root,
        "matrix": root / "speculative_prefill_matrix.csv",
        "summary": root / "speculative_prefill_summary.csv",
        "summary_md": root / "speculative_prefill_summary.md",
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
                "arm": pick(row, "arm"),
                "spec_prefill": pick(row, "spec_prefill"),
                "prompt_isolation_mode": pick(row, "prompt_isolation_mode"),
                "request_source": pick(row, "request_source"),
                "real_turn_b_mode": pick(row, "real_turn_b_mode"),
                "turn_a_status": pick(row, "turn_a_status"),
                "turn_a_error": pick(row, "turn_a_error"),
                "turn_a_ms": pick(row, "turn_a_ms"),
                "turn_a_ttft_ms": pick(row, "turn_a_ttft_ms"),
                "turn_b_status": pick(row, "turn_b_status"),
                "turn_b_error": pick(row, "turn_b_error"),
                "turn_b_ms": pick(row, "turn_b_ms"),
                "turn_b_ttft_ms": pick(row, "turn_b_ttft_ms"),
                "turn_b_gain_ms": pick(row, "turn_b_latency_gain_ms"),
                "turn_b_ttft_gain_ms": pick(row, "turn_b_ttft_gain_ms"),
                "turn_b_cached": pick(row, "turn_b_cached"),
                "turn_b_reuse": pick(row, "turn_b_reuse"),
                "interturn_distractor_count": pick(row, "interturn_distractor_count"),
                "interturn_distractor_success_count": pick(row, "interturn_distractor_success_count"),
                "interturn_distractor_ms_total": pick(row, "interturn_distractor_ms_total"),
                "interturn_distractor_cached_total": pick(row, "interturn_distractor_cached_total"),
                "turn_a_prompt_family": pick(row, "turn_a_prompt_family"),
                "turn_b_prompt_family": pick(row, "turn_b_prompt_family"),
                "turn_a_prompt_hash": pick(row, "turn_a_prompt_hash"),
                "turn_b_prompt_hash": pick(row, "turn_b_prompt_hash"),
                "turn_a_source_instance_id": pick(row, "turn_a_source_instance_id"),
                "turn_a_source_task_index": pick(row, "turn_a_source_task_index"),
                "turn_b_source_instance_id": pick(row, "turn_b_source_instance_id"),
                "turn_b_source_task_index": pick(row, "turn_b_source_task_index"),
                "hint_status": pick(row, "hint_status"),
                "prefill_wrap": pick(row, "prefill_wrap"),
                "prefill_spawned": pick(row, "prefill_spawned"),
                "prefill_sent": pick(row, "prefill_sent"),
                "prefill_done": pick(row, "prefill_done"),
                "prefill_target_seen": pick(row, "prefill_target_seen"),
                "prefill_tokens": pick(row, "prefill_tokens"),
                "effect": pick(row, "effect_status"),
            }
        )
    return normalized


def normalize_sweep_matrix_rows(
    benchmark_id: str,
    run_id: str,
    model: str,
    sweep_axis: str,
    sweep_value: str,
    rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    normalized = normalize_matrix_rows(benchmark_id, run_id, model, rows)
    for row in normalized:
        row["part"] = "sweep"
        row["sweep_axis"] = sweep_axis
        row["sweep_value"] = sweep_value
    return normalized


def normalize_summary(benchmark_id: str, summary_row: dict[str, str]) -> dict[str, Any]:
    return {
        "benchmark_id": benchmark_id,
        "mode": pick(summary_row, "mode"),
        "run_id": pick(summary_row, "run_id"),
        "model": pick(summary_row, "model"),
        "request_source": pick(summary_row, "request_source"),
        "real_turn_b_mode": pick(summary_row, "real_turn_b_mode"),
        "swebench_dataset": pick(summary_row, "swebench_dataset"),
        "swebench_split": pick(summary_row, "swebench_split"),
        "swebench_turn_a_index": pick(summary_row, "swebench_turn_a_index"),
        "swebench_turn_b_index": pick(summary_row, "swebench_turn_b_index"),
        "swebench_protected_offset": pick(summary_row, "swebench_protected_offset"),
        "prompt_isolation_mode": pick(summary_row, "prompt_isolation_mode"),
        "turn_a_words": pick(summary_row, "turn_a_words"),
        "turn_b_words": pick(summary_row, "turn_b_words"),
        "output_tokens": pick(summary_row, "output_tokens"),
        "turn_a_output_tokens": pick(summary_row, "turn_a_output_tokens"),
        "turn_b_output_tokens": pick(summary_row, "turn_b_output_tokens"),
        "warmup_wait_ms": pick(summary_row, "warmup_wait_ms"),
        "stream_responses": pick(summary_row, "stream_responses"),
        "interturn_distractor_count": pick(summary_row, "interturn_distractor_count"),
        "interturn_distractor_start_index": pick(summary_row, "interturn_distractor_start_index"),
        "interturn_distractor_output_tokens": pick(summary_row, "interturn_distractor_output_tokens"),
        "control_turn_b_ms": pick(summary_row, "control_turn_b_ms"),
        "control_turn_b_ttft_ms": pick(summary_row, "control_turn_b_ttft_ms"),
        "protected_turn_b_ms": pick(summary_row, "protected_turn_b_ms"),
        "protected_turn_b_ttft_ms": pick(summary_row, "protected_turn_b_ttft_ms"),
        "turn_b_gain_ms": pick(summary_row, "turn_b_latency_delta_ms"),
        "turn_b_ttft_gain_ms": pick(summary_row, "turn_b_ttft_delta_ms"),
        "control_turn_b_cached": pick(summary_row, "control_turn_b_cached"),
        "protected_turn_b_cached": pick(summary_row, "protected_turn_b_cached"),
        "turn_b_cached_delta": pick(summary_row, "turn_b_cached_delta"),
        "protected_prefill_done": pick(summary_row, "protected_prefill_done"),
        "protected_prefill_target_seen": pick(summary_row, "protected_prefill_target_seen"),
        "effect": pick(summary_row, "effect_status"),
    }


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Speculative Prefill Microbenchmark",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- model: `{summary['model']}`",
        f"- request_source: `{summary['request_source']}`",
        f"- real_turn_b_mode: `{summary['real_turn_b_mode']}`",
        f"- swebench_dataset: `{summary['swebench_dataset']}`",
        f"- swebench_split: `{summary['swebench_split']}`",
        f"- swebench_turn_a_index: `{summary['swebench_turn_a_index']}`",
        f"- swebench_turn_b_index: `{summary['swebench_turn_b_index']}`",
        f"- swebench_protected_offset: `{summary['swebench_protected_offset']}`",
        f"- comparison_mode: `{summary['comparison_mode']}`",
        f"- probe_run_id: `{summary['probe_run_id']}`",
        f"- sweep_axis: `{summary['sweep_axis']}`",
        f"- sweep_values: `{summary['sweep_values']}`",
        f"- sweep_run_count: `{summary['sweep_run_count']}`",
        f"- prompt_isolation_mode: `{summary['prompt_isolation_mode']}`",
        f"- turn_a_words: `{summary['turn_a_words']}`",
        f"- turn_b_words: `{summary['turn_b_words']}`",
        f"- turn_a_output_tokens: `{summary['turn_a_output_tokens']}`",
        f"- turn_b_output_tokens: `{summary['turn_b_output_tokens']}`",
        f"- stream_responses: `{summary['stream_responses']}`",
        f"- interturn_distractor_count: `{summary['interturn_distractor_count']}`",
        f"- interturn_distractor_start_index: `{summary['interturn_distractor_start_index']}`",
        f"- interturn_distractor_output_tokens: `{summary['interturn_distractor_output_tokens']}`",
        f"- control_turn_b_ms: `{summary['control_turn_b_ms']}`",
        f"- protected_turn_b_ms: `{summary['protected_turn_b_ms']}`",
        f"- turn_b_gain_ms: `{summary['turn_b_gain_ms']}`",
        f"- control_turn_b_ttft_ms: `{summary['control_turn_b_ttft_ms']}`",
        f"- protected_turn_b_ttft_ms: `{summary['protected_turn_b_ttft_ms']}`",
        f"- turn_b_ttft_gain_ms: `{summary['turn_b_ttft_gain_ms']}`",
        f"- protected_turn_b_cached: `{summary['protected_turn_b_cached']}`",
        f"- protected_prefill_done: `{summary['protected_prefill_done']}`",
        f"- protected_prefill_target_seen: `{summary['protected_prefill_target_seen']}`",
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
    comparison_mode = contract_env.get("SPEC_PREFILL_COMPARISON_MODE", "")

    matrix_rows: list[dict[str, Any]] = []
    summary_row = {column: "" for column in SUMMARY_COLUMNS}
    summary_row["benchmark_id"] = args.run_id
    summary_row["mode"] = args.mode
    summary_row["model"] = args.model
    summary_row["probe_run_id"] = args.probe_run_id
    summary_row["sweep_axis"] = args.sweep_axis
    summary_row["sweep_values"] = args.sweep_values
    summary_row["comparison_mode"] = comparison_mode

    sweep_run_ids = [item for item in args.sweep_run_ids.split(",") if item]
    summary_row["sweep_run_count"] = str(len(sweep_run_ids)) if sweep_run_ids else ""

    if args.probe_run_id:
        paths = probe_paths(args.probe_run_id)
        source_matrix = read_csv(paths["matrix"])
        source_summary = read_csv(paths["summary"])
        matrix_rows.extend(normalize_matrix_rows(args.run_id, args.probe_run_id, args.model, source_matrix))
        if source_summary:
            summary_row = normalize_summary(args.run_id, source_summary[0])
            summary_row["probe_run_id"] = args.probe_run_id
            summary_row["sweep_axis"] = args.sweep_axis
            summary_row["sweep_values"] = args.sweep_values
            summary_row["sweep_run_count"] = str(len(sweep_run_ids)) if sweep_run_ids else ""
            summary_row["comparison_mode"] = comparison_mode

    if sweep_run_ids:
        sweep_values = [item for item in args.sweep_values.split() if item]
        for idx, run_id in enumerate(sweep_run_ids):
            paths = probe_paths(run_id)
            source_matrix = read_csv(paths["matrix"])
            if not source_matrix:
                continue
            sweep_value = sweep_values[idx] if idx < len(sweep_values) else str(idx + 1)
            matrix_rows.extend(
                normalize_sweep_matrix_rows(
                    args.run_id,
                    run_id,
                    args.model,
                    args.sweep_axis,
                    sweep_value,
                    source_matrix,
                )
            )

    for row in matrix_rows:
        row["comparison_mode"] = comparison_mode
    summary_row["comparison_mode"] = comparison_mode

    write_csv(out_dir / "microbenchmark_matrix.csv", matrix_rows, MATRIX_COLUMNS)
    write_csv(out_dir / "microbenchmark_summary.csv", [summary_row], SUMMARY_COLUMNS)
    write_summary_md(out_dir / "microbenchmark_summary.md", summary_row)
    with (out_dir / "run_contract.json").open("w", encoding="utf-8") as fh:
        json.dump(run_contract, fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
