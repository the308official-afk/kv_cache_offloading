#!/usr/bin/env python3
"""Build the Exp13 decision-proof table from latest latency-sensitivity artifacts."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from build_priority_scheduling_decision_proof import (
    REPO_ROOT,
    event_count,
    find_run_ids,
    find_runtime_logs,
    legacy_jump_count,
    markdown_link,
    matrix_hint_seen,
    matrix_result_reordered,
    max_jump_count,
    max_jump_rate,
    md_escape,
    percent_to_float,
    read_csv,
    read_json,
    read_texts,
    repo_path,
    short_paths,
    source_present,
    to_int,
)


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
    sensitivity_class: str
    order_metric: str
    failure_meaning: str
    check_name: str


PROOF_STEPS = [
    ProofStep(
        1,
        "Contract selects latency-sensitivity mode",
        "contracts/latency_sensitivity_microbenchmark.contract.sh",
        18,
        "The public Exp13 wrapper forces the shared harness to send `latency_sensitivity` hints.",
        ': "${PRIORITY_HINT_KIND:=latency_sensitivity}"',
        "run_contract.json PRIORITY_HINT_KIND / matrix hint_kind",
        "whole run",
        "all",
        "hint kind",
        "The run may be using the priority experiment instead of the latency-sensitivity experiment.",
        "contract_hint_kind",
    ),
    ProofStep(
        2,
        "Harness builds low/high request specs",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        724,
        "The shared harness creates a mixed burst of low-sensitivity and high-sensitivity requests.",
        'priority_class="low-priority"\npriority_class="high-priority"',
        "latest_priority_scheduling_requests.csv rows with both classes",
        "all",
        "low-sensitivity, high-sensitivity",
        "arrival_index",
        "The request table does not show both low and high request classes.",
        "request_classes",
    ),
    ProofStep(
        3,
        "Harness attaches latency-sensitivity hint",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        489,
        "Each request gets `nvext.agent_hints.latency_sensitivity`; high requests get the high value and low requests get the low value.",
        'if args.hint_kind == "latency_sensitivity":\n    payload["latency_sensitivity"] = ...',
        "agent_hints_latency_sensitivity / worker_latency_sensitivity",
        "all",
        "low-sensitivity, high-sensitivity",
        "hint value",
        "The request/proof table did not show latency-sensitivity values.",
        "latency_hint_values",
    ),
    ProofStep(
        4,
        "Contract disables top-level priority",
        "contracts/latency_sensitivity_microbenchmark.contract.sh",
        21,
        "Exp13 isolates the latency-sensitivity hint by not sending OpenAI top-level `priority`.",
        ': "${PRIORITY_TOP_LEVEL_PRIORITY_MODE:=disable}"',
        "sent_top_prio false / top_prio_compat not_attempted",
        "whole run",
        "all",
        "top-level priority",
        "Top-level priority was sent, so the run is no longer a clean latency-sensitivity-only test.",
        "top_level_disabled",
    ),
    ProofStep(
        5,
        "Frontend preprocesses request",
        "upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py",
        436,
        "Dynamo frontend tokenizes/preprocesses the hinted request and logs the `agent_hints` payload.",
        'emit_runtime_event(...)\n"frontend.request.preprocessed"',
        "frontend.request.preprocessed",
        "all",
        "low-sensitivity, high-sensitivity",
        "frontend runtime",
        "Frontend runtime logs were missing or did not show preprocessing.",
        "frontend_preprocessed",
    ),
    ProofStep(
        6,
        "Frontend dispatches request",
        "upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py",
        579,
        "Dynamo frontend hands the preprocessed request to the router/worker path.",
        'emit_runtime_event(...)\n"frontend.request.dispatched"',
        "frontend.request.dispatched",
        "all",
        "low-sensitivity, high-sensitivity",
        "frontend runtime",
        "Frontend runtime logs did not show dispatch into the serving path.",
        "frontend_dispatched",
    ),
    ProofStep(
        7,
        "Worker receives request",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        482,
        "Dynamo worker receives the request before generation starts.",
        'emit_runtime_event(...)\n"worker.decode.request_received"',
        "worker.decode.request_received",
        "all",
        "low-sensitivity, high-sensitivity",
        "worker runtime",
        "Worker runtime logs did not show the request entering the decode handler.",
        "worker_received",
    ),
    ProofStep(
        8,
        "Worker runtime payload includes agent hints",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        56,
        "The worker-side runtime event includes sanitized `agent_hints`, including `latency_sensitivity` when present.",
        "**agent_hint_log_fields(request)",
        "worker runtime JSON agent_hints.latency_sensitivity",
        "all",
        "low-sensitivity, high-sensitivity",
        "worker hint payload",
        "The worker event was emitted but did not include agent hints.",
        "worker_agent_hints_logged",
    ),
    ProofStep(
        9,
        "Runtime helper extracts agent hints",
        "upstream/dynamo/components/src/dynamo/common/runtime_logging.py",
        145,
        "The shared runtime logger extracts and emits the hint keys and values.",
        "def agent_hint_log_fields(request: dict[str, Any])",
        "agent_hints_keys includes latency_sensitivity",
        "all",
        "low-sensitivity, high-sensitivity",
        "runtime hint extraction",
        "Runtime logging did not expose the latency-sensitivity hint.",
        "worker_agent_hints_logged",
    ),
    ProofStep(
        10,
        "Report parses worker-side latency hint",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        1273,
        "Postprocess reads `agent_hints.latency_sensitivity` from worker runtime JSON.",
        'hint_latency_sensitivity = maybe_float(hints.get("latency_sensitivity"))',
        "worker_agent_hints_latency_sensitivity",
        "all",
        "low-sensitivity, high-sensitivity",
        "worker hint value",
        "Postprocess could not recover the latency-sensitivity hint from worker logs.",
        "runtime_parser_latency",
    ),
    ProofStep(
        11,
        "Report copies latency hint onto rows",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        1402,
        "The request rows receive `worker_agent_hints_latency_sensitivity`, which becomes the readable proof column.",
        'row["worker_agent_hints_latency_sensitivity"]',
        "worker_latency_sensitivity",
        "all",
        "low-sensitivity, high-sensitivity",
        "request/proof row",
        "The proof table did not expose worker-side latency-sensitivity values.",
        "row_worker_latency",
    ),
    ProofStep(
        12,
        "Report assigns attach order",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        1410,
        "Postprocess sorts worker attach timestamps and assigns `attached_rank`.",
        'attached_rows.sort(...worker_request_attached_timestamp...)\nrow["attached_rank"] = index',
        "attached_rank",
        "all",
        "low-sensitivity, high-sensitivity",
        "attached_rank",
        "The proof table cannot compare arrival order against worker attach order.",
        "attached_ranks",
    ),
    ProofStep(
        13,
        "Report computes high-sensitivity jump-ahead count",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        1445,
        "For each high-sensitivity request, postprocess counts earlier low-sensitivity requests it attached before.",
        'if low_attached is not None and low_attached > high_attached:\n    attached_leapfrogs += 1',
        "beat_low_attach / high_jump_ahead_count",
        "high requests",
        "high-sensitivity",
        "jump-ahead count",
        "High-sensitivity requests did not attach before earlier low-sensitivity requests.",
        "jump_ahead_count",
    ),
    ProofStep(
        14,
        "Summary marks worker hint status",
        "experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py",
        1596,
        "For latency-sensitivity runs, the summary checks the high rows for the expected float hint value.",
        'request_float_status(...\nfield="worker_agent_hints_latency_sensitivity"',
        "worker_hint_status=full / hint_seen=yes",
        "high requests",
        "high-sensitivity",
        "hint status",
        "The high-sensitivity rows did not show the expected worker-side hint value.",
        "matrix_hint_seen",
    ),
    ProofStep(
        15,
        "Microbenchmark report preserves hint kind",
        "experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py",
        240,
        "The compact matrix records that this was a `latency_sensitivity` run.",
        'hint_kind = str(summary.get("hint_kind") or "priority")',
        "hint_kind=latency_sensitivity",
        "whole run",
        "all",
        "matrix hint kind",
        "The public matrix did not identify the run as latency sensitivity.",
        "matrix_hint_kind",
    ),
    ProofStep(
        16,
        "Microbenchmark report computes jump-ahead rate",
        "experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py",
        259,
        "The compact matrix converts raw leapfrogs into `high_jump_ahead_count` and `high_jump_ahead_rate`.",
        '"high_jump_ahead_count": jump_count\n"high_jump_ahead_rate": percent_text(...)',
        "high_jump_ahead_count / high_jump_ahead_rate",
        "all",
        "high-sensitivity",
        "high_jump_ahead_rate",
        "The compact matrix did not show a positive jump-ahead rate.",
        "jump_ahead_rate",
    ),
    ProofStep(
        17,
        "Matrix reports final verdict",
        "experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py",
        247,
        "The public matrix marks the run reordered when at least one high-sensitivity request jumped ahead.",
        'result = f"{prefix}_reordered" if jump_count > 0 else "no_visible_reorder"',
        "result=latency_sensitivity_reordered",
        "all",
        "high-sensitivity",
        "result",
        "The matrix did not show visible latency-sensitivity reordering.",
        "matrix_result",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-csv", default="experiments/reports/latest_latency_sensitivity_microbenchmark_matrix.csv")
    parser.add_argument("--requests-csv", default="experiments/reports/latest_priority_scheduling_requests.csv")
    parser.add_argument("--proof-csv", default="experiments/reports/latest_priority_scheduling_proof.csv")
    parser.add_argument("--run-contract-json", default="experiments/reports/latest_latency_sensitivity_microbenchmark_run_contract.json")
    parser.add_argument("--reports-csv", default="experiments/reports/latest_exp13_decision_proof.csv")
    parser.add_argument("--reports-md", default="experiments/reports/latest_exp13_decision_proof.md")
    parser.add_argument("--charts-csv", default="experiments/charts/exp13_decision_proof.csv")
    parser.add_argument("--charts-md", default="experiments/charts/exp13_decision_proof.md")
    return parser.parse_args()


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def any_nonempty(rows: Iterable[dict[str, str]], *keys: str) -> bool:
    for row in rows:
        for key in keys:
            if str(row.get(key, "")).strip():
                return True
    return False


def latency_values(rows: Iterable[dict[str, str]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        for key in (
            "worker_latency_sensitivity",
            "worker_agent_hints_latency_sensitivity",
            "agent_hints_latency_sensitivity",
        ):
            value = str(row.get(key, "")).strip()
            if value:
                values.append(value)
    return sorted(set(values))


def matrix_hint_kind_is_latency(matrix_rows: list[dict[str, str]]) -> bool:
    return any(str(row.get("hint_kind", "")).strip() == "latency_sensitivity" for row in matrix_rows)


def matrix_latency_reordered(matrix_rows: list[dict[str, str]]) -> bool:
    return any("latency_sensitivity_reordered" in str(row.get("result", "")).strip() for row in matrix_rows)


def compact_matrix_rows(matrix_rows: list[dict[str, str]]) -> bool:
    return any("high_jump_ahead_count" in row or "gap_ms" in row for row in matrix_rows)


def build_checks(
    *,
    matrix_rows: list[dict[str, str]],
    requests_rows: list[dict[str, str]],
    proof_rows: list[dict[str, str]],
    frontend_logs: list[Path],
    worker_logs: list[Path],
    contract: dict[str, Any],
) -> dict[str, tuple[bool, str, str]]:
    all_request_rows = proof_rows or requests_rows
    low_rows = [row for row in all_request_rows if row.get("prio_class") == "low-priority" or row.get("priority_class") == "low-priority"]
    high_rows = [row for row in all_request_rows if row.get("prio_class") == "high-priority" or row.get("priority_class") == "high-priority"]
    frontend_text = read_texts(frontend_logs)
    worker_text = read_texts(worker_logs)

    frontend_source = short_paths(frontend_logs) or "frontend log not captured"
    worker_source = short_paths(worker_logs) or "worker log not captured"

    values = latency_values(all_request_rows)
    jump_count = legacy_jump_count(matrix_rows)
    request_jump_count = max(
        [to_int(row.get("beat_low_attach")) for row in all_request_rows]
        + [to_int(row.get("overtook_earlier_low_attached_count")) for row in all_request_rows]
        + [0]
    )
    jump_rate = max_jump_rate(matrix_rows)
    if jump_rate <= 0:
        max_count = max_jump_count(matrix_rows) or len(low_rows) * len(high_rows)
        if max_count > 0 and (jump_count or request_jump_count):
            jump_rate = ((jump_count or request_jump_count) / max_count) * 100.0

    attached_count = sum(1 for row in all_request_rows if str(row.get("attach") or row.get("attached_rank") or "").strip())
    completed_count = sum(1 for row in all_request_rows if str(row.get("complete") or row.get("completed_rank") or "").strip())
    sent_top_values = sorted({str(row.get("sent_top_prio") or row.get("top_level_priority_sent") or "").strip() for row in all_request_rows if str(row.get("sent_top_prio") or row.get("top_level_priority_sent") or "").strip()})
    top_level_mode = str(contract.get("PRIORITY_TOP_LEVEL_PRIORITY_MODE", "")).strip().lower()
    worker_latency_log_count = worker_text.count("latency_sensitivity")

    return {
        "contract_hint_kind": (
            str(contract.get("PRIORITY_HINT_KIND", "")).strip() == "latency_sensitivity"
            or matrix_hint_kind_is_latency(matrix_rows),
            "run contract / matrix CSV",
            f"contract_PRIORITY_HINT_KIND={contract.get('PRIORITY_HINT_KIND', '')}; matrix_hint_kind_latency={matrix_hint_kind_is_latency(matrix_rows)}",
        ),
        "request_classes": (
            bool(low_rows and high_rows),
            "priority request/proof CSV",
            f"low_rows={len(low_rows)}; high_rows={len(high_rows)}",
        ),
        "latency_hint_values": (
            bool(values) or matrix_hint_seen(matrix_rows),
            "priority request/proof CSV / matrix CSV",
            f"worker_latency_sensitivity_values={values or ['not recorded']}; hint_seen={matrix_hint_seen(matrix_rows)}",
        ),
        "top_level_disabled": (
            top_level_mode == "disable"
            or not sent_top_values
            or all(value.lower() in {"false", "0", "no"} for value in sent_top_values),
            "run contract / priority request/proof CSV",
            f"PRIORITY_TOP_LEVEL_PRIORITY_MODE={contract.get('PRIORITY_TOP_LEVEL_PRIORITY_MODE', '')}; sent_top_prio_values={sent_top_values or ['not recorded']}",
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
            or any(truthy(row.get("runtime_match") or row.get("worker_runtime_matched")) for row in all_request_rows),
            worker_source if worker_text else "priority request/proof CSV",
            f"log_count={event_count(worker_text, 'worker.decode.request_received')}; runtime_match_rows={sum(1 for row in all_request_rows if truthy(row.get('runtime_match') or row.get('worker_runtime_matched')))}",
        ),
        "worker_agent_hints_logged": (
            worker_latency_log_count > 0 or bool(values) or matrix_hint_seen(matrix_rows),
            worker_source if worker_latency_log_count > 0 else "priority request/proof CSV / matrix CSV",
            f"worker_log_latency_sensitivity_count={worker_latency_log_count}; row_values={values or ['not recorded']}; hint_seen={matrix_hint_seen(matrix_rows)}",
        ),
        "runtime_parser_latency": (
            bool(values) or matrix_hint_seen(matrix_rows),
            "priority request/proof CSV / matrix CSV",
            f"worker_latency_sensitivity_values={values or ['not recorded']}",
        ),
        "row_worker_latency": (
            bool(values) or matrix_hint_seen(matrix_rows),
            "priority request/proof CSV / matrix CSV",
            f"worker_latency_sensitivity_values={values or ['not recorded']}",
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
            jump_rate > 0 or any(percent_to_float(row.get("high_jump_ahead_rate")) > 0 for row in matrix_rows),
            "matrix CSV",
            f"max_high_jump_ahead_rate={jump_rate:.1f}%",
        ),
        "matrix_hint_seen": (
            matrix_hint_seen(matrix_rows),
            "matrix CSV",
            f"matrix_hint_seen={matrix_hint_seen(matrix_rows)}",
        ),
        "matrix_hint_kind": (
            matrix_hint_kind_is_latency(matrix_rows),
            "matrix CSV",
            f"matrix_hint_kind_latency={matrix_hint_kind_is_latency(matrix_rows)}",
        ),
        "matrix_result": (
            matrix_latency_reordered(matrix_rows) or matrix_result_reordered(matrix_rows),
            "matrix CSV",
            f"latency_result_reordered={matrix_latency_reordered(matrix_rows)}; any_reordered={matrix_result_reordered(matrix_rows)}; format={'compact' if compact_matrix_rows(matrix_rows) else 'legacy'}",
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
        "request_role",
        "sensitivity_class",
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
            "# Experiment 13 Decision Proof",
            "",
            "This table is generated from the latest latency-sensitivity artifacts. The `checked_true` column is runtime/report evidence, not a hand-written claim.",
            "",
            "| Step | When | Where | What It Means | Code Snippet | Runtime Signal | Evidence Source | Evidence Value | Request Role | Sensitivity Class | Order Metric | Checked True | Failure Meaning |",
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
        contract=contract,
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
                "sensitivity_class": step.sensitivity_class,
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
