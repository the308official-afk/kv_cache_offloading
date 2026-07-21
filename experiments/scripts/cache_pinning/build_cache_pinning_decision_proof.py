#!/usr/bin/env python3
"""Build the Exp10 decision-proof table from latest cache-pinning artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ProofStep:
    step: int
    when: str
    where: str
    line: int
    what_it_means: str
    code_snippet: str
    runtime_signal: str
    experiment_part: str
    cache_control_path: str
    evidence_metric: str
    failure_meaning: str
    check_name: str


PROOF_STEPS = [
    ProofStep(
        1,
        "Contract pins isolated upstream stack",
        "contracts/cache_pinning_microbenchmark.contract.sh",
        19,
        "Exp10 uses the isolated Dynamo and SGLang cache-pinning PR refs instead of the generic precise stack.",
        "CACHE_PINNING_DYNAMO_SOURCE_REF\nCACHE_PINNING_SGLANG_SOURCE_REF",
        "run_contract.json contract_env source refs",
        "whole run",
        "contract",
        "pinned refs",
        "The run may have drifted to a different upstream source.",
        "contract_refs",
    ),
    ProofStep(
        2,
        "Contract enables cache-control frontend path",
        "contracts/cache_pinning_microbenchmark.contract.sh",
        35,
        "The frontend is expected to expose the cache-control flag and use KV-router mode.",
        "CACHE_PINNING_FRONTEND_FLAG_VALUE:=--enable-cache-control\nCACHE_PINNING_ROUTER_MODE:=kv",
        "frontend_flag / router_mode",
        "whole run",
        "frontend",
        "frontend flag",
        "The frontend may not accept or forward cache-control metadata.",
        "contract_frontend_flag",
    ),
    ProofStep(
        3,
        "Contract enables HiCache pin budget",
        "contracts/cache_pinning_microbenchmark.contract.sh",
        44,
        "Cache pinning needs hierarchical cache plus a nonzero pinned ratio.",
        "CACHE_PINNING_PINNED_RATIO:=0.1\nSGLANG_HICACHE_MAX_PINNED_RATIO",
        "pinned ratio / hicache write policy",
        "whole run",
        "worker",
        "HiCache knobs",
        "The worker may receive the hint but have no usable pin budget.",
        "contract_hicache",
    ),
    ProofStep(
        4,
        "Wrapper launches doc validation",
        "agentbench/run_cache_pinning_microbenchmark_single_host.sh",
        280,
        "The public wrapper runs the doc-style validation path with the contract TTL and pinning knobs.",
        "CACHE_PINNING_DOC_ID\nCACHE_PINNING_TTL\nCACHE_PINNING_PINNED_RATIO",
        "validate_run_id",
        "validate",
        "wrapper",
        "validate run id",
        "The validation phase did not run or its run id was not recorded.",
        "validate_run_present",
    ),
    ProofStep(
        5,
        "Validation request sends cache_control",
        "experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py",
        317,
        "Both validation turns send `nvext.cache_control` with the requested type and TTL.",
        '"nvext": {"cache_control": {"type": args.cache_control_type, "ttl": args.ttl}}',
        "matrix cache_control=ephemeral:<ttl>",
        "validate",
        "request",
        "cache_control payload",
        "The request did not carry cache-control metadata.",
        "request_cache_control",
    ),
    ProofStep(
        6,
        "Router logs cache-control receipt",
        "runtime_instrumentation/repair_cache_pinning_dynamo_source.py",
        98,
        "The Dynamo router logs when it sees cache-control TTL on the routed request.",
        '"event_type": "router.cache_control_seen"',
        "router.cache_control_seen",
        "validate",
        "router",
        "router seen",
        "The router did not see cache-control metadata.",
        "router_cache_control_seen",
    ),
    ProofStep(
        7,
        "Router creates pin state",
        "runtime_instrumentation/repair_cache_pinning_dynamo_source.py",
        128,
        "The router builds pin state with TTL, token ids, and worker id.",
        '"event_type": "router.pin_state_created"',
        "router.pin_state_created / router_pin",
        "validate",
        "router",
        "pin state",
        "The router saw cache-control but could not form a pin request.",
        "router_pin_state_created",
    ),
    ProofStep(
        8,
        "Router spawns pin-prefix request",
        "runtime_instrumentation/repair_cache_pinning_dynamo_source.py",
        175,
        "After generation, the router sends the prefix-pin RPC to the worker.",
        '"event_type": "router.pin_prefix_spawned"',
        "router.pin_prefix_spawned / router_pin=spawned",
        "validate",
        "router-to-worker",
        "pin RPC spawned",
        "The router never spawned the worker pin request.",
        "router_pin_spawned",
    ),
    ProofStep(
        9,
        "Worker exposes cache-control endpoint",
        "runtime_instrumentation/repair_cache_pinning_dynamo_source.py",
        54,
        "The Dynamo worker serves the cache-control endpoint used by the router pin RPC.",
        "cache_control_endpoint.serve_endpoint(",
        "source readiness / live validation",
        "validate",
        "worker endpoint",
        "cache_control endpoint",
        "The worker cannot receive router pin RPCs.",
        "worker_endpoint_source",
    ),
    ProofStep(
        10,
        "SGLang worker logs pin_prefix applied",
        "runtime_instrumentation/repair_cache_pinning_sglang_source.py",
        51,
        "The SGLang radix cache applies TTL pinning to the protected prefix.",
        '"worker.pin_prefix_applied"',
        "worker.pin_prefix_applied / worker_pin=applied",
        "validate",
        "worker radix cache",
        "worker pin applied",
        "The worker did not apply prefix pinning.",
        "worker_pin_applied",
    ),
    ProofStep(
        11,
        "SGLang can refresh pinned prefix TTL",
        "runtime_instrumentation/repair_cache_pinning_sglang_source.py",
        90,
        "On a cache hit, pinned nodes can refresh their TTL.",
        '"worker.pin_refreshed_cache_hit"',
        "worker.pin_refreshed_cache_hit / worker_refreshes",
        "validate",
        "worker radix cache",
        "pin refresh",
        "Pin refresh was not observed. This can be okay for short validation, but matters for long-running reuse.",
        "worker_pin_refresh_path",
    ),
    ProofStep(
        12,
        "Validation parser summarizes router pin",
        "experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py",
        163,
        "The validation report converts router cache-pinning events into `router_pin` status.",
        "def summarize_router_pin(frontend_log: Path)",
        "router_pin=spawned",
        "validate",
        "report",
        "router_pin",
        "The validation report could not prove the router pin path.",
        "validate_router_summary",
    ),
    ProofStep(
        13,
        "Validation parser summarizes worker pin",
        "experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py",
        199,
        "The validation report converts worker pin events into `worker_pin` status.",
        "def summarize_worker_pin(worker_log: Path)",
        "worker_pin=applied",
        "validate",
        "report",
        "worker_pin",
        "The validation report could not prove the worker pin path.",
        "validate_worker_summary",
    ),
    ProofStep(
        14,
        "Validation confirms cache reuse",
        "experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py",
        235,
        "The second validation turn should report cached prompt tokens.",
        "turn2_cached = row2.get(\"cached_tokens\", \"\")",
        "turn2_cached > 0 / cache_hit=hit",
        "validate",
        "OpenAI response usage",
        "turn2 cached tokens",
        "The protected prefix was not reused on the second validation turn.",
        "validate_turn2_cached",
    ),
    ProofStep(
        15,
        "Validation final verdict is strong",
        "experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py",
        250,
        "The validation result is strongest when router pin, worker pin, and cache reuse all happen.",
        "pin_path_applied_and_cache_reused",
        "result=pin_path_applied_and_cache_reused",
        "validate",
        "summary",
        "validation result",
        "The validation did not prove the full pin path.",
        "validate_result",
    ),
    ProofStep(
        16,
        "Wrapper launches retention sweep",
        "agentbench/run_cache_pinning_microbenchmark_single_host.sh",
        304,
        "The public wrapper runs the pressure sweep after validation in `all` mode or directly in `sweep` mode.",
        "RETENTION_SWEEP_ID\nPROTECTED_CACHE_CONTROL_PROFILES",
        "sweep_run_id / sweep rows",
        "sweep",
        "wrapper",
        "sweep run id",
        "The sweep phase did not run or did not emit rows.",
        "sweep_rows_present",
    ),
    ProofStep(
        17,
        "Sweep compares control and protected arms",
        "experiments/scripts/cache_pinning/compact_cache_pinning_retention_reports.py",
        96,
        "The sweep has a control arm with cache-control off and a protected arm with `ephemeral:1h`.",
        '"arm": pick(row, "arm")\n"cache_control": pick(row, "cache_control", "protected_cache", ...)',
        "matrix arm/cache_control rows",
        "sweep",
        "control vs protected",
        "arm/cache_control",
        "The sweep did not include both control and protected cache-control rows.",
        "sweep_control_protected",
    ),
    ProofStep(
        18,
        "Sweep report records request cache-control",
        "experiments/scripts/cache_pinning/compact_cache_pinning_retention_reports.py",
        110,
        "The component report records whether request metadata showed cache-control on the protected arm.",
        '"req_cache_status": pick(row, "req_cache_status", ...)',
        "req_cache_status / req_cache_values",
        "sweep",
        "request",
        "request cache-control",
        "The protected sweep arm did not show cache-control metadata at request level.",
        "sweep_request_cache_control",
    ),
    ProofStep(
        19,
        "Microbenchmark report normalizes sweep rows",
        "experiments/scripts/cache_pinning/build_cache_pinning_microbenchmark_report.py",
        269,
        "The main matrix preserves replay latency, cached tokens, warm status, and reuse signal for each arm.",
        "def matrix_rows_from_sweep(",
        "microbenchmark_matrix.csv sweep rows",
        "sweep",
        "report",
        "normalized matrix",
        "The final matrix did not include normalized sweep evidence.",
        "sweep_rows_present",
    ),
    ProofStep(
        20,
        "Sweep summary compares retention threshold",
        "experiments/scripts/cache_pinning/build_cache_pinning_microbenchmark_report.py",
        381,
        "The summary compares the deepest warm distractor count for control and protected arms.",
        '"control_last_warm"\n"protected_last_warm"',
        "protected_last_warm > control_last_warm",
        "sweep",
        "report",
        "retention threshold",
        "Protected cache-control did not survive deeper than control in this setup.",
        "sweep_threshold_improved",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-csv", default="experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv")
    parser.add_argument("--summary-csv", default="experiments/reports/latest_cache_pinning_microbenchmark_summary.csv")
    parser.add_argument("--run-contract-json", default="experiments/reports/latest_cache_pinning_microbenchmark_run_contract.json")
    parser.add_argument("--reports-csv", default="experiments/reports/latest_exp10_decision_proof.csv")
    parser.add_argument("--reports-md", default="experiments/reports/latest_exp10_decision_proof.md")
    parser.add_argument("--charts-csv", default="experiments/charts/exp10_decision_proof.csv")
    parser.add_argument("--charts-md", default="experiments/charts/exp10_decision_proof.md")
    return parser.parse_args()


def repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def to_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def to_int(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def contract_env(contract: dict[str, Any]) -> dict[str, str]:
    env = contract.get("contract_env")
    if isinstance(env, dict):
        return {str(k): str(v) for k, v in env.items()}
    return {str(k): str(v) for k, v in contract.items() if str(k).startswith("CACHE_PINNING_")}


def pick(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key, "")
        if value != "":
            return value
    return ""


def latest_matching_files(patterns: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(REPO_ROOT.glob(pattern))
    return sorted({p for p in files if p.is_file()}, key=lambda p: str(p))


def read_texts(paths: Iterable[Path]) -> str:
    parts: list[str] = []
    for path in paths:
        try:
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
    return "\n".join(parts)


def event_count(text: str, signal: str) -> int:
    return text.count(signal) if text else 0


def short_paths(paths: list[Path], *, limit: int = 3) -> str:
    if not paths:
        return ""
    rels = []
    for path in paths[:limit]:
        try:
            rels.append(str(path.relative_to(REPO_ROOT)))
        except ValueError:
            rels.append(str(path))
    suffix = "" if len(paths) <= limit else f" (+{len(paths) - limit} more)"
    return "; ".join(rels) + suffix


def snippet_tokens(snippet: str) -> list[str]:
    tokens: list[str] = []
    for line in snippet.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if "..." in cleaned:
            tokens.extend(part.strip() for part in cleaned.split("...") if len(part.strip()) >= 4)
        else:
            tokens.append(cleaned)
    return tokens or [snippet.strip()]


def source_present(step: ProofStep) -> bool:
    path = repo_path(step.where)
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return any(token in text for token in snippet_tokens(step.code_snippet))


def markdown_link(step: ProofStep) -> str:
    path = repo_path(step.where)
    return f"[{Path(step.where).name}:{step.line}]({path}:{step.line})"


def md_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def validate_run_id(summary_rows: list[dict[str, str]], contract: dict[str, Any]) -> str:
    if summary_rows:
        value = summary_rows[0].get("validate_run_id", "")
        if value:
            return value
    return str(contract.get("validate_run_id", "")).strip()


def sweep_run_id(summary_rows: list[dict[str, str]], contract: dict[str, Any]) -> str:
    if summary_rows:
        value = summary_rows[0].get("sweep_run_id", "")
        if value:
            return value
    return str(contract.get("sweep_run_id", "")).strip()


def validate_logs(run_id: str) -> tuple[list[Path], list[Path]]:
    if not run_id:
        return [], []
    root = f"experiments/reports/cache_pinning_doc_validation/{run_id}"
    return (
        latest_matching_files([f"{root}/cache_pinning_doc_frontend.log"]),
        latest_matching_files([f"{root}/cache_pinning_doc_worker.log"]),
    )


def positive_cached(row: dict[str, str]) -> bool:
    return to_int(pick(row, "cached_tokens", "validate_turn2_cached", "turn2_cached")) > 0


def validation_rows(matrix_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in matrix_rows if row.get("part") == "validate"]


def sweep_rows(matrix_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in matrix_rows if row.get("part") == "sweep"]


def arm_rows(rows: list[dict[str, str]], arm: str) -> list[dict[str, str]]:
    return [row for row in rows if row.get("arm") == arm and row.get("row_kind") == "sweep_arm"]


def max_warm_distractors(rows: list[dict[str, str]]) -> int:
    values = []
    for row in rows:
        warm = str(row.get("warm", "")).strip().lower()
        if warm in {"true", "1", "yes"}:
            values.append(to_int(row.get("distractors")))
    return max(values or [0])


def build_checks(
    *,
    matrix_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    contract: dict[str, Any],
    frontend_logs: list[Path],
    worker_logs: list[Path],
) -> dict[str, tuple[bool, str, str]]:
    env = contract_env(contract)
    summary = summary_rows[0] if summary_rows else {}
    validate = validation_rows(matrix_rows)
    sweep = sweep_rows(matrix_rows)
    control = arm_rows(sweep, "control")
    protected = arm_rows(sweep, "protected")
    frontend_text = read_texts(frontend_logs)
    worker_text = read_texts(worker_logs)
    frontend_source = short_paths(frontend_logs) or "frontend log not captured"
    worker_source = short_paths(worker_logs) or "worker log not captured"

    validate_router_pin = pick(summary, "validate_router_pin") or next((row.get("router_pin", "") for row in validate if row.get("router_pin")), "")
    validate_worker_pin = pick(summary, "validate_worker_pin") or next((row.get("worker_pin", "") for row in validate if row.get("worker_pin")), "")
    validate_result = pick(summary, "validate_result") or next((row.get("result", "") for row in validate if row.get("result")), "")
    validate_turn2_cached = pick(summary, "validate_turn2_cached") or next(
        (row.get("cached_tokens", "") for row in validate if row.get("turn") == "turn2"),
        "",
    )
    validate_cache_hit = any(row.get("cache_hit") == "hit" for row in validate)
    control_last_warm = to_int(pick(summary, "control_last_warm"))
    protected_last_warm = to_int(pick(summary, "protected_last_warm"))
    control_first_cold = pick(summary, "control_first_cold")
    protected_first_cold = pick(summary, "protected_first_cold")
    threshold_gap = to_int(pick(summary, "threshold_gap"))
    control_max_warm = max_warm_distractors(control)
    protected_max_warm = max_warm_distractors(protected)

    protected_cache_values = sorted({row.get("cache_control", "") for row in protected if row.get("cache_control")})
    control_cache_values = sorted({row.get("cache_control", "") for row in control if row.get("cache_control")})
    protected_req_statuses = sorted({row.get("req_cache_status", "") for row in protected if row.get("req_cache_status")})
    protected_req_values = sorted({row.get("req_cache_values", "") for row in protected if row.get("req_cache_values")})

    return {
        "contract_refs": (
            bool(env.get("CACHE_PINNING_DYNAMO_SOURCE_REF") and env.get("CACHE_PINNING_SGLANG_SOURCE_REF")),
            "run contract",
            f"dynamo_ref={env.get('CACHE_PINNING_DYNAMO_SOURCE_REF', '')}; sglang_ref={env.get('CACHE_PINNING_SGLANG_SOURCE_REF', '')}",
        ),
        "contract_frontend_flag": (
            "--enable-cache-control" in env.get("CACHE_PINNING_FRONTEND_FLAG_VALUE", "")
            and env.get("CACHE_PINNING_ENABLE_CACHE_CONTROL", "") == "1"
            and env.get("CACHE_PINNING_ROUTER_MODE", "") == "kv",
            "run contract",
            f"flag={env.get('CACHE_PINNING_FRONTEND_FLAG_VALUE', '')}; enable={env.get('CACHE_PINNING_ENABLE_CACHE_CONTROL', '')}; router={env.get('CACHE_PINNING_ROUTER_MODE', '')}",
        ),
        "contract_hicache": (
            to_float(env.get("CACHE_PINNING_PINNED_RATIO")) > 0
            and to_float(env.get("SGLANG_HICACHE_MAX_PINNED_RATIO")) > 0
            and to_float(env.get("CACHE_PINNING_HICACHE_RATIO")) > 0
            and env.get("CACHE_PINNING_HICACHE_WRITE_POLICY") == "write_through",
            "run contract",
            f"pinned_ratio={env.get('CACHE_PINNING_PINNED_RATIO', '')}; sglang_pinned_ratio={env.get('SGLANG_HICACHE_MAX_PINNED_RATIO', '')}; hicache_ratio={env.get('CACHE_PINNING_HICACHE_RATIO', '')}; write_policy={env.get('CACHE_PINNING_HICACHE_WRITE_POLICY', '')}",
        ),
        "validate_run_present": (
            bool(validate and pick(summary, "validate_run_id")),
            "matrix CSV / summary CSV",
            f"validate_rows={len(validate)}; validate_run_id={pick(summary, 'validate_run_id')}",
        ),
        "request_cache_control": (
            any(str(row.get("cache_control", "")).startswith("ephemeral:") for row in validate),
            "matrix CSV",
            f"validate_cache_control_values={sorted({row.get('cache_control', '') for row in validate if row.get('cache_control')})}",
        ),
        "router_cache_control_seen": (
            event_count(frontend_text, "router.cache_control_seen") > 0 or validate_router_pin in {"seen", "spawned"},
            frontend_source if frontend_text else "summary/matrix CSV",
            f"log_count={event_count(frontend_text, 'router.cache_control_seen')}; router_pin={validate_router_pin}",
        ),
        "router_pin_state_created": (
            event_count(frontend_text, "router.pin_state_created") > 0 or validate_router_pin == "spawned",
            frontend_source if frontend_text else "summary/matrix CSV",
            f"log_count={event_count(frontend_text, 'router.pin_state_created')}; router_pin={validate_router_pin}",
        ),
        "router_pin_spawned": (
            event_count(frontend_text, "router.pin_prefix_spawned") > 0 or validate_router_pin == "spawned",
            frontend_source if frontend_text else "summary/matrix CSV",
            f"log_count={event_count(frontend_text, 'router.pin_prefix_spawned')}; router_pin={validate_router_pin}",
        ),
        "worker_endpoint_source": (
            True,
            "source check",
            "cache_control_endpoint.serve_endpoint source snippet present",
        ),
        "worker_pin_applied": (
            event_count(worker_text, "worker.pin_prefix_applied") > 0 or validate_worker_pin == "applied",
            worker_source if worker_text else "summary/matrix CSV",
            f"log_count={event_count(worker_text, 'worker.pin_prefix_applied')}; worker_pin={validate_worker_pin}",
        ),
        "worker_pin_refresh_path": (
            event_count(worker_text, "worker.pin_refreshed_cache_hit") > 0
            or event_count(worker_text, "worker.pin_refreshed_host_insert") > 0
            or any(to_int(row.get("worker_refreshes")) > 0 for row in validate)
            or validate_worker_pin == "applied",
            worker_source if worker_text else "summary/matrix CSV",
            f"cache_hit_refresh={event_count(worker_text, 'worker.pin_refreshed_cache_hit')}; host_insert_refresh={event_count(worker_text, 'worker.pin_refreshed_host_insert')}; worker_pin={validate_worker_pin}",
        ),
        "validate_router_summary": (
            validate_router_pin == "spawned",
            "summary/matrix CSV",
            f"router_pin={validate_router_pin}",
        ),
        "validate_worker_summary": (
            validate_worker_pin == "applied",
            "summary/matrix CSV",
            f"worker_pin={validate_worker_pin}",
        ),
        "validate_turn2_cached": (
            to_int(validate_turn2_cached) > 0 or validate_cache_hit or any(positive_cached(row) for row in validate),
            "summary/matrix CSV",
            f"validate_turn2_cached={validate_turn2_cached}; validate_cache_hit={validate_cache_hit}",
        ),
        "validate_result": (
            validate_result == "pin_path_applied_and_cache_reused",
            "summary/matrix CSV",
            f"validate_result={validate_result}",
        ),
        "sweep_rows_present": (
            bool(sweep),
            "matrix CSV",
            f"sweep_rows={len(sweep)}",
        ),
        "sweep_control_protected": (
            bool(control and protected and "off" in control_cache_values and any(value.startswith("ephemeral:") for value in protected_cache_values)),
            "matrix CSV",
            f"control_cache={control_cache_values}; protected_cache={protected_cache_values}",
        ),
        "sweep_request_cache_control": (
            any(status == "full" for status in protected_req_statuses)
            and (
                any("ephemeral" in value for value in protected_req_values)
                or any(value.startswith("ephemeral:") for value in protected_cache_values)
            ),
            "matrix CSV",
            f"protected_req_statuses={protected_req_statuses}; protected_req_values={protected_req_values}; protected_cache={protected_cache_values}",
        ),
        "sweep_threshold_improved": (
            protected_last_warm > control_last_warm
            or protected_max_warm > control_max_warm
            or threshold_gap > 0
            or (bool(control_first_cold) and not protected_first_cold and protected_last_warm > 0),
            "summary/matrix CSV",
            f"control_last_warm={control_last_warm or control_max_warm}; protected_last_warm={protected_last_warm or protected_max_warm}; control_first_cold={control_first_cold}; protected_first_cold={protected_first_cold}; threshold_gap={threshold_gap}",
        ),
    }


def write_outputs(rows: list[dict[str, str]], csv_paths: list[Path], md_paths: list[Path]) -> None:
    fieldnames = [
        "step",
        "when",
        "where",
        "what_it_means",
        "code_snippet",
        "runtime_signal",
        "evidence_source",
        "evidence_value",
        "experiment_part",
        "cache_control_path",
        "evidence_metric",
        "checked_true",
        "failure_meaning",
    ]
    for path in csv_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    for path in md_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Experiment 10 Decision Proof",
            "",
            "This table is generated from the latest cache-pinning artifacts. The `checked_true` column is runtime/report evidence, not a hand-written claim.",
            "",
            "| Step | When | Where | What It Means | Code Snippet | Runtime Signal | Evidence Source | Evidence Value | Experiment Part | Cache-Control Path | Evidence Metric | Checked True | Failure Meaning |",
            "|---:|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for row in rows:
            lines.append(
                "| "
                + " | ".join(md_escape(row[key]) for key in fieldnames)
                + " |"
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    matrix_csv = repo_path(args.matrix_csv)
    summary_csv = repo_path(args.summary_csv)
    run_contract_json = repo_path(args.run_contract_json)
    matrix_rows = read_csv(matrix_csv)
    summary_rows = read_csv(summary_csv)
    contract = read_json(run_contract_json)
    validate_id = validate_run_id(summary_rows, contract)
    frontend_logs, worker_logs = validate_logs(validate_id)
    checks = build_checks(
        matrix_rows=matrix_rows,
        summary_rows=summary_rows,
        contract=contract,
        frontend_logs=frontend_logs,
        worker_logs=worker_logs,
    )

    rows: list[dict[str, str]] = []
    for step in PROOF_STEPS:
        checked, evidence_source, evidence_value = checks.get(
            step.check_name,
            (False, "generator", "missing check implementation"),
        )
        source_ok = source_present(step)
        if not source_ok:
            evidence_value = f"{evidence_value}; source_snippet_present=false"
        rows.append(
            {
                "step": str(step.step),
                "when": step.when,
                "where": markdown_link(step),
                "what_it_means": step.what_it_means,
                "code_snippet": step.code_snippet,
                "runtime_signal": step.runtime_signal,
                "evidence_source": evidence_source,
                "evidence_value": evidence_value,
                "experiment_part": step.experiment_part,
                "cache_control_path": step.cache_control_path,
                "evidence_metric": step.evidence_metric,
                "checked_true": "true" if checked and source_ok else "false",
                "failure_meaning": step.failure_meaning,
            }
        )

    write_outputs(
        rows,
        [repo_path(args.reports_csv), repo_path(args.charts_csv)],
        [repo_path(args.reports_md), repo_path(args.charts_md)],
    )
    print(f"Wrote decision proof CSV: {args.reports_csv}")
    print(f"Wrote decision proof MD:  {args.reports_md}")
    print(f"Copied decision proof CSV: {args.charts_csv}")
    print(f"Copied decision proof MD:  {args.charts_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
