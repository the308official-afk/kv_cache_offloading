#!/usr/bin/env python3
"""Build a consolidated KV retention microbenchmark report."""

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
    "run_id",
    "model",
    "kv_tier",
    "arm",
    "hint_profile",
    "cache_control",
    "distractors",
    "first_status",
    "replay_status",
    "first_ms",
    "replay_ms",
    "delta_ms",
    "speedup_x",
    "replay_cached",
    "replay_reuse",
    "warm",
    "warm_source",
    "req_prio_status",
    "worker_prio_status",
    "replay_evicts",
    "replay_evict_cache",
    "replay_evict_status",
    "result",
]

SUMMARY_COLUMNS = [
    "benchmark_id",
    "mode",
    "model",
    "probe_run_id",
    "probe_rows",
    "probe_result",
    "probe_protected_replay_ms",
    "probe_protected_replay_cached",
    "probe_worker_prio",
    "sweep_run_id",
    "sweep_rows",
    "kv_tiers",
    "control_last_warm",
    "control_first_cold",
    "protected_last_warm",
    "protected_first_cold",
    "threshold_gap",
    "sweep_result",
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
    parser.add_argument("--sweep-run-id", default="")
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


def as_int(value: Any) -> int | None:
    try:
        if value in ("", None):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def infer_arm(row: dict[str, str]) -> str:
    arm = pick(row, "arm")
    if arm:
        return arm
    if "is_control" in row:
        return "control" if boolish(pick(row, "is_control")) else "protected"
    hint_profile = pick(row, "hint_profile", "protected_hint_profile").strip().lower()
    cache_control = pick(row, "protected_cache", "protected_cache_control_profile").strip().lower()
    if hint_profile in {"", "none"} and cache_control in {"", "off", "none"}:
        return "control"
    return "protected"


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
        "KV_RETENTION_",
        "RETENTION_",
        "CONTROL_",
        "PROTECTED_",
        "DISTRACTOR_",
        "CACHE_CONTROL_",
        "GPU_",
        "HICACHE_",
        "WORKER_",
        "SGLANG_TRANSFER_",
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
        "sweep_run_id": args.sweep_run_id,
        "contract_env": contract_env,
    }


def probe_paths(run_id: str) -> dict[str, Path]:
    root = Path("experiments/reports/retention_probe_batches") / run_id
    return {
        "root": root,
        "matrix": root / "design_space_retention_matrix.csv",
        "progress": root / "retention_probe_progress.csv",
        "summary_md": root / "retention_probe_batch_summary.md",
    }


def sweep_paths(run_id: str) -> dict[str, Path]:
    root = Path("experiments/reports/retention_threshold_sweeps") / run_id
    return {
        "root": root,
        "matrix": root / "retention_threshold_matrix.csv",
        "comparison": root / "retention_threshold_comparison.csv",
        "summary_md": root / "retention_threshold_summary.md",
    }


def normalize_probe_rows(
    benchmark_id: str,
    probe_run_id: str,
    rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "benchmark_id": benchmark_id,
                "part": "probe",
                "run_id": probe_run_id,
                "model": pick(row, "model"),
                "kv_tier": pick(row, "kv_tier", "kv_tier_mode"),
                "arm": infer_arm(row),
                "hint_profile": pick(row, "hint_profile", "protected_hint_profile"),
                "cache_control": pick(row, "protected_cache", "protected_cache_control_profile"),
                "distractors": pick(row, "distractors", "distractor_count"),
                "first_status": pick(row, "first_status", "a_first_status"),
                "replay_status": pick(row, "replay_status", "a_replay_status"),
                "first_ms": pick(row, "first_ms", "a_first_latency_ms"),
                "replay_ms": pick(row, "replay_ms", "a_replay_latency_ms"),
                "delta_ms": pick(row, "replay_delta_ms", "a_replay_latency_delta_ms"),
                "speedup_x": pick(row, "replay_speedup", "a_replay_speedup_ratio"),
                "replay_cached": pick(row, "replay_cached", "a_replay_cached_tokens"),
                "replay_reuse": pick(row, "replay_reuse", "a_replay_cache_reuse_ratio"),
                "warm": pick(row, "warm", "survived", "survived_effective", "a_survived_cache_threshold"),
                "warm_source": pick(row, "warm_source", "survival_source", "effective_survival_source", "cache_survival_source"),
                "req_prio_status": pick(row, "req_prio_status", "request_agent_hints_priority_status"),
                "worker_prio_status": pick(row, "worker_prio_status", "worker_priority_path_status"),
                "replay_evicts": pick(row, "replay_evicts", "a_replay_sglang_cache_evict_events"),
                "replay_evict_cache": pick(row, "replay_evict_cache", "a_replay_sglang_evict_cache_control_values"),
                "replay_evict_status": pick(row, "replay_evict_status", "a_replay_sglang_evict_identity_status"),
                "result": pick(row, "effect_status", "hint_runtime_effect_status"),
            }
        )
    return normalized


def normalize_sweep_rows(
    benchmark_id: str,
    sweep_run_id: str,
    rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        arm = infer_arm(row)
        normalized.append(
            {
                "benchmark_id": benchmark_id,
                "part": "sweep",
                "run_id": sweep_run_id,
                "model": pick(row, "model"),
                "kv_tier": pick(row, "kv_tier", "kv_tier_mode"),
                "arm": arm,
                "hint_profile": pick(row, "hint_profile", "protected_hint_profile"),
                "cache_control": pick(row, "protected_cache", "protected_cache_control_profile"),
                "distractors": pick(row, "distractors", "distractor_count"),
                "first_status": pick(row, "first_status", "a_first_status"),
                "replay_status": pick(row, "replay_status", "a_replay_status"),
                "first_ms": pick(row, "first_ms", "a_first_latency_ms"),
                "replay_ms": pick(row, "replay_ms", "a_replay_latency_ms"),
                "delta_ms": pick(row, "replay_delta_ms", "a_replay_latency_delta_ms"),
                "speedup_x": pick(row, "replay_speedup", "a_replay_speedup_ratio"),
                "replay_cached": pick(row, "replay_cached", "a_replay_cached_tokens"),
                "replay_reuse": pick(row, "replay_reuse", "a_replay_cache_reuse_ratio"),
                "warm": pick(row, "warm", "survived", "survived_effective"),
                "warm_source": pick(row, "warm_source", "survival_source", "effective_survival_source"),
                "req_prio_status": pick(
                    row,
                    "req_prio_status",
                    "request_agent_hints_priority_status",
                    "request_top_level_priority_status",
                ),
                "worker_prio_status": pick(row, "worker_prio_status", "worker_priority_path_status"),
                "replay_evicts": pick(row, "replay_evicts", "a_replay_sglang_cache_evict_events"),
                "replay_evict_cache": pick(row, "replay_evict_cache", "a_replay_sglang_evict_cache_control_values"),
                "replay_evict_status": pick(row, "replay_evict_status", "a_replay_sglang_evict_identity_status"),
                "result": pick(row, "effect_status", "hint_runtime_effect_status"),
            }
        )
    return normalized


def summarize_probe(probe_rows: list[dict[str, Any]]) -> dict[str, str]:
    protected = next((row for row in probe_rows if row.get("arm") == "protected"), {})
    results = {row.get("result", "") for row in probe_rows if row.get("result")}
    if "survived" in results or boolish(protected.get("warm", "")):
        result = "protected_replay_survived"
    elif "unknown" in results and len(results) == 1:
        result = "unknown"
    elif results:
        result = "|".join(sorted(results))
    else:
        result = "not_run"
    return {
        "probe_rows": str(len(probe_rows)),
        "probe_result": result,
        "probe_protected_replay_ms": str(protected.get("replay_ms", "")),
        "probe_protected_replay_cached": str(protected.get("replay_cached", "")),
        "probe_worker_prio": str(protected.get("worker_prio_status", "")),
    }


def summarize_sweep_comparisons(comparison_rows: list[dict[str, str]]) -> dict[str, str]:
    if not comparison_rows:
        return {
            "sweep_rows": "0",
            "kv_tiers": "",
            "control_last_warm": "",
            "control_first_cold": "",
            "protected_last_warm": "",
            "protected_first_cold": "",
            "threshold_gap": "",
            "sweep_result": "not_run",
        }

    kv_tiers = sorted({pick(row, "kv_tier", "kv_tier_mode") for row in comparison_rows if pick(row, "kv_tier", "kv_tier_mode")})
    control_last = []
    control_first = []
    protected_last = []
    protected_first = []
    threshold_gaps = []
    interpretations = []

    for row in comparison_rows:
        kv_tier = pick(row, "kv_tier", "kv_tier_mode")
        prefix = f"{kv_tier}:" if kv_tier else ""
        value = pick(row, "control_last_warm", "control_last_survived_distractor_count")
        if value:
            control_last.append(f"{prefix}{value}")
        value = pick(row, "control_first_cold", "control_first_evicted_distractor_count")
        if value:
            control_first.append(f"{prefix}{value}")
        value = pick(row, "protected_last_warm", "protected_last_survived_distractor_count")
        if value:
            protected_last.append(f"{prefix}{value}")
        value = pick(row, "protected_first_cold", "protected_first_evicted_distractor_count")
        if value:
            protected_first.append(f"{prefix}{value}")
        value = pick(row, "threshold_gap", "threshold_gap_distractors")
        if value:
            threshold_gaps.append(f"{prefix}{value}")
        interpretation = pick(row, "sweep_result", "interpretation", "result", "hint_runtime_effect_status")
        if interpretation:
            interpretations.append(f"{prefix}{interpretation}")

    return {
        "sweep_rows": str(len(comparison_rows)),
        "kv_tiers": ",".join(kv_tiers),
        "control_last_warm": "|".join(control_last),
        "control_first_cold": "|".join(control_first),
        "protected_last_warm": "|".join(protected_last),
        "protected_first_cold": "|".join(protected_first),
        "threshold_gap": "|".join(threshold_gaps),
        "sweep_result": "|".join(interpretations),
    }


def build_summary_row(
    benchmark_id: str,
    mode: str,
    model: str,
    probe_run_id: str,
    probe_rows: list[dict[str, Any]],
    sweep_run_id: str,
    sweep_comparison_rows: list[dict[str, str]],
) -> dict[str, str]:
    row = {
        "benchmark_id": benchmark_id,
        "mode": mode,
        "model": model,
        "probe_run_id": probe_run_id,
        "probe_rows": "0",
        "probe_result": "not_run",
        "probe_protected_replay_ms": "",
        "probe_protected_replay_cached": "",
        "probe_worker_prio": "",
        "sweep_run_id": sweep_run_id,
        "sweep_rows": "0",
        "kv_tiers": "",
        "control_last_warm": "",
        "control_first_cold": "",
        "protected_last_warm": "",
        "protected_first_cold": "",
        "threshold_gap": "",
        "sweep_result": "not_run",
    }
    row.update(summarize_probe(probe_rows))
    row.update(summarize_sweep_comparisons(sweep_comparison_rows))
    return row


def write_summary_md(
    path: Path,
    args: argparse.Namespace,
    summary_row: dict[str, str],
    matrix_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# KV Retention Microbenchmark",
        "",
        f"- benchmark_id: `{args.run_id}`",
        f"- mode: `{args.mode}`",
        f"- model: `{args.model}`",
        f"- probe_run_id: `{args.probe_run_id or 'not_run'}`",
        f"- sweep_run_id: `{args.sweep_run_id or 'not_run'}`",
        "",
        "## Summary",
        "",
        f"- Probe rows: `{summary_row.get('probe_rows', '')}`",
        f"- Probe result: `{summary_row.get('probe_result', '')}`",
        f"- Protected replay ms: `{summary_row.get('probe_protected_replay_ms', '')}`",
        f"- Protected replay cached: `{summary_row.get('probe_protected_replay_cached', '')}`",
        f"- Probe worker priority proof: `{summary_row.get('probe_worker_prio', '')}`",
        f"- Sweep rows: `{summary_row.get('sweep_rows', '')}`",
        f"- KV tiers: `{summary_row.get('kv_tiers', '')}`",
        f"- Control last warm: `{summary_row.get('control_last_warm', '')}`",
        f"- Control first cold: `{summary_row.get('control_first_cold', '')}`",
        f"- Protected last warm: `{summary_row.get('protected_last_warm', '')}`",
        f"- Protected first cold: `{summary_row.get('protected_first_cold', '')}`",
        f"- Threshold gap: `{summary_row.get('threshold_gap', '')}`",
        f"- Sweep result: `{summary_row.get('sweep_result', '')}`",
        "",
        "## Files",
        "",
        f"- Matrix CSV: `{path.parent / 'microbenchmark_matrix.csv'}`",
        f"- Summary CSV: `{path.parent / 'microbenchmark_summary.csv'}`",
        f"- Run contract: `{path.parent / 'run_contract.json'}`",
        "",
        "## Notes",
        "",
        "- This microbenchmark matrix is the normalized public view over the current",
        "  retention probe and retention threshold sweep helpers.",
        f"- Rows included: `{len(matrix_rows)}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    contract_env = load_contract_env(Path(args.contract_sh).resolve())
    run_contract = build_run_contract(args, contract_env)

    probe_matrix_rows: list[dict[str, Any]] = []
    sweep_matrix_rows: list[dict[str, Any]] = []
    sweep_comparison_rows: list[dict[str, str]] = []

    if args.probe_run_id:
        probe_matrix = probe_paths(args.probe_run_id)["matrix"]
        probe_matrix_rows = normalize_probe_rows(args.run_id, args.probe_run_id, read_csv(probe_matrix))

    if args.sweep_run_id:
        paths = sweep_paths(args.sweep_run_id)
        sweep_matrix_rows = normalize_sweep_rows(args.run_id, args.sweep_run_id, read_csv(paths["matrix"]))
        sweep_comparison_rows = read_csv(paths["comparison"])

    matrix_rows = probe_matrix_rows + sweep_matrix_rows
    matrix_path = out_dir / "microbenchmark_matrix.csv"
    summary_csv_path = out_dir / "microbenchmark_summary.csv"
    summary_md_path = out_dir / "microbenchmark_summary.md"
    run_contract_path = out_dir / "run_contract.json"

    write_csv(matrix_path, matrix_rows, MATRIX_COLUMNS)

    summary_row = build_summary_row(
        args.run_id,
        args.mode,
        args.model,
        args.probe_run_id,
        probe_matrix_rows,
        args.sweep_run_id,
        sweep_comparison_rows,
    )
    write_csv(summary_csv_path, [summary_row], SUMMARY_COLUMNS)
    write_summary_md(summary_md_path, args, summary_row, matrix_rows)

    with run_contract_path.open("w", encoding="utf-8") as handle:
        json.dump(run_contract, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"matrix: {matrix_path}")
    print(f"summary csv: {summary_csv_path}")
    print(f"summary md: {summary_md_path}")
    print(f"run contract: {run_contract_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
