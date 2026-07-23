#!/usr/bin/env python3
"""Build the Exp9 decision-proof table from latest retention artifacts.

The table is intentionally both documentation and evidence.  Static columns name
the source location and code snippet; evidence columns say whether the latest
run produced the corresponding runtime/report signal.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


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
    failure_meaning: str
    check_name: str


PROOF_STEPS = [
    ProofStep(
        1,
        "Harness sends request",
        "experiments/scripts/retention_probe/run_kv_retention_probe.py",
        1295,
        "AgentBench starts timing the HTTP request and sends the prompt plus nvext metadata.",
        'start = time.perf_counter()\nstatus, response_json, error = post_json(...)',
        "retention_probe_requests.csv rows with request metadata",
        "all",
        "The harness did not produce request rows, so the run cannot be tied back to prompt/hint metadata.",
        "harness_rows",
    ),
    ProofStep(
        2,
        "Frontend finishes preprocessing",
        "upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py",
        436,
        "Dynamo frontend tokenized/preprocessed the request while preserving request context and hints.",
        'emit_runtime_event(...)\n"frontend.request.preprocessed"',
        "frontend.request.preprocessed",
        "all",
        "Frontend runtime logs were missing or did not show preprocessing for this run.",
        "frontend_preprocessed",
    ),
    ProofStep(
        3,
        "Frontend dispatches request",
        "upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py",
        579,
        "Dynamo frontend handed the preprocessed request to the router/worker path.",
        'emit_runtime_event(...)\n"frontend.request.dispatched"',
        "frontend.request.dispatched",
        "all",
        "Frontend runtime logs did not show the request being dispatched toward the worker path.",
        "frontend_dispatched",
    ),
    ProofStep(
        4,
        "Worker receives request",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        482,
        "Dynamo worker received the request before generation starts.",
        'emit_runtime_event(...)\n"worker.decode.request_received"',
        "worker.decode.request_received",
        "all",
        "Worker runtime logs did not show the request entering the decode handler.",
        "worker_received",
    ),
    ProofStep(
        5,
        "Worker reads routed priority",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        493,
        "Worker extracts the routed top-level priority value when that path is enabled.",
        'priority = (request.get("routing") or {}).get("priority")',
        "request CSV priority / matrix req_prio_status",
        "protected",
        "No request-level priority evidence was found. This can be expected when top-level priority is disabled.",
        "request_priority",
    ),
    ProofStep(
        6,
        "Worker forwards priority into SGLang",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        528,
        "Worker forwards the routed priority into the live SGLang generation call.",
        "decode = await self.engine.async_generate(...)\n**self._priority_kwargs(priority)",
        "worker_prio_status / SGLang priority metadata",
        "protected",
        "The run did not expose worker/SGLang priority evidence. Check precise attribution and SGLang priority markers.",
        "worker_priority",
    ),
    ProofStep(
        7,
        "Worker attaches to SGLang request id",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        647,
        "SGLang produced a request id, allowing Dynamo request rows to join with SGLang runtime events.",
        'emit_runtime_event(...)\n"worker.decode.request_attached"\nsglang_request_id=sglang_request_id',
        "worker.decode.request_attached",
        "all",
        "The worker did not expose an SGLang request id, so SGLang events cannot be safely joined to the request.",
        "worker_attached",
    ),
    ProofStep(
        8,
        "SGLang priority/cache path executes",
        "runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py",
        1542,
        "Instrumented SGLang emits priority/cache events when the patched runtime path executes.",
        'payload = {"event": "sglang.priority", "action": action, ...}\nprint(line, file=sys.stderr, flush=True)',
        "sglang.priority or sglang.cache",
        "protected",
        "No SGLang priority/cache event was observed. Check transfer logging and precise SGLang overlay.",
        "sglang_events",
    ),
    ProofStep(
        9,
        "Worker completes request",
        "upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        730,
        "Worker logs final usage, cached-token evidence, finish reason, and request context.",
        'emit_runtime_event(...)\n"worker.decode.request_completed"\ncompletion_usage=out["completion_usage"]',
        "worker.decode.request_completed",
        "all",
        "Worker runtime logs did not show request completion.",
        "worker_completed",
    ),
    ProofStep(
        10,
        "Frontend completes stream",
        "upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py",
        667,
        "Frontend observed the final response chunk and logged completion.",
        'emit_runtime_event(...)\n"frontend.request.completed"',
        "frontend.request.completed",
        "all",
        "Frontend runtime logs did not show stream completion for the request.",
        "frontend_completed",
    ),
    ProofStep(
        11,
        "Harness records CSV row",
        "experiments/scripts/retention_probe/run_kv_retention_probe.py",
        1363,
        "AgentBench records latency, prompt hash, hint metadata, cached tokens, and status.",
        'return {\n  "latency_ms": round_ms(latency_ms),\n  "cached_prompt_tokens": cached_tokens,\n}',
        "retention_probe_requests.csv status/latency/cached fields",
        "all",
        "Request CSV rows are missing status or latency fields.",
        "request_csv_complete",
    ),
    ProofStep(
        12,
        "Postprocess maps logs to report columns",
        "experiments/scripts/retention_probe/run_kv_retention_probe.py",
        1772,
        "Postprocessing parses runtime logs and collapses them into public matrix fields.",
        'event = parse_sglang_event_line(line)\nif event.get("event") == "sglang.priority":\n    row["sglang_priority_events"] += 1',
        "latest_kv_retention_microbenchmark_matrix.csv",
        "all",
        "The matrix is missing or does not contain usable Exp9 rows.",
        "matrix_rows",
    ),
]

PROOF_STEP_METADATA = {
    "harness_rows": {
        "component": "harness",
        "severity": "critical",
        "meaning_short": "AgentBench sent and recorded requests.",
    },
    "frontend_preprocessed": {
        "component": "frontend",
        "severity": "warning",
        "meaning_short": "Frontend preprocessing evidence was captured.",
    },
    "frontend_dispatched": {
        "component": "frontend",
        "severity": "warning",
        "meaning_short": "Frontend dispatch evidence was captured.",
    },
    "worker_received": {
        "component": "worker",
        "severity": "critical",
        "meaning_short": "Dynamo worker received the requests.",
    },
    "request_priority": {
        "component": "harness",
        "severity": "critical",
        "meaning_short": "Protected requests carried priority metadata.",
    },
    "worker_priority": {
        "component": "worker/sglang",
        "severity": "warning",
        "meaning_short": "Runtime priority action evidence was visible.",
    },
    "worker_attached": {
        "component": "worker",
        "severity": "critical",
        "meaning_short": "Worker exposed SGLang request ids for attribution.",
    },
    "sglang_events": {
        "component": "sglang",
        "severity": "critical",
        "meaning_short": "SGLang cache/priority instrumentation emitted events.",
    },
    "worker_completed": {
        "component": "worker",
        "severity": "critical",
        "meaning_short": "Worker completed requests and logged usage.",
    },
    "frontend_completed": {
        "component": "frontend",
        "severity": "warning",
        "meaning_short": "Frontend stream completion evidence was captured.",
    },
    "request_csv_complete": {
        "component": "harness",
        "severity": "critical",
        "meaning_short": "Request CSV rows include status and latency.",
    },
    "matrix_rows": {
        "component": "postprocess",
        "severity": "critical",
        "meaning_short": "Final Exp9 matrix was produced.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--matrix-csv",
        default="experiments/reports/latest_kv_retention_microbenchmark_matrix.csv",
        help="Latest Exp9 microbenchmark matrix CSV.",
    )
    parser.add_argument(
        "--requests-csv",
        default="experiments/reports/latest_retention_probe_requests.csv",
        help="Latest aggregated retention request CSV.",
    )
    parser.add_argument(
        "--run-contract-json",
        default="experiments/reports/latest_kv_retention_microbenchmark_run_contract.json",
        help="Latest Exp9 run contract JSON.",
    )
    parser.add_argument(
        "--reports-csv",
        default="experiments/reports/latest_exp9_decision_proof.csv",
        help="Output CSV under experiments/reports.",
    )
    parser.add_argument(
        "--reports-md",
        default="experiments/reports/latest_exp9_decision_proof.md",
        help="Output markdown under experiments/reports.",
    )
    parser.add_argument(
        "--charts-csv",
        default="experiments/charts/exp9_decision_proof.csv",
        help="Clean public CSV copy under experiments/charts.",
    )
    parser.add_argument(
        "--charts-md",
        default="experiments/charts/exp9_decision_proof.md",
        help="Clean public markdown copy under experiments/charts.",
    )
    return parser.parse_args()


def repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def any_nonempty(rows: Iterable[dict[str, str]], key: str) -> bool:
    return any(str(row.get(key, "")).strip() for row in rows)


def find_run_ids(matrix_rows: list[dict[str, str]], contract: dict[str, object]) -> list[str]:
    run_ids = [str(row.get("run_id", "")).strip() for row in matrix_rows if row.get("run_id")]
    for key in ("sweep_run_id", "probe_run_id", "KV_RETENTION_ID"):
        value = str(contract.get(key, "")).strip()
        if value:
            run_ids.append(value)
    seen: set[str] = set()
    unique: list[str] = []
    for run_id in run_ids:
        if run_id and run_id not in seen:
            seen.add(run_id)
            unique.append(run_id)
    return unique


def latest_matching_files(patterns: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(REPO_ROOT.glob(pattern))
    return sorted({p for p in files if p.is_file()}, key=lambda p: str(p))


def find_request_csvs(run_ids: list[str], fallback: Path) -> list[Path]:
    patterns = [
        f"experiments/reports/retention_probe/{run_id}*/retention_probe_requests.csv"
        for run_id in run_ids
    ]
    files = latest_matching_files(patterns)
    if not files and fallback.exists():
        files = [fallback]
    return files


def find_runtime_logs(run_ids: list[str], kind: str) -> list[Path]:
    if kind == "frontend":
        names = ("*frontend_runtime.log", "*frontend*.log")
    else:
        names = ("*worker_runtime.log",)
    patterns: list[str] = []
    for run_id in run_ids:
        for name in names:
            patterns.append(f"experiments/reports/retention_probe_batches/{run_id}*/{name}")
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
    if not text:
        return 0
    return text.count(signal)


def source_present(step: ProofStep) -> bool:
    path = repo_path(step.where)
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return any(token in text for token in snippet_tokens(step.code_snippet))


def snippet_tokens(snippet: str) -> list[str]:
    tokens = []
    for line in snippet.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned == "...":
            continue
        if "..." in cleaned:
            cleaned = cleaned.replace("...", "").strip()
        if cleaned:
            tokens.append(cleaned)
    return tokens or [snippet.strip()]


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


def matrix_evidence(matrix_rows: list[dict[str, str]]) -> dict[str, str]:
    protected = [row for row in matrix_rows if row.get("arm") == "protected"]
    rows = protected or matrix_rows
    req_values = sorted({row.get("req_prio_status", "") for row in rows if row.get("req_prio_status", "")})
    worker_values = sorted({row.get("worker_prio_status", "") for row in rows if row.get("worker_prio_status", "")})
    warm_values = sorted({row.get("warm", "") for row in matrix_rows if row.get("warm", "")})
    return {
        "req_prio_status": ",".join(req_values),
        "worker_prio_status": ",".join(worker_values),
        "warm": ",".join(warm_values),
    }


def build_checks(
    *,
    matrix_rows: list[dict[str, str]],
    request_rows: list[dict[str, str]],
    request_csvs: list[Path],
    frontend_logs: list[Path],
    worker_logs: list[Path],
    sglang_log: Path,
) -> dict[str, tuple[bool, str, str]]:
    frontend_text = read_texts(frontend_logs)
    worker_text = read_texts(worker_logs)
    sglang_text = read_texts([sglang_log] if sglang_log.exists() else [])
    combined_runtime_text = "\n".join(part for part in (frontend_text, worker_text, sglang_text) if part)
    protected_request_rows = [
        row for row in request_rows if row.get("hint_profile") not in {"", "none"}
    ]
    matrix = matrix_evidence(matrix_rows)

    frontend_source = short_paths(frontend_logs) or "frontend log not captured"
    worker_source = short_paths(worker_logs) or "worker log not captured"
    sglang_source = str(sglang_log.relative_to(REPO_ROOT)) if sglang_log.exists() else "SGLang transfer log not found"

    request_has_priority = any_nonempty(protected_request_rows, "agent_hints_priority") or any(
        truthy(row.get("hints_enabled", "")) for row in protected_request_rows
    )
    matrix_has_req_priority = matrix["req_prio_status"] not in {"", "none"}
    matrix_has_worker_priority = matrix["worker_prio_status"] not in {"", "none"}
    sglang_priority_count = event_count(combined_runtime_text, '"event": "sglang.priority"') + event_count(
        combined_runtime_text, '"event":"sglang.priority"'
    )
    sglang_cache_count = event_count(combined_runtime_text, '"event": "sglang.cache"') + event_count(
        combined_runtime_text, '"event":"sglang.cache"'
    )

    return {
        "harness_rows": (
            bool(request_rows),
            "requests CSV",
            f"rows={len(request_rows)}; files={short_paths(request_csvs)}",
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
            event_count(worker_text, "worker.decode.request_received") > 0,
            worker_source,
            f"count={event_count(worker_text, 'worker.decode.request_received')}",
        ),
        "request_priority": (
            request_has_priority or matrix_has_req_priority,
            "requests CSV / matrix CSV",
            f"protected_hint_rows={len(protected_request_rows)}; req_prio_status={matrix['req_prio_status'] or 'none'}",
        ),
        "worker_priority": (
            matrix_has_worker_priority or sglang_priority_count > 0,
            "matrix CSV / SGLang logs",
            f"worker_prio_status={matrix['worker_prio_status'] or 'none'}; sglang_priority_events={sglang_priority_count}",
        ),
        "worker_attached": (
            event_count(worker_text, "worker.decode.request_attached") > 0,
            worker_source,
            f"count={event_count(worker_text, 'worker.decode.request_attached')}",
        ),
        "sglang_events": (
            sglang_priority_count > 0 or sglang_cache_count > 0,
            sglang_source,
            f"sglang.priority={sglang_priority_count}; sglang.cache={sglang_cache_count}",
        ),
        "worker_completed": (
            event_count(worker_text, "worker.decode.request_completed") > 0,
            worker_source,
            f"count={event_count(worker_text, 'worker.decode.request_completed')}",
        ),
        "frontend_completed": (
            event_count(frontend_text, "frontend.request.completed") > 0,
            frontend_source,
            f"count={event_count(frontend_text, 'frontend.request.completed')}",
        ),
        "request_csv_complete": (
            bool(request_rows)
            and any_nonempty(request_rows, "status")
            and any_nonempty(request_rows, "latency_ms"),
            "requests CSV",
            f"rows={len(request_rows)}; status_field={any_nonempty(request_rows, 'status')}; latency_field={any_nonempty(request_rows, 'latency_ms')}",
        ),
        "matrix_rows": (
            bool(matrix_rows),
            "matrix CSV",
            f"rows={len(matrix_rows)}; warm={matrix['warm'] or 'missing'}",
        ),
    }


def markdown_link(step: ProofStep) -> str:
    path = repo_path(step.where)
    label = f"{Path(step.where).name}:{step.line}"
    return f"[{label}]({path}:{step.line})"


def md_escape(value: object) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def write_outputs(rows: list[dict[str, str]], csv_paths: list[Path], md_paths: list[Path]) -> None:
    fieldnames = [
        "step",
        "checked_true",
        "severity",
        "component",
        "when",
        "runtime_signal",
        "evidence_value",
        "meaning_short",
        "failure_meaning",
        "where",
        "what_it_means",
        "code_snippet",
        "evidence_source",
        "request_role",
    ]
    for path in csv_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    for path in md_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        false_rows = [row for row in rows if row.get("checked_true") != "true"]
        false_critical = [row for row in false_rows if row.get("severity") == "critical"]
        false_warning = [row for row in false_rows if row.get("severity") == "warning"]
        lines = [
            "# Experiment 9 Decision Proof",
            "",
            "This table is generated from the latest KV retention run artifacts. The `checked_true` column is runtime/report evidence, not a hand-written claim.",
            "",
            "## Quick Read",
            "",
            f"- rows: `{len(rows)}`",
            f"- false critical rows: `{len(false_critical)}`",
            f"- false warning rows: `{len(false_warning)}`",
            "",
            "| Step | Checked True | Severity | Component | When | Runtime Signal | Evidence Value | Meaning Short | Failure Meaning | Where | What It Means | Code Snippet | Evidence Source | Request Role |",
            "|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for row in rows:
            lines.append(
                "| "
                + " | ".join(
                    md_escape(row[key])
                    for key in (
                        "step",
                        "checked_true",
                        "severity",
                        "component",
                        "when",
                        "runtime_signal",
                        "evidence_value",
                        "meaning_short",
                        "failure_meaning",
                        "where",
                        "what_it_means",
                        "code_snippet",
                        "evidence_source",
                        "request_role",
                    )
                )
                + " |"
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    matrix_csv = repo_path(args.matrix_csv)
    requests_csv = repo_path(args.requests_csv)
    run_contract_json = repo_path(args.run_contract_json)
    sglang_log = repo_path("experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl")

    matrix_rows = read_csv(matrix_csv)
    contract = read_json(run_contract_json)
    run_ids = find_run_ids(matrix_rows, contract)
    request_csvs = find_request_csvs(run_ids, requests_csv)
    request_rows: list[dict[str, str]] = []
    for path in request_csvs:
        request_rows.extend(read_csv(path))

    frontend_logs = find_runtime_logs(run_ids, "frontend")
    worker_logs = find_runtime_logs(run_ids, "worker")
    checks = build_checks(
        matrix_rows=matrix_rows,
        request_rows=request_rows,
        request_csvs=request_csvs,
        frontend_logs=frontend_logs,
        worker_logs=worker_logs,
        sglang_log=sglang_log,
    )

    rows: list[dict[str, str]] = []
    for step in PROOF_STEPS:
        metadata = PROOF_STEP_METADATA.get(
            step.check_name,
            {
                "component": "unknown",
                "severity": "warning",
                "meaning_short": step.what_it_means,
            },
        )
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
                "checked_true": "true" if checked and source_ok else "false",
                "severity": str(metadata["severity"]),
                "component": str(metadata["component"]),
                "when": step.when,
                "runtime_signal": step.runtime_signal,
                "evidence_value": evidence_value,
                "meaning_short": str(metadata["meaning_short"]),
                "failure_meaning": step.failure_meaning,
                "where": markdown_link(step),
                "what_it_means": step.what_it_means,
                "code_snippet": step.code_snippet,
                "evidence_source": evidence_source,
                "request_role": step.request_role,
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
