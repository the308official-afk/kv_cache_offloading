#!/usr/bin/env python3
"""Build a consolidated cache-pinning microbenchmark report."""

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
    "row_kind",
    "run_id",
    "model",
    "kv_tier",
    "arm",
    "turn",
    "distractors",
    "cache_control",
    "ttl",
    "http_status",
    "latency_ms",
    "prompt_tokens",
    "cached_tokens",
    "cache_hit",
    "reuse_ratio",
    "warm",
    "first_ms",
    "replay_ms",
    "delta_ms",
    "speedup_x",
    "router_pin",
    "worker_pin",
    "worker_refreshes",
    "req_cache_status",
    "worker_cache_status",
    "replay_evicts",
    "replay_evict_status",
    "result",
    "reuse_signal",
]

SUMMARY_COLUMNS = [
    "benchmark_id",
    "mode",
    "model",
    "validate_run_id",
    "validate_result",
    "validate_turn1_ms",
    "validate_turn2_ms",
    "validate_turn2_cached",
    "validate_router_pin",
    "validate_worker_pin",
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
    parser.add_argument("--mode", required=True, choices=("validate", "sweep", "all", "plot"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--contract-sh", required=True)
    parser.add_argument("--contract-md", default="")
    parser.add_argument("--validate-run-id", default="")
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


def normalize_cache_hit(value: str) -> str:
    lowered = str(value).strip().lower()
    if lowered in {"hit", "true", "1", "yes"}:
        return "hit"
    if lowered in {"miss", "false", "0", "no"}:
        return "miss"
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
        "CACHE_PINNING_",
        "SGLANG_HICACHE_MAX_PINNED_RATIO",
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
        "validate_run_id": args.validate_run_id,
        "sweep_run_id": args.sweep_run_id,
        "contract_env": contract_env,
    }


def validate_paths(run_id: str) -> dict[str, Path]:
    root = Path("experiments/reports/cache_pinning_doc_validation") / run_id
    return {
        "root": root,
        "summary": root / "doc_validation_summary.csv",
        "requests": root / "doc_validation_requests.csv",
        "summary_md": root / "doc_validation_summary.md",
    }


def sweep_paths(run_id: str) -> dict[str, Path]:
    root = Path("experiments/reports/retention_threshold_sweeps") / run_id
    alt_root = Path("experiments/reports/cache_pinning_retention_threshold_sweeps") / run_id
    if alt_root.exists() and not root.exists():
        root = alt_root
    return {
        "root": root,
        "matrix": root / "retention_threshold_matrix.csv",
        "comparison": root / "retention_threshold_comparison.csv",
        "summary_md": root / "retention_threshold_summary.md",
    }


def matrix_rows_from_validate(
    microbenchmark_id: str,
    validate_run_id: str,
    summary_rows: list[dict[str, str]],
    request_rows: list[dict[str, str]],
    source_root: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary = summary_rows[0] if summary_rows else {}

    for request in request_rows:
        rows.append(
            {
                "benchmark_id": microbenchmark_id,
                "part": "validate",
                "row_kind": "validate_turn",
                "run_id": validate_run_id,
                "model": summary.get("model", ""),
                "kv_tier": "",
                "arm": "protected",
                "turn": request.get("turn", ""),
                "distractors": "",
                "cache_control": f"{summary.get('ttl', '') and 'ephemeral:' + summary.get('ttl', '')}",
                "ttl": summary.get("ttl", ""),
                "http_status": pick(request, "http_status"),
                "latency_ms": request.get("latency_ms", ""),
                "prompt_tokens": request.get("prompt_tokens", ""),
                "cached_tokens": request.get("cached_tokens", ""),
                "cache_hit": "hit" if request.get("cached_tokens", "") not in {"", "0"} else "miss",
                "reuse_ratio": "",
                "warm": "",
                "first_ms": "",
                "replay_ms": "",
                "delta_ms": "",
                "speedup_x": "",
                "router_pin": pick(summary, "router_pin", "router_pin_status"),
                "worker_pin": pick(summary, "worker_pin", "worker_pin_status"),
                "worker_refreshes": summary.get("worker_pin_refreshes", ""),
                "req_cache_status": "",
                "worker_cache_status": "",
                "replay_evicts": "",
                "replay_evict_status": "",
                "result": pick(summary, "result", "verdict"),
                "reuse_signal": "",
            }
        )

    if summary:
        rows.append(
            {
                "benchmark_id": microbenchmark_id,
                "part": "validate",
                "row_kind": "validate_summary",
                "run_id": validate_run_id,
                "model": summary.get("model", ""),
                "kv_tier": "",
                "arm": "protected",
                "turn": "turn2",
                "distractors": "",
                "cache_control": f"{summary.get('ttl', '') and 'ephemeral:' + summary.get('ttl', '')}",
                "ttl": summary.get("ttl", ""),
                "http_status": pick(summary, "turn2_status"),
                "latency_ms": summary.get("turn2_ms", ""),
                "prompt_tokens": "",
                "cached_tokens": summary.get("turn2_cached", ""),
                "cache_hit": normalize_cache_hit(summary.get("turn2_cache", "")),
                "reuse_ratio": "",
                "warm": "",
                "first_ms": summary.get("turn1_ms", ""),
                "replay_ms": summary.get("turn2_ms", ""),
                "delta_ms": "",
                "speedup_x": "",
                "router_pin": pick(summary, "router_pin", "router_pin_status"),
                "worker_pin": pick(summary, "worker_pin", "worker_pin_status"),
                "worker_refreshes": summary.get("worker_pin_refreshes", ""),
                "req_cache_status": "",
                "worker_cache_status": "",
                "replay_evicts": "",
                "replay_evict_status": "",
                "result": pick(summary, "result", "verdict"),
                "reuse_signal": "doc_validation",
            }
        )

    return rows


def matrix_rows_from_sweep(
    microbenchmark_id: str,
    sweep_run_id: str,
    matrix_rows: list[dict[str, str]],
    comparison_rows: list[dict[str, str]],
    source_root: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in matrix_rows:
        rows.append(
            {
                "benchmark_id": microbenchmark_id,
                "part": "sweep",
                "row_kind": "sweep_arm",
                "run_id": sweep_run_id,
                "model": row.get("model", ""),
                "kv_tier": pick(row, "kv_tier", "kv_tier_mode"),
                "arm": row.get("arm", ""),
                "turn": "replay",
                "distractors": pick(row, "distractors", "distractor_count"),
                "cache_control": pick(row, "cache_control", "protected_cache", "protected_cache_control_profile"),
                "ttl": "",
                "http_status": pick(row, "replay_http_status", "replay_status", "a_replay_status"),
                "latency_ms": pick(row, "replay_ms", "a_replay_latency_ms"),
                "prompt_tokens": "",
                "cached_tokens": pick(row, "replay_cached", "a_replay_cached_tokens"),
                "cache_hit": "hit" if pick(row, "replay_cached", "a_replay_cached_tokens") not in {"", "0"} else "miss",
                "reuse_ratio": pick(row, "replay_reuse", "a_replay_cache_reuse_ratio"),
                "warm": pick(row, "warm", "survived", "survived_effective"),
                "first_ms": pick(row, "first_ms", "a_first_latency_ms"),
                "replay_ms": pick(row, "replay_ms", "a_replay_latency_ms"),
                "delta_ms": pick(row, "delta_ms", "replay_delta_ms", "a_replay_latency_delta_ms"),
                "speedup_x": pick(row, "speedup_x", "replay_speedup", "a_replay_speedup_ratio"),
                "router_pin": "",
                "worker_pin": "",
                "worker_refreshes": "",
                "req_cache_status": pick(row, "req_cache_status", "request_cache_control_status"),
                "worker_cache_status": pick(row, "worker_cache_status", "worker_cache_control_status"),
                "replay_evicts": pick(row, "replay_evicts", "a_replay_sglang_cache_evict_events"),
                "replay_evict_status": pick(row, "replay_evict_status", "a_replay_sglang_evict_identity_status"),
                "result": pick(row, "result", "effect_status", "hint_runtime_effect_status"),
                "reuse_signal": pick(row, "reuse_signal", "reuse_status"),
            }
        )

    for row in comparison_rows:
        rows.append(
            {
                "benchmark_id": microbenchmark_id,
                "part": "sweep",
                "row_kind": "sweep_compare",
                "run_id": sweep_run_id,
                "model": row.get("model", ""),
                "kv_tier": pick(row, "kv_tier", "kv_tier_mode"),
                "arm": "compare",
                "turn": "",
                "distractors": "",
                "cache_control": pick(row, "protected_cache_control", "protected_cache_control_profile"),
                "ttl": "",
                "http_status": pick(row, "status", "sweep_status"),
                "latency_ms": "",
                "prompt_tokens": "",
                "cached_tokens": "",
                "cache_hit": "",
                "reuse_ratio": "",
                "warm": "",
                "first_ms": "",
                "replay_ms": "",
                "delta_ms": "",
                "speedup_x": "",
                "router_pin": "",
                "worker_pin": pick(row, "worker_cache_status", "worker_cache_control_status"),
                "worker_refreshes": "",
                "req_cache_status": "",
                "worker_cache_status": pick(row, "worker_cache_status", "worker_cache_control_status"),
                "replay_evicts": "",
                "replay_evict_status": "",
                "result": pick(row, "result", "hint_runtime_effect_status"),
                "reuse_signal": pick(row, "sweep_result", "interpretation"),
            }
        )

    return rows


def build_summary_row(
    microbenchmark_id: str,
    mode: str,
    model: str,
    validate_run_id: str,
    validate_summary_rows: list[dict[str, str]],
    sweep_run_id: str,
    sweep_comparison_rows: list[dict[str, str]],
    sweep_matrix_rows: list[dict[str, str]],
) -> dict[str, Any]:
    validate = validate_summary_rows[0] if validate_summary_rows else {}
    compare = sweep_comparison_rows[0] if sweep_comparison_rows else {}
    kv_tiers = sorted({pick(row, "kv_tier", "kv_tier_mode") for row in sweep_matrix_rows if pick(row, "kv_tier", "kv_tier_mode")})
    return {
        "benchmark_id": microbenchmark_id,
        "mode": mode,
        "model": model,
        "validate_run_id": validate_run_id,
        "validate_result": pick(validate, "result", "verdict"),
        "validate_turn1_ms": validate.get("turn1_ms", ""),
        "validate_turn2_ms": validate.get("turn2_ms", ""),
        "validate_turn2_cached": validate.get("turn2_cached", ""),
        "validate_router_pin": pick(validate, "router_pin", "router_pin_status"),
        "validate_worker_pin": pick(validate, "worker_pin", "worker_pin_status"),
        "sweep_run_id": sweep_run_id,
        "sweep_rows": str(len(sweep_matrix_rows)) if sweep_matrix_rows else "",
        "kv_tiers": "|".join(kv_tiers),
        "control_last_warm": pick(compare, "control_last_warm", "control_last_survived_distractor_count"),
        "control_first_cold": pick(compare, "control_first_cold", "control_first_evicted_distractor_count"),
        "protected_last_warm": pick(compare, "protected_last_warm", "protected_last_survived_distractor_count"),
        "protected_first_cold": pick(compare, "protected_first_cold", "protected_first_evicted_distractor_count"),
        "threshold_gap": pick(compare, "threshold_gap", "threshold_gap_distractors"),
        "sweep_result": pick(compare, "sweep_result", "interpretation"),
    }


def write_summary_md(
    path: Path,
    summary: dict[str, Any],
    contract_env: dict[str, str],
    contract_sh: str,
    contract_md: str,
) -> None:
    lines = [
        "# Cache-Pinning Microbenchmark Summary",
        "",
        "## Scope",
        "",
        f"- benchmark_id: `{summary['benchmark_id']}`",
        f"- mode: `{summary['mode']}`",
        f"- model: `{summary['model']}`",
        f"- contract_sh: `{Path(contract_sh).resolve()}`",
        f"- contract_md: `{Path(contract_md).resolve() if contract_md else ''}`",
        "",
        "## Validation",
        "",
        f"- validate_run_id: `{summary['validate_run_id']}`",
        f"- validate_result: `{summary['validate_result']}`",
        f"- validate_turn1_ms: `{summary['validate_turn1_ms']}`",
        f"- validate_turn2_ms: `{summary['validate_turn2_ms']}`",
        f"- validate_turn2_cached: `{summary['validate_turn2_cached']}`",
        f"- validate_router_pin: `{summary['validate_router_pin']}`",
        f"- validate_worker_pin: `{summary['validate_worker_pin']}`",
        "",
        "## Sweep",
        "",
        f"- sweep_run_id: `{summary['sweep_run_id']}`",
        f"- sweep_rows: `{summary['sweep_rows']}`",
        f"- kv_tiers: `{summary['kv_tiers']}`",
        f"- control_last_warm: `{summary['control_last_warm']}`",
        f"- control_first_cold: `{summary['control_first_cold']}`",
        f"- protected_last_warm: `{summary['protected_last_warm']}`",
        f"- protected_first_cold: `{summary['protected_first_cold']}`",
        f"- threshold_gap: `{summary['threshold_gap']}`",
        f"- sweep_result: `{summary['sweep_result']}`",
        "",
        "## Contract Knobs",
        "",
    ]
    for key in sorted(contract_env):
        lines.append(f"- {key}: `{contract_env[key]}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    contract_env = load_contract_env(Path(args.contract_sh))
    run_contract = build_run_contract(args, contract_env)
    (out_dir / "run_contract.json").write_text(json.dumps(run_contract, indent=2), encoding="utf-8")

    rows: list[dict[str, Any]] = []
    validate_summary_rows: list[dict[str, str]] = []
    sweep_matrix_rows: list[dict[str, str]] = []
    sweep_comparison_rows: list[dict[str, str]] = []

    if args.validate_run_id:
        paths = validate_paths(args.validate_run_id)
        validate_summary_rows = read_csv(paths["summary"])
        validate_request_rows = read_csv(paths["requests"])
        rows.extend(
            matrix_rows_from_validate(
                args.run_id,
                args.validate_run_id,
                validate_summary_rows,
                validate_request_rows,
                paths["root"],
            )
        )

    if args.sweep_run_id:
        paths = sweep_paths(args.sweep_run_id)
        sweep_matrix_rows = read_csv(paths["matrix"])
        sweep_comparison_rows = read_csv(paths["comparison"])
        rows.extend(
            matrix_rows_from_sweep(
                args.run_id,
                args.sweep_run_id,
                sweep_matrix_rows,
                sweep_comparison_rows,
                paths["root"],
            )
        )

    write_csv(out_dir / "microbenchmark_matrix.csv", rows, MATRIX_COLUMNS)
    summary_row = build_summary_row(
        args.run_id,
        args.mode,
        args.model,
        args.validate_run_id,
        validate_summary_rows,
        args.sweep_run_id,
        sweep_comparison_rows,
        sweep_matrix_rows,
    )
    write_csv(out_dir / "microbenchmark_summary.csv", [summary_row], SUMMARY_COLUMNS)
    write_summary_md(
        out_dir / "microbenchmark_summary.md",
        summary_row,
        contract_env,
        args.contract_sh,
        args.contract_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
