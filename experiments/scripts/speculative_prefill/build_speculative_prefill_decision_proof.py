#!/usr/bin/env python3
"""Build the Exp12 decision-proof table from latest speculative-prefill artifacts."""

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
    arm: str
    prefill_metric: str
    failure_meaning: str
    check_name: str


PROOF_STEPS = [
    ProofStep(
        1,
        "Harness attaches speculative-prefill hint",
        "experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py",
        1182,
        "The protected arm sends `nvext.agent_hints.speculative_prefill=true`.",
        '"speculative_prefill": spec_prefill',
        "hint_status=on / spec_prefill=True",
        "turn_a",
        "protected",
        "hint_status",
        "The protected arm did not send the speculative-prefill hint.",
        "protected_hint_sent",
    ),
    ProofStep(
        2,
        "Harness names the target turn B request",
        "experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py",
        1184,
        "The hint carries the exact turn-B request id that the warmup should target.",
        '"spec_prefill_target_request_id": target_request_id',
        "spec_prefill_target_request_id / prefill_target_seen",
        "turn_a -> turn_b",
        "protected",
        "prefill_target_seen",
        "The run did not prove that the warmup targeted turn B.",
        "target_metadata_seen",
    ),
    ProofStep(
        3,
        "Dynamo declares the typed hint field",
        "upstream/dynamo/lib/llm/src/protocols/openai/nvext.rs",
        426,
        "Dynamo's OpenAI nvext schema has a real `speculative_prefill` field.",
        "pub speculative_prefill: Option<bool>",
        "source schema + protected hint row",
        "all",
        "protected",
        "schema",
        "The source tree does not expose the speculative-prefill hint field.",
        "nvext_field_present",
    ),
    ProofStep(
        4,
        "Dynamo calls the speculative-prefill wrapper",
        "upstream/dynamo/lib/llm/src/preprocessor.rs",
        1819,
        "The normal response stream passes through the speculative-prefill decision path.",
        "let final_stream = speculative_prefill::maybe_wrap_stream(",
        "worker.spec_prefill.wrap_checked",
        "turn_a",
        "protected",
        "prefill_wrap",
        "The runtime did not show that the speculative-prefill wrapper ran.",
        "wrap_checked",
    ),
    ProofStep(
        5,
        "Prefill gate reads the hint",
        "upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs",
        198,
        "The decision gate reads `hints.speculative_prefill` and decides whether to continue.",
        ".and_then(|hints| hints.speculative_prefill)",
        "worker.spec_prefill.wrap_checked enabled=true",
        "turn_a",
        "protected",
        "prefill_wrap",
        "The runtime did not show the protected hint enabling the prefill gate.",
        "wrap_enabled",
    ),
    ProofStep(
        6,
        "Prefill task is spawned",
        "upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs",
        219,
        "Dynamo launches the background task that will build the next-turn warmup.",
        '"worker.spec_prefill.task_spawned"',
        "worker.spec_prefill.task_spawned / prefill_spawned",
        "turn_a",
        "protected",
        "prefill_spawned",
        "The runtime did not show a background prefill task.",
        "prefill_spawned",
    ),
    ProofStep(
        7,
        "Warmup prompt is rendered",
        "upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs",
        327,
        "Dynamo rendered the predicted next-turn prefix and counted its tokens.",
        '"worker.spec_prefill.prefill_rendered"',
        "worker.spec_prefill.prefill_rendered / prefill_tokens",
        "warmup",
        "protected",
        "prefill_tokens",
        "The runtime did not show a rendered warmup prompt.",
        "prefill_rendered",
    ),
    ProofStep(
        8,
        "Warmup request is sent",
        "upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs",
        356,
        "Dynamo sends the synthetic `max_tokens=1` warmup request into the backend path.",
        '"worker.spec_prefill.prefill_sent"',
        "worker.spec_prefill.prefill_sent / prefill_sent",
        "warmup",
        "protected",
        "prefill_sent",
        "The runtime did not show the warmup request being sent.",
        "prefill_sent",
    ),
    ProofStep(
        9,
        "Warmup request completes",
        "upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs",
        374,
        "Dynamo drains the warmup stream so the prefill lifecycle completes.",
        '"worker.spec_prefill.prefill_completed"',
        "worker.spec_prefill.prefill_completed / prefill_done",
        "warmup",
        "protected",
        "prefill_done",
        "The runtime did not show the warmup request completing.",
        "prefill_done",
    ),
    ProofStep(
        10,
        "Probe parses worker speculative-prefill events",
        "experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py",
        1543,
        "Postprocess collects `worker.spec_prefill.*` events from the worker runtime log.",
        'elif event_type.startswith("worker.spec_prefill."):',
        "spec_events",
        "all",
        "protected",
        "runtime parser",
        "The report did not see speculative-prefill runtime events.",
        "runtime_events_parsed",
    ),
    ProofStep(
        11,
        "Probe maps events into proof columns",
        "experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py",
        1717,
        "The raw runtime events become `prefill_wrap`, `prefill_spawned`, `prefill_sent`, `prefill_done`, and `prefill_target_seen`.",
        '"prefill_wrap": wrap_status\n"prefill_spawned": "worker.spec_prefill.task_spawned" in event_types',
        "prefill_* columns",
        "all",
        "protected",
        "prefill columns",
        "The matrix did not contain usable prefill proof columns.",
        "prefill_columns_present",
    ),
    ProofStep(
        12,
        "Probe classifies the effect",
        "experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py",
        1789,
        "The probe marks whether the protected arm had direct/inferred prefill evidence and whether turn B TTFT or full latency improved.",
        'effect_status = "faster_direct_ttft"',
        "effect_status / effect",
        "turn_b",
        "protected",
        "effect",
        "The protected arm did not show usable speculative-prefill evidence.",
        "effect_visible",
    ),
    ProofStep(
        13,
        "Microbenchmark report normalizes matrix rows",
        "experiments/scripts/speculative_prefill/build_speculative_prefill_microbenchmark_report.py",
        194,
        "The public report carries the probe proof fields into one compact matrix.",
        "def normalize_matrix_rows(",
        "latest_speculative_prefill_microbenchmark_matrix.csv",
        "all",
        "protected",
        "public matrix",
        "The compact matrix was missing protected speculative-prefill rows.",
        "public_matrix_present",
    ),
    ProofStep(
        14,
        "Microbenchmark report carries prefill columns",
        "experiments/scripts/speculative_prefill/build_speculative_prefill_microbenchmark_report.py",
        231,
        "The compact matrix keeps the direct proof columns used by slides and debugging.",
        '"prefill_wrap": pick(row, "prefill_wrap")',
        "prefill_wrap/prefill_sent/prefill_done",
        "all",
        "protected",
        "public prefill columns",
        "The compact matrix dropped the columns needed to prove prefill behavior.",
        "public_prefill_columns",
    ),
    ProofStep(
        15,
        "Microbenchmark report writes public outputs",
        "experiments/scripts/speculative_prefill/build_speculative_prefill_microbenchmark_report.py",
        398,
        "The final public matrix and summary are written from the normalized rows.",
        'write_csv(out_dir / "microbenchmark_matrix.csv", matrix_rows, MATRIX_COLUMNS)',
        "microbenchmark_matrix.csv / microbenchmark_summary.csv",
        "all",
        "protected",
        "public outputs",
        "The public Exp12 matrix or summary was not generated.",
        "public_outputs_present",
    ),
]


PROOF_STEP_METADATA = {
    "protected_hint_sent": {
        "component": "harness",
        "severity": "critical",
        "meaning_short": "The protected request carried the speculative prefill hint.",
    },
    "target_metadata_seen": {
        "component": "harness/runtime",
        "severity": "critical",
        "meaning_short": "The warmup knew which next request it was meant to help.",
    },
    "nvext_field_present": {
        "component": "dynamo schema",
        "severity": "critical",
        "meaning_short": "Dynamo has a typed speculative-prefill hint field.",
    },
    "wrap_checked": {
        "component": "dynamo preprocessor",
        "severity": "critical",
        "meaning_short": "The speculative-prefill wrapper ran.",
    },
    "wrap_enabled": {
        "component": "dynamo preprocessor",
        "severity": "critical",
        "meaning_short": "The protected hint enabled the prefill path.",
    },
    "prefill_spawned": {
        "component": "dynamo preprocessor",
        "severity": "critical",
        "meaning_short": "A background prefill task was spawned.",
    },
    "prefill_rendered": {
        "component": "dynamo preprocessor",
        "severity": "critical",
        "meaning_short": "The warmup prompt was rendered and tokenized.",
    },
    "prefill_sent": {
        "component": "dynamo preprocessor",
        "severity": "critical",
        "meaning_short": "The warmup request was sent into the backend.",
    },
    "prefill_done": {
        "component": "dynamo preprocessor",
        "severity": "critical",
        "meaning_short": "The warmup request completed.",
    },
    "runtime_events_parsed": {
        "component": "postprocess",
        "severity": "critical",
        "meaning_short": "Runtime prefill events were parsed into the report.",
    },
    "prefill_columns_present": {
        "component": "postprocess",
        "severity": "critical",
        "meaning_short": "The matrix includes direct prefill evidence columns.",
    },
    "effect_visible": {
        "component": "postprocess",
        "severity": "critical",
        "meaning_short": "The protected arm showed direct/inferred prefill evidence.",
    },
    "public_matrix_present": {
        "component": "postprocess",
        "severity": "critical",
        "meaning_short": "The public Exp12 matrix was produced.",
    },
    "public_prefill_columns": {
        "component": "postprocess",
        "severity": "critical",
        "meaning_short": "The public matrix preserved the prefill proof columns.",
    },
    "public_outputs_present": {
        "component": "postprocess",
        "severity": "critical",
        "meaning_short": "The public Exp12 summary outputs were generated.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-csv", default="experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv")
    parser.add_argument("--requests-csv", default="experiments/reports/latest_speculative_prefill_requests.csv")
    parser.add_argument("--summary-csv", default="experiments/reports/latest_speculative_prefill_microbenchmark_summary.csv")
    parser.add_argument("--run-contract-json", default="experiments/reports/latest_speculative_prefill_microbenchmark_run_contract.json")
    parser.add_argument("--reports-csv", default="experiments/reports/latest_exp12_decision_proof.csv")
    parser.add_argument("--reports-md", default="experiments/reports/latest_exp12_decision_proof.md")
    parser.add_argument("--charts-csv", default="experiments/charts/exp12_decision_proof.csv")
    parser.add_argument("--charts-md", default="experiments/charts/exp12_decision_proof.md")
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


def read_summary_rows(path: Path, matrix_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = read_csv(path)
    if rows:
        return rows
    benchmark_id = ""
    for row in matrix_rows:
        benchmark_id = str(row.get("benchmark_id", "")).strip()
        if benchmark_id:
            break
    if not benchmark_id:
        return []
    fallback = REPO_ROOT / "experiments" / "reports" / "speculative_prefill_microbenchmark" / benchmark_id / "microbenchmark_summary.csv"
    return read_csv(fallback)


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def to_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(str(value).replace("%", "")))
    except (TypeError, ValueError):
        return 0


def any_nonempty(rows: Iterable[dict[str, str]], *keys: str) -> bool:
    for row in rows:
        for key in keys:
            if str(row.get(key, "")).strip():
                return True
    return False


def protected_rows(matrix_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in matrix_rows if str(row.get("arm", "")).strip().lower() == "protected"]


def protected_hint_sent(matrix_rows: list[dict[str, str]], requests_rows: list[dict[str, str]]) -> bool:
    for row in protected_rows(matrix_rows):
        if truthy(row.get("spec_prefill")) or str(row.get("hint_status", "")).strip().lower() == "on":
            return True
    for row in requests_rows:
        if str(row.get("arm", "")).strip().lower() == "protected" and truthy(row.get("spec_prefill")):
            return True
    return False


def direct_or_inferred_prefill_seen(row: dict[str, str]) -> bool:
    effect = str(row.get("effect") or row.get("effect_status") or "").strip().lower()
    evidence = str(row.get("prefill_evidence_status", "")).strip().lower()
    if truthy(row.get("prefill_spawned")) or truthy(row.get("prefill_sent")) or truthy(row.get("prefill_done")):
        return True
    if effect in {
        "faster_direct",
        "faster_direct_ttft",
        "faster_inferred",
        "faster_inferred_ttft",
        "direct_no_visible_gain",
        "inferred_no_visible_gain",
        "sent_no_visible_gain",
    }:
        return True
    return evidence in {"direct_prefill_seen", "inferred_prefill_seen"}


def find_run_ids(matrix_rows: list[dict[str, str]], contract: dict[str, Any]) -> list[str]:
    ids = [str(row.get("run_id", "")).strip() for row in matrix_rows if row.get("run_id")]
    for key in ("probe_run_id", "SPEC_PREFILL_ID"):
        value = str(contract.get(key, "")).strip()
        if value:
            ids.append(value)
    sweep_ids = contract.get("sweep_run_ids")
    if isinstance(sweep_ids, list):
        ids.extend(str(item).strip() for item in sweep_ids if str(item).strip())
    contract_env = contract.get("contract_env")
    if isinstance(contract_env, dict):
        value = str(contract_env.get("SPEC_PREFILL_ID", "")).strip()
        if value:
            ids.append(value)
    seen: set[str] = set()
    unique: list[str] = []
    for run_id in ids:
        if run_id and run_id not in seen:
            seen.add(run_id)
            unique.append(run_id)
    return unique


def find_worker_logs(run_ids: list[str]) -> list[Path]:
    paths: list[Path] = []
    for run_id in run_ids:
        paths.extend(REPO_ROOT.glob(f"experiments/reports/speculative_prefill/{run_id}*/speculative_prefill_worker_runtime*.log"))
    return sorted({p for p in paths if p.is_file()}, key=lambda p: str(p))


def read_texts(paths: Iterable[Path]) -> str:
    parts: list[str] = []
    for path in paths:
        try:
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
    return "\n".join(parts)


def event_count(text: str, event_type: str) -> int:
    return text.count(event_type) if text else 0


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
    summary_rows: list[dict[str, str]],
    worker_logs: list[Path],
) -> dict[str, tuple[bool, str, str]]:
    protected = protected_rows(matrix_rows)
    worker_text = read_texts(worker_logs)
    worker_source = short_paths(worker_logs) or "worker log not captured"

    wrap_count = event_count(worker_text, "worker.spec_prefill.wrap_checked")
    spawned_count = event_count(worker_text, "worker.spec_prefill.task_spawned")
    rendered_count = event_count(worker_text, "worker.spec_prefill.prefill_rendered")
    sent_count = event_count(worker_text, "worker.spec_prefill.prefill_sent")
    done_count = event_count(worker_text, "worker.spec_prefill.prefill_completed")
    target_count = event_count(worker_text, "spec_prefill_target_request_id")

    protected_hint = protected_hint_sent(matrix_rows, requests_rows)
    target_seen = any(truthy(row.get("prefill_target_seen")) for row in protected) or target_count > 0
    wrap_seen = any(str(row.get("prefill_wrap", "")).strip().lower() in {"on", "off", "inferred_on"} for row in protected) or wrap_count > 0
    wrap_enabled = any(str(row.get("prefill_wrap", "")).strip().lower() in {"on", "inferred_on"} for row in protected) or (
        wrap_count > 0 and protected_hint
    )
    spawned_seen = any(truthy(row.get("prefill_spawned")) for row in protected) or spawned_count > 0
    rendered_seen = any(to_int(row.get("prefill_tokens")) > 0 for row in protected) or rendered_count > 0
    sent_seen = any(truthy(row.get("prefill_sent")) for row in protected) or sent_count > 0
    done_seen = any(truthy(row.get("prefill_done")) for row in protected) or done_count > 0
    usable_effect = any(direct_or_inferred_prefill_seen(row) for row in protected)
    positive_latency_gain = any(to_int(row.get("turn_b_gain_ms")) > 0 for row in protected)
    positive_ttft_gain = any(to_int(row.get("turn_b_ttft_gain_ms")) > 0 for row in protected)
    prefill_columns = bool(protected) and all(
        key in protected[0]
        for key in ("prefill_wrap", "prefill_spawned", "prefill_sent", "prefill_done", "prefill_target_seen")
    )
    public_outputs = bool(matrix_rows) and bool(summary_rows)

    return {
        "protected_hint_sent": (
            protected_hint,
            "matrix CSV / requests CSV",
            f"protected_rows={len(protected)}; hint_status_values={sorted({row.get('hint_status','') for row in protected})}",
        ),
        "target_metadata_seen": (
            target_seen,
            worker_source if target_count > 0 else "matrix CSV",
            f"prefill_target_seen_rows={sum(1 for row in protected if truthy(row.get('prefill_target_seen')))}; runtime_target_mentions={target_count}",
        ),
        "nvext_field_present": (
            protected_hint,
            "source schema + matrix CSV",
            f"protected_hint_sent={protected_hint}",
        ),
        "wrap_checked": (
            wrap_seen,
            worker_source if wrap_count > 0 else "matrix CSV",
            f"wrap_checked_events={wrap_count}; prefill_wrap_values={sorted({row.get('prefill_wrap','') for row in protected})}",
        ),
        "wrap_enabled": (
            wrap_enabled,
            worker_source if wrap_count > 0 else "matrix CSV",
            f"wrap_checked_events={wrap_count}; protected_hint_sent={protected_hint}; prefill_wrap_values={sorted({row.get('prefill_wrap','') for row in protected})}",
        ),
        "prefill_spawned": (
            spawned_seen,
            worker_source if spawned_count > 0 else "matrix CSV",
            f"task_spawned_events={spawned_count}; prefill_spawned_rows={sum(1 for row in protected if truthy(row.get('prefill_spawned')))}",
        ),
        "prefill_rendered": (
            rendered_seen,
            worker_source if rendered_count > 0 else "matrix CSV",
            f"prefill_rendered_events={rendered_count}; max_prefill_tokens={max([to_int(row.get('prefill_tokens')) for row in protected] + [0])}",
        ),
        "prefill_sent": (
            sent_seen,
            worker_source if sent_count > 0 else "matrix CSV",
            f"prefill_sent_events={sent_count}; prefill_sent_rows={sum(1 for row in protected if truthy(row.get('prefill_sent')))}",
        ),
        "prefill_done": (
            done_seen,
            worker_source if done_count > 0 else "matrix CSV",
            f"prefill_completed_events={done_count}; prefill_done_rows={sum(1 for row in protected if truthy(row.get('prefill_done')))}",
        ),
        "runtime_events_parsed": (
            wrap_count + spawned_count + rendered_count + sent_count + done_count > 0,
            worker_source if worker_text else "matrix CSV",
            f"spec_prefill_runtime_events={wrap_count + spawned_count + rendered_count + sent_count + done_count}; usable_effect={usable_effect}",
        ),
        "prefill_columns_present": (
            prefill_columns,
            "matrix CSV",
            f"protected_rows={len(protected)}; prefill_columns_present={prefill_columns}",
        ),
        "effect_visible": (
            usable_effect or positive_latency_gain or positive_ttft_gain,
            "matrix CSV",
            f"effects={sorted({row.get('effect') or row.get('effect_status') or '' for row in protected})}; positive_latency_gain={positive_latency_gain}; positive_ttft_gain={positive_ttft_gain}",
        ),
        "public_matrix_present": (
            bool(protected),
            "matrix CSV",
            f"matrix_rows={len(matrix_rows)}; protected_rows={len(protected)}",
        ),
        "public_prefill_columns": (
            prefill_columns,
            "matrix CSV",
            f"columns={','.join(protected[0].keys()) if protected else 'none'}",
        ),
        "public_outputs_present": (
            public_outputs,
            "matrix CSV / summary CSV",
            f"matrix_rows={len(matrix_rows)}; summary_rows={len(summary_rows)}",
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
        "arm",
        "prefill_metric",
    ]
    for path in csv_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    for path in md_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Experiment 12 Decision Proof",
            "",
            "This table is generated from the latest speculative-prefill artifacts. The `checked_true` column is runtime/report evidence, not a hand-written claim.",
            "",
            "## Quick Read",
            "",
            f"- rows: `{len(rows)}`",
            f"- false critical rows: `{sum(1 for row in rows if row.get('checked_true') != 'true' and row.get('severity') == 'critical')}`",
            f"- false warning rows: `{sum(1 for row in rows if row.get('checked_true') != 'true' and row.get('severity') == 'warning')}`",
            "",
            "| Step | Checked True | Severity | Component | When | Runtime Signal | Evidence Value | Meaning Short | Failure Meaning | Where | What It Means | Code Snippet | Evidence Source | Request Role | Arm | Prefill Metric |",
            "|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for row in rows:
            lines.append("| " + " | ".join(md_escape(row[key]) for key in fieldnames) + " |")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    matrix_csv = repo_path(args.matrix_csv)
    requests_csv = repo_path(args.requests_csv)
    summary_csv = repo_path(args.summary_csv)
    run_contract_json = repo_path(args.run_contract_json)

    matrix_rows = read_csv(matrix_csv)
    requests_rows = read_csv(requests_csv)
    summary_rows = read_summary_rows(summary_csv, matrix_rows)
    contract = read_json(run_contract_json)
    run_ids = find_run_ids(matrix_rows, contract)
    worker_logs = find_worker_logs(run_ids)
    checks = build_checks(
        matrix_rows=matrix_rows,
        requests_rows=requests_rows,
        summary_rows=summary_rows,
        worker_logs=worker_logs,
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
                "arm": step.arm,
                "prefill_metric": step.prefill_metric,
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
