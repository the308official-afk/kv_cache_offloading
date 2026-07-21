#!/usr/bin/env python3
"""Build the Exp11 decision-proof table from latest priority artifacts."""

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
    request_role: str
    priority_class: str
    order_metric: str
    failure_meaning: str
    check_name: str


PROOF_STEPS = [
    ProofStep(
        1,
        "Harness builds low/high request specs",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        797,
        "The harness creates a mixed burst with low-priority and high-priority requests.",
        'priority_class="low-priority"\npriority_class="high-priority"',
        "latest_priority_scheduling_requests.csv request/prio_class rows",
        "all",
        "low-priority, high-priority",
        "arrival_index",
        "The request table does not show both low and high priority classes.",
        "request_classes",
    ),
    ProofStep(
        2,
        "Harness attaches priority hint",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        496,
        "Each request gets an `nvext.agent_hints.priority` value.",
        'payload["priority"] = priority_value',
        "worker_hint_prio / hint_seen",
        "all",
        "low-priority, high-priority",
        "hint value",
        "The request/proof table did not show hint priority values.",
        "hint_values",
    ),
    ProofStep(
        3,
        "Harness optionally sends top-level priority",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        913,
        "When supported, the script also sends a top-level OpenAI-compatible `priority` field.",
        'payload["priority"] = priority',
        "sent_top_prio / top_level_priority_sent",
        "all",
        "high-priority",
        "top-level priority",
        "Top-level priority was not sent or was unsupported. This is acceptable when hint metadata still reaches the worker.",
        "top_level_attempted",
    ),
    ProofStep(
        4,
        "Dynamo frontend preprocesses request",
        "upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py",
        436,
        "Dynamo frontend tokenizes/preprocesses the hinted request.",
        'emit_runtime_event(...)\n"frontend.request.preprocessed"',
        "frontend.request.preprocessed",
        "all",
        "low-priority, high-priority",
        "frontend runtime",
        "Frontend runtime logs were missing or did not show preprocessing.",
        "frontend_preprocessed",
    ),
    ProofStep(
        5,
        "Dynamo frontend dispatches request",
        "upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py",
        579,
        "Dynamo frontend hands the request to the router/worker path.",
        'emit_runtime_event(...)\n"frontend.request.dispatched"',
        "frontend.request.dispatched",
        "all",
        "low-priority, high-priority",
        "frontend runtime",
        "Frontend runtime logs did not show dispatch into the serving path.",
        "frontend_dispatched",
    ),
    ProofStep(
        6,
        "Worker receives request",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        482,
        "Dynamo worker receives the request before generation starts.",
        'emit_runtime_event(...)\n"worker.decode.request_received"',
        "worker.decode.request_received",
        "all",
        "low-priority, high-priority",
        "worker runtime",
        "Worker runtime logs did not show the request entering the decode handler.",
        "worker_received",
    ),
    ProofStep(
        7,
        "Worker reads routed priority",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        493,
        "Worker extracts routed priority from the request routing metadata.",
        'priority = (request.get("routing") or {}).get("priority")',
        "worker_top_prio / worker_hint_prio / hint_path_status",
        "all",
        "high-priority",
        "worker priority value",
        "The worker did not expose priority metadata. Check precise attribution and request-context forwarding.",
        "worker_priority_seen",
    ),
    ProofStep(
        8,
        "Worker forwards priority into SGLang",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        542,
        "Worker forwards priority into the live SGLang generation call.",
        "**self._priority_kwargs(priority)",
        "worker.decode generation kwargs / SGLang priority metadata",
        "all",
        "high-priority",
        "worker/SGLang priority",
        "No worker/SGLang priority evidence was found.",
        "sglang_priority_seen",
    ),
    ProofStep(
        9,
        "Worker attaches request to SGLang id",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        647,
        "SGLang produced a request id, so worker runtime timestamps can be joined to the script request rows.",
        'emit_runtime_event(...)\n"worker.decode.request_attached"\nsglang_request_id=sglang_request_id',
        "worker_request_attached_timestamp / attached_rank",
        "all",
        "low-priority, high-priority",
        "attached_rank",
        "No attach timestamp/rank was found, so jump-ahead order cannot be proven.",
        "attached_ranks",
    ),
    ProofStep(
        10,
        "Worker completes request",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        730,
        "Worker logs completion, giving completion timestamps and request usage.",
        'emit_runtime_event(...)\n"worker.decode.request_completed"',
        "worker_request_completed_timestamp / completed_rank",
        "all",
        "low-priority, high-priority",
        "completed_rank",
        "No completion timestamp/rank was found.",
        "completed_ranks",
    ),
    ProofStep(
        11,
        "Report assigns attach order",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        1410,
        "Postprocess sorts worker attach timestamps and assigns `attached_rank`.",
        'attached_rows.sort(...worker_request_attached_timestamp...)\nrow["attached_rank"] = index',
        "attached_rank",
        "all",
        "low-priority, high-priority",
        "attached_rank",
        "The proof table cannot compare arrival order against worker attach order.",
        "attached_ranks",
    ),
    ProofStep(
        12,
        "Report computes high-priority jump-ahead count",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        1445,
        "For each high-priority request, postprocess counts earlier low-priority requests it attached before.",
        'if low_attached is not None and low_attached > high_attached:\n    attached_leapfrogs += 1',
        "beat_low_attach / high_jump_ahead_count",
        "high requests",
        "high-priority",
        "jump-ahead count",
        "High-priority requests did not attach before earlier low-priority requests.",
        "jump_ahead_count",
    ),
    ProofStep(
        13,
        "Microbenchmark report computes jump-ahead rate",
        "experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py",
        243,
        "The compact matrix converts raw leapfrogs into `high_jump_ahead_count` and `high_jump_ahead_rate`.",
        "max_jump_ahead = low_requests * high_requests\nhigh_jump_ahead_rate = percent_text(...)",
        "high_jump_ahead_count / high_jump_ahead_rate",
        "all",
        "high-priority",
        "high_jump_ahead_rate",
        "The compact matrix did not show a positive jump-ahead rate.",
        "jump_ahead_rate",
    ),
    ProofStep(
        14,
        "Matrix reports hint path",
        "experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py",
        262,
        "The public matrix reports whether the worker saw priority hints.",
        '"hint_seen": priority_hint_seen_status(...)',
        "hint_seen=yes / worker_hint_status=full",
        "all",
        "high-priority",
        "hint_seen",
        "The public matrix did not show that priority hints reached the worker.",
        "matrix_hint_seen",
    ),
    ProofStep(
        15,
        "Matrix reports final verdict",
        "experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py",
        247,
        "The public matrix marks the run reordered when at least one high-priority request jumped ahead.",
        'result = f"{prefix}_reordered" if jump_count > 0 else "no_visible_reorder"',
        "result=priority_reordered",
        "all",
        "high-priority",
        "result",
        "The matrix did not show visible priority reordering.",
        "matrix_result",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-csv", default="experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv")
    parser.add_argument("--requests-csv", default="experiments/reports/latest_priority_scheduling_requests.csv")
    parser.add_argument("--proof-csv", default="experiments/reports/latest_priority_scheduling_proof.csv")
    parser.add_argument("--run-contract-json", default="experiments/reports/latest_priority_scheduling_microbenchmark_run_contract.json")
    parser.add_argument("--reports-csv", default="experiments/reports/latest_exp11_decision_proof.csv")
    parser.add_argument("--reports-md", default="experiments/reports/latest_exp11_decision_proof.md")
    parser.add_argument("--charts-csv", default="experiments/charts/exp11_decision_proof.csv")
    parser.add_argument("--charts-md", default="experiments/charts/exp11_decision_proof.md")
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


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def to_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(str(value).replace("%", "")))
    except (TypeError, ValueError):
        return 0


def percent_to_float(value: Any) -> float:
    try:
        return float(str(value).strip().replace("%", ""))
    except (TypeError, ValueError):
        return 0.0


def any_nonempty(rows: Iterable[dict[str, str]], key: str) -> bool:
    return any(str(row.get(key, "")).strip() for row in rows)


def any_positive(rows: Iterable[dict[str, str]], *keys: str) -> bool:
    for row in rows:
        for key in keys:
            if to_int(row.get(key)) > 0:
                return True
    return False


def compact_matrix_rows(matrix_rows: list[dict[str, str]]) -> bool:
    return any("high_jump_ahead_count" in row or "gap_ms" in row for row in matrix_rows)


def legacy_jump_count(matrix_rows: list[dict[str, str]]) -> int:
    return max(
        [to_int(row.get("high_attach_leapfrogs")) for row in matrix_rows]
        + [to_int(row.get("high_jump_ahead_count")) for row in matrix_rows]
        + [0]
    )


def max_jump_count(matrix_rows: list[dict[str, str]]) -> int:
    return max([to_int(row.get("max_jump_ahead")) for row in matrix_rows] + [0])


def max_jump_rate(matrix_rows: list[dict[str, str]]) -> float:
    rates = [percent_to_float(row.get("high_jump_ahead_rate")) for row in matrix_rows]
    if any(rate > 0 for rate in rates):
        return max(rates)
    max_count = max_jump_count(matrix_rows)
    jump_count = legacy_jump_count(matrix_rows)
    if max_count > 0:
        return (jump_count / max_count) * 100.0
    return 0.0


def matrix_hint_seen(matrix_rows: list[dict[str, str]]) -> bool:
    for row in matrix_rows:
        if str(row.get("hint_seen", "")).strip().lower() == "yes":
            return True
        if str(row.get("worker_hint_status", "")).strip().lower() in {"full", "partial"}:
            return True
        if str(row.get("sglang_prio_status", "")).strip().lower() not in {"", "none", "missing"}:
            return True
    return False


def matrix_result_reordered(matrix_rows: list[dict[str, str]]) -> bool:
    for row in matrix_rows:
        result = str(row.get("result", "") or row.get("effect", "")).strip().lower()
        if "reordered" in result or result == "yes":
            return True
    return False


def find_run_ids(matrix_rows: list[dict[str, str]], contract: dict[str, Any]) -> list[str]:
    ids = [str(row.get("run_id", "")).strip() for row in matrix_rows if row.get("run_id")]
    for key in ("probe_run_id", "PRIORITY_SCHEDULING_ID"):
        value = str(contract.get(key, "")).strip()
        if value:
            ids.append(value)
    sweep_ids = contract.get("sweep_run_ids")
    if isinstance(sweep_ids, list):
        ids.extend(str(item).strip() for item in sweep_ids if str(item).strip())
    contract_env = contract.get("contract_env")
    if isinstance(contract_env, dict):
        value = str(contract_env.get("PRIORITY_SCHEDULING_ID", "")).strip()
        if value:
            ids.append(value)
    seen: set[str] = set()
    unique: list[str] = []
    for run_id in ids:
        if run_id and run_id not in seen:
            seen.add(run_id)
            unique.append(run_id)
    return unique


def latest_matching_files(patterns: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(REPO_ROOT.glob(pattern))
    return sorted({p for p in files if p.is_file()}, key=lambda p: str(p))


def find_runtime_logs(run_ids: list[str], kind: str) -> list[Path]:
    if kind == "frontend":
        names = ("*frontend_runtime.log", "*frontend*.log")
    else:
        names = ("*worker_runtime.log",)
    patterns: list[str] = []
    for run_id in run_ids:
        for name in names:
            patterns.append(f"experiments/reports/priority_scheduling/{run_id}*/{name}")
    return latest_matching_files(patterns)


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


def snippet_tokens(snippet: str) -> list[str]:
    tokens: list[str] = []
    for line in snippet.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if "..." in cleaned:
            tokens.extend(part.strip() for part in cleaned.split("...") if len(part.strip()) >= 4)
        elif cleaned:
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


def build_checks(
    *,
    matrix_rows: list[dict[str, str]],
    requests_rows: list[dict[str, str]],
    proof_rows: list[dict[str, str]],
    frontend_logs: list[Path],
    worker_logs: list[Path],
    sglang_log: Path,
) -> dict[str, tuple[bool, str, str]]:
    all_request_rows = proof_rows or requests_rows
    low_rows = [row for row in all_request_rows if row.get("prio_class") == "low-priority"]
    high_rows = [row for row in all_request_rows if row.get("prio_class") == "high-priority"]
    frontend_text = read_texts(frontend_logs)
    worker_text = read_texts(worker_logs)
    sglang_text = read_texts([sglang_log] if sglang_log.exists() else [])
    combined_runtime_text = "\n".join(part for part in (worker_text, sglang_text) if part)

    frontend_source = short_paths(frontend_logs) or "frontend log not captured"
    worker_source = short_paths(worker_logs) or "worker log not captured"
    sglang_source = str(sglang_log.relative_to(REPO_ROOT)) if sglang_log.exists() else "SGLang transfer log not found"
    sglang_priority_count = event_count(combined_runtime_text, '"event": "sglang.priority"') + event_count(
        combined_runtime_text, '"event":"sglang.priority"'
    )
    jump_count = legacy_jump_count(matrix_rows)
    jump_rate = max_jump_rate(matrix_rows)
    if jump_rate <= 0:
        possible = len(low_rows) * len(high_rows)
        if possible > 0 and jump_count > 0:
            jump_rate = (jump_count / possible) * 100.0
    request_jump_count = max(
        [to_int(row.get("beat_low_attach")) for row in all_request_rows]
        + [to_int(row.get("overtook_earlier_low_attached_count")) for row in all_request_rows]
        + [0]
    )
    attached_count = sum(1 for row in all_request_rows if str(row.get("attach") or row.get("attached_rank") or "").strip())
    completed_count = sum(1 for row in all_request_rows if str(row.get("complete") or row.get("completed_rank") or "").strip())

    return {
        "request_classes": (
            bool(low_rows and high_rows),
            "priority request/proof CSV",
            f"low_rows={len(low_rows)}; high_rows={len(high_rows)}",
        ),
        "hint_values": (
            any_nonempty(all_request_rows, "worker_hint_prio")
            or any_nonempty(all_request_rows, "agent_hints_priority")
            or matrix_hint_seen(matrix_rows),
            "priority request/proof CSV / matrix CSV",
            f"worker_hint_values={sorted({r.get('worker_hint_prio','') for r in all_request_rows if r.get('worker_hint_prio','')})}; hint_seen={matrix_hint_seen(matrix_rows)}",
        ),
        "top_level_attempted": (
            any_nonempty(all_request_rows, "sent_top_prio")
            or any_nonempty(all_request_rows, "top_level_priority_sent"),
            "priority request/proof CSV",
            f"sent_top_prio_values={sorted({r.get('sent_top_prio','') for r in all_request_rows if r.get('sent_top_prio','')}) or ['not recorded']}",
        ),
        "frontend_preprocessed": (
            event_count(frontend_text, "frontend.request.preprocessed") > 0,
            frontend_source,
            f"count={event_count(frontend_text, 'frontend.request.preprocessed')}",
        ),
        "frontend_dispatched": (
            event_count(frontend_text, "frontend.request.dispatched") > 0,
            frontend_source,
            f"count={event_count(frontend_text, 'frontend.request.dispatched')}",
        ),
        "worker_received": (
            event_count(worker_text, "worker.decode.request_received") > 0
            or any_nonempty(all_request_rows, "runtime_match"),
            worker_source if worker_text else "priority request/proof CSV",
            f"log_count={event_count(worker_text, 'worker.decode.request_received')}; runtime_match_rows={sum(1 for row in all_request_rows if truthy(row.get('runtime_match')))}",
        ),
        "worker_priority_seen": (
            matrix_hint_seen(matrix_rows) or any_nonempty(all_request_rows, "worker_hint_prio"),
            "matrix CSV / priority request/proof CSV",
            f"hint_seen={matrix_hint_seen(matrix_rows)}; worker_hint_rows={sum(1 for row in all_request_rows if str(row.get('worker_hint_prio','')).strip())}",
        ),
        "sglang_priority_seen": (
            sglang_priority_count > 0 or matrix_hint_seen(matrix_rows),
            sglang_source if sglang_priority_count > 0 else "matrix CSV",
            f"sglang.priority={sglang_priority_count}; matrix_hint_seen={matrix_hint_seen(matrix_rows)}",
        ),
        "attached_ranks": (
            attached_count > 0,
            "priority request/proof CSV",
            f"attached_rank_rows={attached_count}",
        ),
        "completed_ranks": (
            completed_count > 0,
            "priority request/proof CSV",
            f"completed_rank_rows={completed_count}",
        ),
        "jump_ahead_count": (
            jump_count > 0 or request_jump_count > 0,
            "matrix CSV / priority proof CSV",
            f"matrix_jump_count={jump_count}; request_max_beat_low_attach={request_jump_count}",
        ),
        "jump_ahead_rate": (
            jump_rate > 0,
            "matrix CSV",
            f"max_high_jump_ahead_rate={jump_rate:.1f}%",
        ),
        "matrix_hint_seen": (
            matrix_hint_seen(matrix_rows),
            "matrix CSV",
            f"matrix_hint_seen={matrix_hint_seen(matrix_rows)}",
        ),
        "matrix_result": (
            matrix_result_reordered(matrix_rows),
            "matrix CSV",
            f"matrix_result_reordered={matrix_result_reordered(matrix_rows)}; format={'compact' if compact_matrix_rows(matrix_rows) else 'legacy'}",
        ),
    }


def markdown_link(step: ProofStep) -> str:
    path = repo_path(step.where)
    return f"[{Path(step.where).name}:{step.line}]({path}:{step.line})"


def md_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


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
        "request_role",
        "priority_class",
        "order_metric",
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
            "# Experiment 11 Decision Proof",
            "",
            "This table is generated from the latest priority-scheduling artifacts. The `checked_true` column is runtime/report evidence, not a hand-written claim.",
            "",
            "| Step | When | Where | What It Means | Code Snippet | Runtime Signal | Evidence Source | Evidence Value | Request Role | Priority Class | Order Metric | Checked True | Failure Meaning |",
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
    requests_csv = repo_path(args.requests_csv)
    proof_csv = repo_path(args.proof_csv)
    run_contract_json = repo_path(args.run_contract_json)
    sglang_log = repo_path("experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl")

    matrix_rows = read_csv(matrix_csv)
    requests_rows = read_csv(requests_csv)
    proof_rows = read_csv(proof_csv)
    contract = read_json(run_contract_json)
    run_ids = find_run_ids(matrix_rows, contract)
    frontend_logs = find_runtime_logs(run_ids, "frontend")
    worker_logs = find_runtime_logs(run_ids, "worker")

    checks = build_checks(
        matrix_rows=matrix_rows,
        requests_rows=requests_rows,
        proof_rows=proof_rows,
        frontend_logs=frontend_logs,
        worker_logs=worker_logs,
        sglang_log=sglang_log,
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
                "request_role": step.request_role,
                "priority_class": step.priority_class,
                "order_metric": step.order_metric,
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
