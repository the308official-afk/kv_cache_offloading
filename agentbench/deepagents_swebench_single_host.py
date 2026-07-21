#!/usr/bin/env python3

"""Run one SWE-bench Pro task through Deep Agents against a local Dynamo frontend."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

CURRENT_FILE = Path(__file__).resolve()
REPO_ROOT = CURRENT_FILE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from datasets import load_dataset
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "datasets is required. Install with: python3 -m pip install -r agentbench/requirements.txt"
    ) from exc

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "pandas is required. Install with: python3 -m pip install -r agentbench/requirements.txt"
    ) from exc

try:
    import openpyxl  # noqa: F401
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "openpyxl is required. Install with: python3 -m pip install -r agentbench/requirements.txt"
    ) from exc

try:
    from agentbench.deepagents_app.src.agent import (
        frontend_base_url,
        load_agent_instructions,
        run_task_workflow,
    )
    from agentbench.deepagents_app.src.hint_providers import (
        HINT_PROVIDER_AGENTBENCH,
        HINT_PROVIDERS,
        normalize_hint_provider,
    )
    from agentbench.log_utils import (
        load_logged_events,
        log_checkpoint,
        log_lifecycle_event,
        set_checkpoint_log_file,
        set_lifecycle_log_file,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "The Deep Agents app modules could not be imported. "
        "If dependencies are missing, install them with: python3 -m pip install -r agentbench/requirements.txt. "
        f"Original import error: {exc}"
    ) from exc


DEFAULT_RESULTS_DIR = REPO_ROOT / "experiments" / "raw" / "agentbench" / "results"
RESULTS_DIR = Path(os.environ.get("AGENTBENCH_RESULTS_DIR", str(DEFAULT_RESULTS_DIR))).expanduser()
if not RESULTS_DIR.is_absolute():
    RESULTS_DIR = REPO_ROOT / RESULTS_DIR
REPOS_DIR = REPO_ROOT / "agentbench" / "repos"
DEFAULT_RESULTS_TIMEZONE = "America/Chicago"
RECURSION_SOFT_STOP_EXIT_CODE = 20
DEFAULT_HINTS = {
    "priority": 5,
    "reuse_likelihood": 0.9,
    "agent_phase": "execution",
    "latency_sensitivity": 0.7,
    "program_id": "agentbench.deepagents_app",
    "context_type": "software_engineering_long_horizon",
    "expected_output_tokens": 512,
}
HINT_PROFILES = {
    "baseline": {},
    "high-reuse": {
        "priority": 5,
        "reuse_likelihood": 1.0,
        "latency_sensitivity": 0.5,
        "expected_output_tokens": 512,
    },
    "low-reuse": {
        "priority": 5,
        "reuse_likelihood": 0.0,
        "latency_sensitivity": 0.5,
        "expected_output_tokens": 512,
    },
    "high-priority": {
        "priority": 10,
        "reuse_likelihood": 0.5,
        "latency_sensitivity": 1.0,
        "expected_output_tokens": 512,
    },
    "low-priority": {
        "priority": 1,
        "reuse_likelihood": 0.5,
        "latency_sensitivity": 0.2,
        "expected_output_tokens": 512,
    },
    "long-output": {
        "priority": 5,
        "reuse_likelihood": 0.8,
        "latency_sensitivity": 0.5,
        "expected_output_tokens": 2048,
    },
    "short-output": {
        "priority": 5,
        "reuse_likelihood": 0.8,
        "latency_sensitivity": 0.5,
        "expected_output_tokens": 128,
    },
}
FRONTEND_CONTAINER_NAME = "dynamo-frontend"
WORKER_CONTAINER_NAME = "dynamo-sglang-worker"
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
FRONTEND_SELECTION_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[0-9:.]+Z).*Selected worker: "
    r"worker_id=(?P<worker_id>\d+) dp_rank=(?P<dp_rank>\d+), "
    r"logit: (?P<logit>-?\d+(?:\.\d+)?), cached blocks: (?P<cached_blocks>\d+), "
    r"tree size: (?P<tree_size>\d+), total blocks: (?P<total_blocks>\d+)"
)
WORKER_PREFILL_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[0-9:.]+Z).*Prefill batch, "
    r"#new-seq: (?P<new_seq>\d+), #new-token: (?P<new_token>\d+), "
    r"#cached-token: (?P<cached_token>\d+), token usage: (?P<token_usage>\d+(?:\.\d+)?), "
    r"#running-req: (?P<running_req>\d+), #queue-req: (?P<queue_req>\d+), "
    r"input throughput \(token/s\): (?P<input_throughput>\d+(?:\.\d+)?), "
    r"cuda graph: (?P<cuda_graph>True|False)"
)
WORKER_DECODE_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[0-9:.]+Z).*Decode batch, "
    r"#running-req: (?P<running_req>\d+), #token: (?P<token>\d+), "
    r"token usage: (?P<token_usage>\d+(?:\.\d+)?), cuda graph: (?P<cuda_graph>True|False), "
    r"gen throughput \(token/s\): (?P<gen_throughput>\d+(?:\.\d+)?), #queue-req: (?P<queue_req>\d+)"
)
PROVENANCE_LABELS = ("MEASURED", "DERIVED", "SPECULATIVE")
PROVENANCE_SCHEMA = {"labels": list(PROVENANCE_LABELS), "version": 1}
MEASURED_FIELDS = {
    "task_index",
    "task_source",
    "task_metadata",
    "instance_id",
    "repo",
    "app_variant",
    "phase",
    "step_index",
    "step_title",
    "model",
    "model_name",
    "model_name_reported",
    "frontend_url",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "prompt_tokens",
    "completion_tokens",
    "cached_prompt_tokens",
    "finish_reason",
    "prompt_chars",
    "prompt_lines",
    "prompt_preview",
    "request_id",
    "parent_run_id",
    "task_instance_id",
    "worker_id",
    "worker_host",
    "request_hints",
    "cached_token_count",
    "reused_prefix_tokens",
    "actual_tier",
    "stayed_on_gpu",
    "moved_to_cpu",
    "moved_to_nvme",
    "fetched_from_cpu",
    "fetched_from_nvme",
    "recomputed_instead_of_fetch",
    "eviction_happened",
    "evicted_block_count",
    "evicted_token_estimate",
    "eviction_reason",
    "ttft_ms",
    "end_to_end_ms",
    "prefill_ms",
    "decode_ms",
    "fetch_ms",
    "recompute_ms",
    "dp_rank",
    "logit",
    "cached_blocks",
    "tree_size",
    "total_blocks",
    "prefill_timestamp",
    "first_decode_timestamp",
    "last_decode_timestamp",
    "new_seq_count",
    "new_token_count",
    "prefill_token_usage",
    "prefill_running_req",
    "prefill_queue_req",
    "input_throughput_tps",
    "prefill_cuda_graph",
    "decode_event_count",
    "max_decode_tokens",
    "max_decode_queue_req",
    "max_gen_throughput_tps",
    "decode_cuda_graph_seen",
    "prompt",
    "decomposition_plan",
    "step_results",
    "response_text",
    "result",
    "task",
    "workspace",
    "workspace_artifacts",
    "hint_json",
    "hint_profile",
    "run_started_at",
    "active_harness",
    "deepagents_runtime_source",
    "checkpoint_log_file",
    "auto_repo_checkout",
    "source",
    "docker_available",
    "frontend_log_file",
    "worker_log_file",
    "git_head",
    "git_status",
    "git_diff_stat",
    "git_untracked_files",
    "patch_file",
    "patch_nonempty",
    "workspace_present",
    "workspace_path",
    "git_repo",
    "timestamp",
    "stage",
    "event_kind",
    "artifact_name",
    "artifact_path",
    "artifact_format",
    "artifact_size_bytes",
    "payload_json",
    "response_preview",
    "system_prompt",
    "system_prompt_chars",
    "system_prompt_lines",
    "system_prompt_preview",
    "base_task_prompt",
    "approved_plan",
    "prior_step_summaries",
    "step_summaries",
    "workspace_dir",
}
DERIVED_FIELDS = {
    "call_count",
    "phase_counts",
    "total_model_latency_ms",
    "large_prompt_calls",
    "prefill_decode_profile",
    "reuse_signal",
    "pressure_risk",
    "most_prefill_heavy_phase",
    "strongest_reuse_phase",
    "highest_pressure_phase",
    "highest_pressure_risk",
    "slowest_phase",
    "slowest_phase_latency_ms",
    "reuse_score",
    "priority_score",
    "latency_value_score",
    "size_penalty_score",
    "cache_hit",
    "recomputed_prefix_tokens",
    "router_mode",
    "runtime_reuse_strength",
    "alignment_status",
    "runtime_signal_source",
    "frontend_event_found",
    "worker_observation_found",
    "direct_tier_verification_available",
    "observed_worker_count",
    "observed_workers",
    "fully_aligned_runtime_events",
    "indirect_support_count",
    "unverifiable_row_count",
    "best_supported_gpu_candidate",
    "strategy",
    "sequence_index",
    "measurements_summary",
    "event_count",
    "stage_counts",
    "stages_seen",
    "phases_seen",
    "prompt_event_count",
    "request_event_count",
    "response_event_count",
    "artifact_event_count",
    "stage_description",
    "stage_component",
    "stage_category",
    "hint_row_count",
    "propagated_count",
    "frontend_observed_count",
    "worker_observed_count",
    "behavior_supported_count",
    "not_proven_count",
    "metadata_matched_count",
    "metadata_only_count",
    "direct_sglang_hint_evidence",
    "hint_probe_id",
    "probe_status",
    "probe_request_wrapper_observed",
    "probe_frontend_observed",
    "probe_worker_observed",
    "frontend_agent_hints_sources",
    "worker_agent_hints_sources",
    "request_wrapper_observed",
    "dynamo_frontend_observed",
    "sglang_worker_observed",
    "expected_runtime_effect",
    "observed_runtime_effect",
    "claim_level",
}
SPECULATIVE_FIELDS = {
    "recency_score",
    "future_turn_score",
    "cache_value_score",
    "keep_recommendation",
    "recommended_tier",
    "movement_priority",
    "reason",
    "keep_candidates",
    "evict_first_candidates",
    "gpu_candidates",
    "cpu_candidates",
    "nvme_candidates",
    "drop_candidates",
    "highest_value_phase",
    "lowest_value_phase",
    "best_gpu_candidate_phase",
}
HINT_RUNTIME_EXPECTATIONS = {
    "expected_output_tokens": "The runtime should use a generation budget consistent with this value.",
    "reuse_likelihood": "Cache/routing behavior should show reuse when useful context is available.",
    "priority": "A scheduler should be able to prefer this request when there is contention.",
    "latency_sensitivity": "Routing or scheduling should prefer lower latency when there is a real choice.",
    "agent_phase": "The phase label should match the request/run phase for traceability.",
    "program_id": "The program label should be retained as observability metadata.",
    "context_type": "The workload label should be retained as observability metadata.",
    "hint_probe_id": "The probe marker should appear in every layer that receives the hint payload.",
}
HINT_METADATA_ONLY = {"agent_phase", "program_id", "context_type"}

TASK_LIFECYCLE_STAGE_METADATA = {
    "run_initialized": {
        "description": "Run directory, ids, and top-level execution context were initialized.",
        "component": "agentbench_runner",
        "category": "workflow",
    },
    "task_retrieved": {
        "description": "The sample task was loaded from SWE-bench, CSV, or JSON into AgentBench.",
        "component": "agentbench_runner",
        "category": "task_ingest",
    },
    "auto_repo_checkout_evaluated": {
        "description": "The harness decided whether to infer and materialize the task repository automatically.",
        "component": "workspace_manager",
        "category": "workspace",
    },
    "workspace_prepared": {
        "description": "The writable workspace or shared checkout was prepared for the task run.",
        "component": "workspace_manager",
        "category": "workspace",
    },
    "workspace_path_attached_to_task": {
        "description": "The resolved workspace path was attached back onto the task payload.",
        "component": "workspace_manager",
        "category": "workspace",
    },
    "workflow_invocation_started": {
        "description": "The outer runner began the handoff into the Deep Agents workflow.",
        "component": "agentbench_runner",
        "category": "workflow",
    },
    "task_workflow_started": {
        "description": "The app-layer multi-step workflow started for this task.",
        "component": "deepagents_app",
        "category": "workflow",
    },
    "task_prompt_built": {
        "description": "The canonical task prompt was constructed from the task payload.",
        "component": "prompt_builder",
        "category": "prompt",
    },
    "workflow_hints_resolved": {
        "description": "Base Dynamo and agent hints were resolved for the workflow.",
        "component": "deepagents_app",
        "category": "workflow",
    },
    "baseline_agent_system_prompt_loaded": {
        "description": "The Deep Agents system and app instructions were loaded for the baseline agent invocation.",
        "component": "prompt_builder",
        "category": "prompt",
    },
    "baseline_agent_request_prepared": {
        "description": "A single upstream-style baseline request context and hints were prepared.",
        "component": "deepagents_app",
        "category": "request_prep",
    },
    "baseline_agent_request_dispatched": {
        "description": "The baseline Deep Agents request was sent from the app to the Dynamo frontend.",
        "component": "request_dispatch",
        "category": "dispatch",
    },
    "baseline_agent_response_received": {
        "description": "The baseline Deep Agents response was received from the model.",
        "component": "deepagents_app",
        "category": "response",
    },
    "planning_request_prepared": {
        "description": "Planning-phase request context and hint payload were prepared.",
        "component": "deepagents_app",
        "category": "request_prep",
    },
    "planning_prompt_built": {
        "description": "The planning prompt was assembled before being sent to the model.",
        "component": "prompt_builder",
        "category": "prompt",
    },
    "planning_request_dispatched": {
        "description": "The planning request was sent from the app to the Dynamo frontend.",
        "component": "request_dispatch",
        "category": "dispatch",
    },
    "planning_response_received": {
        "description": "The planning response came back and was parsed into step candidates.",
        "component": "deepagents_app",
        "category": "response",
    },
    "step_request_prepared": {
        "description": "Per-step request context and hints were prepared for a decomposition step.",
        "component": "deepagents_app",
        "category": "request_prep",
    },
    "step_agent_system_prompt_loaded": {
        "description": "The Deep Agents system and app instructions were loaded for a step agent invocation.",
        "component": "prompt_builder",
        "category": "prompt",
    },
    "step_prompt_built": {
        "description": "The step execution prompt was assembled with plan and prior-step context.",
        "component": "prompt_builder",
        "category": "prompt",
    },
    "step_request_dispatched": {
        "description": "A step execution request was sent from the app to the Dynamo frontend.",
        "component": "request_dispatch",
        "category": "dispatch",
    },
    "step_response_received": {
        "description": "A step execution response was received and summarized.",
        "component": "deepagents_app",
        "category": "response",
    },
    "synthesis_request_prepared": {
        "description": "Final synthesis request context and hints were prepared.",
        "component": "deepagents_app",
        "category": "request_prep",
    },
    "synthesis_prompt_built": {
        "description": "The final synthesis prompt was built from the task, plan, and step results.",
        "component": "prompt_builder",
        "category": "prompt",
    },
    "synthesis_request_dispatched": {
        "description": "The synthesis request was sent from the app to the Dynamo frontend.",
        "component": "request_dispatch",
        "category": "dispatch",
    },
    "synthesis_response_received": {
        "description": "The final synthesis response was received from the model.",
        "component": "deepagents_app",
        "category": "response",
    },
    "task_workflow_completed": {
        "description": "The app-layer workflow finished and returned plan, steps, result, and measurements.",
        "component": "deepagents_app",
        "category": "workflow",
    },
    "workflow_invocation_completed": {
        "description": "Control returned from the Deep Agents workflow back to the outer runner.",
        "component": "agentbench_runner",
        "category": "workflow",
    },
    "artifact_written": {
        "description": "A run artifact file was written to disk.",
        "component": "artifact_writer",
        "category": "artifact",
    },
    "runtime_logs_collected": {
        "description": "Frontend and worker runtime logs were collected after the run.",
        "component": "runtime_log_collector",
        "category": "runtime",
    },
    "runtime_events_built": {
        "description": "Runtime-side observations were transformed into structured runtime events.",
        "component": "runtime_event_builder",
        "category": "runtime",
    },
    "workspace_artifacts_collected": {
        "description": "Workspace patch, git status, and diff artifacts were collected.",
        "component": "workspace_manager",
        "category": "workspace",
    },
    "frontend_dynamo_runtime_observed": {
        "description": "A frontend-side runtime observation was aligned to this request from Dynamo logs.",
        "component": "frontend_dynamo",
        "category": "runtime",
    },
    "kv_router_worker_selected": {
        "description": "The KV router selected a worker for this request using scheduler and cache signals.",
        "component": "kv_router",
        "category": "runtime",
    },
    "sglang_worker_prefill_observed": {
        "description": "The SGLang worker emitted a prefill-batch observation for this request.",
        "component": "sglang_worker",
        "category": "runtime",
    },
    "sglang_worker_first_decode_observed": {
        "description": "The SGLang worker emitted the first decode observation for this request.",
        "component": "sglang_worker",
        "category": "runtime",
    },
    "sglang_worker_decode_completed": {
        "description": "The last decode observation currently available for this request was recorded from the SGLang worker.",
        "component": "sglang_worker",
        "category": "runtime",
    },
}


def classify_provenance(artifact: str, path: tuple[str, ...], value) -> str:
    leaf = path[-1] if path else artifact
    if leaf in MEASURED_FIELDS:
        return "MEASURED"
    if leaf in DERIVED_FIELDS:
        return "DERIVED"
    if leaf in SPECULATIVE_FIELDS:
        return "SPECULATIVE"

    if artifact == "measurements":
        return "MEASURED"
    if artifact == "measurement_analysis":
        return "DERIVED"
    if artifact == "runtime_events":
        return "MEASURED"
    if artifact == "runtime_alignment_analysis":
        return "DERIVED"
    if artifact == "runtime_hint_alignment_analysis":
        return "DERIVED"
    if artifact == "stage_lifecycle_trace":
        return "MEASURED"
    if artifact == "cache_value_analysis":
        return "SPECULATIVE"
    if artifact == "kv_hierarchy_analysis":
        return "SPECULATIVE"
    if artifact in {"plan", "step_results", "result"}:
        return "MEASURED"
    return "MEASURED"


def annotate_with_provenance(data, artifact: str, path: tuple[str, ...] = (), include_schema: bool = True):
    if isinstance(data, dict):
        annotated = {}
        provenance = {}
        for key, value in data.items():
            if key in {"_provenance", "_provenance_schema"}:
                continue
            child_path = path + (str(key),)
            annotated[key] = annotate_with_provenance(
                value,
                artifact,
                child_path,
                include_schema=False,
            )
            if isinstance(value, dict):
                provenance[key] = {"_container": classify_provenance(artifact, child_path, value)}
            elif isinstance(value, list):
                provenance[key] = {"_container": classify_provenance(artifact, child_path, value)}
            else:
                provenance[key] = classify_provenance(artifact, child_path, value)
        annotated["_provenance"] = provenance
        if include_schema:
            annotated["_provenance_schema"] = PROVENANCE_SCHEMA
        return annotated
    if isinstance(data, list):
        return [
            annotate_with_provenance(item, artifact, path + (str(index),), include_schema=False)
            if isinstance(item, (dict, list))
            else item
            for index, item in enumerate(data)
        ]
    return data


def strip_provenance(data):
    if isinstance(data, dict):
        return {
            key: strip_provenance(value)
            for key, value in data.items()
            if key not in {"_provenance", "_provenance_schema"}
        }
    if isinstance(data, list):
        return [strip_provenance(item) for item in data]
    return data


def write_json_artifact(run_dir: Path, filename: str, payload, artifact: str, *, annotate: bool = True) -> Path:
    output_path = run_dir / filename
    body = annotate_with_provenance(payload, artifact) if annotate else payload
    output_path.write_text(
        json.dumps(body, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )
    return output_path


def row_with_provenance(row: dict, artifact: str) -> dict:
    flattened = {}
    for key, value in row.items():
        flattened[key] = value
        if isinstance(value, (str, int, float, bool)) or value is None:
            flattened[f"{key}_provenance"] = classify_provenance(artifact, (key,), value)
    return flattened


def markdown_value(value) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "-"
    return str(value)


def markdown_field_table(
    record: dict,
    artifact: str,
    ordered_fields: list[tuple[str, str]],
    *,
    include_provenance: bool = True,
) -> list[str]:
    if include_provenance:
        lines = [
            "| Field | Value | Provenance |",
            "| --- | --- | --- |",
        ]
    else:
        lines = [
            "| Field | Value |",
            "| --- | --- |",
        ]
    for field, label in ordered_fields:
        value = record.get(field)
        if include_provenance:
            provenance = classify_provenance(artifact, (field,), value)
            lines.append(f"| {label} | {markdown_value(value)} | {provenance} |")
        else:
            lines.append(f"| {label} | {markdown_value(value)} |")
    return lines


def task_lifecycle_stage_metadata(stage: object) -> dict[str, str]:
    if isinstance(stage, str):
        metadata = TASK_LIFECYCLE_STAGE_METADATA.get(stage)
        if metadata is not None:
            return metadata
    return {
        "description": "No stage description has been defined for this lifecycle event yet.",
        "component": "unknown",
        "category": "unknown",
    }


def write_csv_table(run_dir: Path, filename: str, rows: list[dict]) -> Path:
    output_path = run_dir / filename
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def _lineage_message_text(message: Any) -> str:
    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                chunks.append(str(item["text"]))
            else:
                chunks.append(str(item))
        return "\n".join(chunks)
    if content is None:
        return ""
    return str(content)


def _lineage_messages(response: Any) -> list[dict[str, Any]]:
    messages = None
    if isinstance(response, dict):
        messages = response.get("messages")
    else:
        messages = getattr(response, "messages", None)
    if not isinstance(messages, list):
        return []

    normalized: list[dict[str, Any]] = []
    for index, message in enumerate(messages):
        if isinstance(message, dict):
            tool_calls = message.get("tool_calls") or []
            invalid_tool_calls = message.get("invalid_tool_calls") or []
            name = message.get("name")
            message_type = message.get("type")
            message_id = message.get("id")
        else:
            tool_calls = getattr(message, "tool_calls", None) or []
            invalid_tool_calls = getattr(message, "invalid_tool_calls", None) or []
            name = getattr(message, "name", None)
            message_type = getattr(message, "type", None)
            message_id = getattr(message, "id", None)

        normalized.append(
            {
                "index": index,
                "type": message_type,
                "name": name,
                "id": message_id,
                "text": _lineage_message_text(message),
                "text_preview": _prompt_preview(_lineage_message_text(message)),
                "tool_calls": tool_calls,
                "invalid_tool_calls": invalid_tool_calls,
                "tool_call_count": len(tool_calls),
                "invalid_tool_call_count": len(invalid_tool_calls),
                "tool_call_names": [
                    call.get("name")
                    for call in tool_calls
                    if isinstance(call, dict) and call.get("name")
                ],
            }
        )
    return normalized


def _extract_tool_parser_usage(frontend_log_file: str | None) -> dict[str, Any]:
    if not frontend_log_file:
        return {
            "tool_parser_names_seen": [],
            "tool_parser_observed": False,
        }

    log_path = Path(frontend_log_file)
    if not log_path.exists():
        return {
            "tool_parser_names_seen": [],
            "tool_parser_observed": False,
        }

    parser_names: list[str] = []
    pattern = re.compile(r'Using tool parser: Some\("(?P<name>[^"]+)"\)')
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = pattern.search(line)
        if match:
            parser_names.append(match.group("name"))

    unique_names = sorted(set(parser_names))
    return {
        "tool_parser_names_seen": unique_names,
        "tool_parser_observed": bool(unique_names),
    }


def _extract_execute_failure(messages: list[dict[str, Any]]) -> str | None:
    for message in messages:
        if message.get("type") != "tool" or message.get("name") != "execute":
            continue
        text = str(message.get("text") or "").strip()
        if text:
            return _prompt_preview(text, 220)
    return None


def _runtime_json_records(log_file: str | None) -> list[dict[str, Any]]:
    if not log_file:
        return []
    path = Path(log_file)
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    marker = "[RUNTIME_JSON]"
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = _strip_ansi(raw_line)
        if marker not in line:
            continue
        payload = line.split(marker, 1)[1].strip()
        json_start = payload.find("{")
        if json_start == -1:
            continue
        try:
            parsed = json.loads(payload[json_start:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _record_agent_hints(record: dict[str, Any]) -> dict[str, Any] | None:
    agent_hints = record.get("agent_hints")
    if isinstance(agent_hints, dict):
        return agent_hints

    nvext = record.get("nvext")
    if isinstance(nvext, dict) and isinstance(nvext.get("agent_hints"), dict):
        return nvext["agent_hints"]

    runtime_observability = record.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        nested_hints = runtime_observability.get("agent_hints")
        if isinstance(nested_hints, dict):
            return nested_hints
        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict) and isinstance(nested_nvext.get("agent_hints"), dict):
            return nested_nvext["agent_hints"]

    return None


def _runtime_hint_log_summary(log_file: str | None) -> dict[str, Any]:
    records = _runtime_json_records(log_file)
    observed_values: dict[str, list[Any]] = {}
    agent_hints_sources: list[str] = []
    agent_hints_null_count = 0
    agent_hints_non_null_count = 0

    for record in records:
        if "agent_hints" in record and record.get("agent_hints") is None:
            agent_hints_null_count += 1
        source = record.get("agent_hints_source")
        if isinstance(source, str) and source and source not in agent_hints_sources:
            agent_hints_sources.append(source)
        probe_id = record.get("hint_probe_id")
        if probe_id:
            values = observed_values.setdefault("hint_probe_id", [])
            if not any(_hint_values_equal(probe_id, existing) for existing in values):
                values.append(probe_id)
        hints = _record_agent_hints(record)
        if not hints:
            continue
        agent_hints_non_null_count += 1
        for key, value in hints.items():
            values = observed_values.setdefault(str(key), [])
            if not any(_hint_values_equal(value, existing) for existing in values):
                values.append(value)

    return {
        "runtime_json_event_count": len(records),
        "agent_hints_null_count": agent_hints_null_count,
        "agent_hints_non_null_count": agent_hints_non_null_count,
        "agent_hints_sources": agent_hints_sources,
        "observed_values": observed_values,
    }


def _hint_values_equal(left: Any, right: Any) -> bool:
    if left == right:
        return True
    return str(left) == str(right)


def _hint_observed(log_summary: dict[str, Any], hint_name: str, hint_value: Any) -> bool:
    values = (log_summary.get("observed_values") or {}).get(hint_name) or []
    return any(_hint_values_equal(hint_value, value) for value in values)


def _hint_component_state(log_summary: dict[str, Any], hint_name: str, hint_value: Any) -> str:
    if _hint_observed(log_summary, hint_name, hint_value):
        return "observed"
    if log_summary.get("agent_hints_non_null_count"):
        return "not_observed"
    if log_summary.get("agent_hints_null_count"):
        return "logged_null"
    if log_summary.get("runtime_json_event_count"):
        return "runtime_json_without_hints"
    return "not_logged"


PROMPT_EVOLUTION_STAGE_COMPONENTS = {
    "task_input": "agentbench_runner",
    "formatted_prompt": "prompt_builder",
    "final_model_request": "request_dispatch",
    "system_context": "deepagents_app",
    "tool_runtime_context": "frontend_dynamo",
    "runtime_preprocessing": "frontend_dynamo",
    "model_behavior": "deepagents_app",
}


def build_prompt_evolution_report(
    *,
    task: dict,
    workflow: dict,
    frontend_url: str,
    model: str,
    app_variant: str,
    runtime_log_artifacts: dict[str, Any],
    workspace_metadata: dict[str, Any],
    workspace_artifacts: dict[str, Any],
) -> dict[str, Any]:
    baseline_result = workflow["result"]
    response = baseline_result.get("response")
    messages = _lineage_messages(response)
    system_prompt = load_agent_instructions(app_variant)
    tool_parser_usage = _extract_tool_parser_usage(
        runtime_log_artifacts.get("frontend_log_file")
        if isinstance(runtime_log_artifacts.get("frontend_log_file"), str)
        else None
    )
    observed_tool_call_names = sorted(
        {
            name
            for message in messages
            for name in message.get("tool_call_names", [])
            if isinstance(name, str) and name
        }
    )
    observed_tool_result_names = sorted(
        {
            message.get("name")
            for message in messages
            if message.get("type") == "tool" and isinstance(message.get("name"), str)
        }
    )
    measurement = baseline_result.get("measurement", {})
    request_context = measurement.get("request_context", {})
    baseline_hints = baseline_result.get("baseline_hints", {})
    prompt = workflow.get("prompt", "")
    validation_command = str(workflow.get("validation_command") or task.get("validation_command") or "")

    requirements_text = str(task.get("requirements") or "")
    selected_tests = task.get("selected_test_files_to_run")
    selected_tests_text = (
        ", ".join(selected_tests) if isinstance(selected_tests, list) else str(selected_tests or "")
    )
    expected_tools = [
        "write_todos",
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
        "task",
    ]
    observed_tool_call_count = sum(int(message.get("tool_call_count", 0)) for message in messages)
    response_text = baseline_result.get("response_text", "")
    problem_statement_text = str(task.get("problem_statement") or "")
    task_input_chars = len(problem_statement_text)
    formatted_prompt_chars = len(prompt)
    system_prompt_chars = len(system_prompt)
    response_chars = len(response_text)
    parser_names_text = ", ".join(tool_parser_usage["tool_parser_names_seen"]) or "-"
    tools_used_text = ", ".join(observed_tool_call_names) or "-"
    workspace_changed = bool(workspace_artifacts.get("patch_nonempty"))

    return {
        "stages": [
            {
                "stage": "task_input",
                "component": PROMPT_EVOLUTION_STAGE_COMPONENTS["task_input"],
                "question_answered": "what task did we start with?",
                "changed_from": "-",
                "change_summary": "Loaded the raw SWE-bench task payload with repo metadata, bug description, requirements, and test targets.",
                "delta_summary": "Established the starting task description from dataset fields before any prompt assembly.",
                "result_summary": (
                    f"repo={task.get('repo')} | base_commit={task.get('base_commit')} | "
                    f"tests={selected_tests_text or '-'} | validation={validation_command or '-'} | "
                    f"workspace={workspace_metadata.get('workspace_path') or '-'}"
                ),
                "prompt_preview": _prompt_preview(problem_statement_text),
                "prompt_chars": task_input_chars,
                "major_additions": "Task metadata, problem statement, requirements, selected tests, validation command, workspace path.",
                "added_elements": "repo metadata, problem statement, requirements, selected tests, validation command, workspace path",
                "removed_elements": "none",
                "unchanged_core": "raw bug description and acceptance criteria are the source of truth",
                "key_facts": (
                    f"repo={task.get('repo')} | base_commit={task.get('base_commit')} | "
                    f"tests={selected_tests_text or '-'} | validation={validation_command or '-'} | "
                    f"workspace={workspace_metadata.get('workspace_path') or '-'}"
                ),
                "structure_before": "none",
                "structure_after": "task payload with repo, base_commit, problem_statement, requirements, selected tests, validation command, workspace path",
                "keys_before": "none",
                "keys_after": "repo, base_commit, problem_statement, requirements, selected_test_files_to_run, validation_command, workspace_path",
                "json_keys_before": "none",
                "json_keys_after": '{"repo":"...","base_commit":"...","problem_statement":"...","requirements":"...","selected_test_files_to_run":["..."],"validation_command":"...","workspace_path":"..."}',
                "added_keys": "repo, base_commit, problem_statement, requirements, selected_test_files_to_run, validation_command, workspace_path",
                "removed_keys": "none",
                "changed_keys": "none",
                "chars_before": 0,
                "chars_after": task_input_chars,
                "char_delta": task_input_chars,
            },
            {
                "stage": "formatted_prompt",
                "component": PROMPT_EVOLUTION_STAGE_COMPONENTS["formatted_prompt"],
                "question_answered": "what exact prompt did we build?",
                "changed_from": "task_input",
                "change_summary": (
                    "Merged the task fields into one action-oriented user prompt and added the exact validation command, workspace instructions, and execution expectations."
                ),
                "delta_summary": "Turned scattered task fields into one runnable user prompt with explicit instructions to inspect, edit, validate with the proper test runner, and report real changes.",
                "result_summary": (
                    f"user_prompt_lines={len(prompt.splitlines())} | user_prompt_chars={len(prompt)} | "
                    f"validation={validation_command or '-'}"
                ),
                "prompt_preview": _prompt_preview(prompt),
                "prompt_chars": formatted_prompt_chars,
                "major_additions": (
                    "Combined repo metadata, bug description, requirements, interface notes, selected tests, validation command, workspace instructions, and expectations."
                ),
                "added_elements": "workspace instructions, interface notes, execution expectations, selected test block, validation command",
                "removed_elements": "none",
                "unchanged_core": "problem statement and requirements remained intact inside the merged prompt",
                "key_facts": (
                    f"prompt_lines={len(prompt.splitlines())} | prompt_chars={formatted_prompt_chars} | "
                    f"validation={validation_command or '-'}"
                ),
                "structure_before": "task payload fields spread across dataset columns",
                "structure_after": "single formatted prompt string",
                "keys_before": "repo, base_commit, problem_statement, requirements, selected_test_files_to_run, validation_command, workspace_path",
                "keys_after": "prompt, validation_command",
                "json_keys_before": '{"repo":"...","base_commit":"...","problem_statement":"...","requirements":"...","selected_test_files_to_run":["..."],"validation_command":"...","workspace_path":"..."}',
                "json_keys_after": '{"prompt":"...","validation_command":"..."}',
                "added_keys": "prompt, validation_command",
                "removed_keys": "none",
                "changed_keys": "problem_statement, requirements, selected tests -> prompt text",
                "chars_before": task_input_chars,
                "chars_after": formatted_prompt_chars,
                "char_delta": formatted_prompt_chars - task_input_chars,
                "full_text": prompt,
                "validation_command": validation_command,
            },
            {
                "stage": "final_model_request",
                "component": PROMPT_EVOLUTION_STAGE_COMPONENTS["final_model_request"],
                "question_answered": "what exact request shape did we send?",
                "changed_from": "formatted_prompt",
                "change_summary": (
                    "Wrapped the formatted prompt as the initial user message, selected the model endpoint, and attached request context plus agent hints."
                ),
                "delta_summary": "Converted the plain prompt into an OpenAI-style request envelope with one user message plus request metadata for routing and analysis.",
                "result_summary": (
                    f"model={model} | frontend={frontend_url} | tool_choice=auto | "
                    f"request_id={request_context.get('request_id') or '-'}"
                ),
                "prompt_preview": _prompt_preview(prompt),
                "prompt_chars": formatted_prompt_chars,
                "major_additions": "Initial chat message envelope, request context ids, Dynamo hints, model selection.",
                "added_elements": "initial user message envelope, request_context, agent_hints, model selection, tool_choice=auto",
                "removed_elements": "none",
                "unchanged_core": "formatted user prompt text remained the core request content",
                "key_facts": (
                    f"model={model} | frontend={frontend_url} | tool_choice=auto | "
                    f"request_id={request_context.get('request_id') or '-'}"
                ),
                "structure_before": "plain formatted prompt string",
                "structure_after": "request envelope with model, messages, request_context, agent_hints, tool_choice",
                "keys_before": "prompt",
                "keys_after": "model, messages[].role, messages[].content, request_context.request_id, request_context.parent_run_id, request_context.task_instance_id, request_context.phase, request_context.app_variant, agent_hints.priority, agent_hints.reuse_likelihood, agent_hints.agent_phase, agent_hints.latency_sensitivity, agent_hints.program_id, agent_hints.context_type, agent_hints.expected_output_tokens, tool_choice",
                "json_keys_before": '{"prompt":"..."}',
                "json_keys_after": '{"model":"...","messages":[{"role":"...","content":"..."}],"request_context":{"request_id":"...","parent_run_id":"...","task_instance_id":"...","phase":"...","app_variant":"..."},"agent_hints":{"priority":"...","reuse_likelihood":"...","agent_phase":"...","latency_sensitivity":"...","program_id":"...","context_type":"...","expected_output_tokens":"..."},"tool_choice":"..."}',
                "added_keys": "model, messages, request_context, agent_hints, tool_choice",
                "removed_keys": "none",
                "changed_keys": "prompt -> messages[0].content",
                "chars_before": formatted_prompt_chars,
                "chars_after": formatted_prompt_chars,
                "char_delta": 0,
                "initial_messages": [{"role": "user", "content": prompt}],
                "request_context": request_context,
                "agent_hints": baseline_hints,
            },
            {
                "stage": "system_context",
                "component": PROMPT_EVOLUTION_STAGE_COMPONENTS["system_context"],
                "question_answered": "what exact request shape did we send?",
                "changed_from": "final_model_request",
                "change_summary": "Prepared the Deep Agents instruction layer that guides tool use and coding-agent behavior around the user message.",
                "delta_summary": "Introduced the system-level coding-agent instructions that shape how the model should behave, even if the full wrapped request is not persisted verbatim.",
                "result_summary": f"system_prompt_chars={system_prompt_chars} | runtime_source={workflow.get('deepagents_runtime_source')}",
                "prompt_preview": _prompt_preview(system_prompt),
                "prompt_chars": system_prompt_chars,
                "major_additions": "Deep Agents system prompt and app-specific coding agent behavior.",
                "added_elements": "system prompt, coding-agent behavior rules",
                "removed_elements": "none",
                "unchanged_core": "formatted user prompt remained the user-visible task content",
                "key_facts": (
                    f"system_prompt_chars={system_prompt_chars} | "
                    f"runtime_source={workflow.get('deepagents_runtime_source')}"
                ),
                "structure_before": "request envelope centered on one user message",
                "structure_after": "request envelope plus system prompt and Deep Agents behavior layer",
                "keys_before": "model, messages[].role, messages[].content, request_context.*, agent_hints.*, tool_choice",
                "keys_after": "model, system_prompt, messages[].role, messages[].content, request_context.*, agent_hints.*, tool_choice",
                "json_keys_before": '{"model":"...","messages":[{"role":"...","content":"..."}],"request_context":{...},"agent_hints":{...},"tool_choice":"..."}',
                "json_keys_after": '{"model":"...","system_prompt":"...","messages":[{"role":"...","content":"..."}],"request_context":{...},"agent_hints":{...},"tool_choice":"..."}',
                "added_keys": "system_prompt",
                "removed_keys": "none",
                "changed_keys": "request interpretation now includes system instructions",
                "chars_before": formatted_prompt_chars,
                "chars_after": formatted_prompt_chars + system_prompt_chars,
                "char_delta": system_prompt_chars,
                "system_prompt": system_prompt,
            },
            {
                "stage": "tool_runtime_context",
                "component": PROMPT_EVOLUTION_STAGE_COMPONENTS["tool_runtime_context"],
                "question_answered": "what tools were available?",
                "changed_from": "system_context",
                "change_summary": (
                    "The runtime attached the tool-capable surface and frontend parsing behavior before inference."
                ),
                "delta_summary": "Made the request tool-capable by exposing built-in tools and confirming which tool parser the frontend actually used.",
                "result_summary": (
                    f"expected_tools={', '.join(expected_tools)} | parser={parser_names_text} | "
                    f"prompt_tokens={measurement.get('prompt_tokens') or '-'} | cached_prompt_tokens={measurement.get('cached_prompt_tokens') or '-'}"
                ),
                "prompt_preview": _prompt_preview(prompt),
                "prompt_chars": formatted_prompt_chars,
                "major_additions": "Built-in tool surface, tool parser selection, tokenizer work, and prompt-cache context.",
                "added_elements": "built-in tool surface, tool parser, prompt tokenization, prompt caching context",
                "removed_elements": "none",
                "unchanged_core": "same user prompt content, now made tool-capable",
                "key_facts": (
                    f"expected_tools={', '.join(expected_tools)} | parser={parser_names_text} | "
                    f"prompt_tokens={measurement.get('prompt_tokens') or '-'} | "
                    f"cached_prompt_tokens={measurement.get('cached_prompt_tokens') or '-'}"
                ),
                "structure_before": "request envelope plus system prompt",
                "structure_after": "tool-capable request with expected tools and parser context",
                "keys_before": "model, system_prompt, messages[].role, messages[].content, request_context.*, agent_hints.*, tool_choice",
                "keys_after": "model, system_prompt, messages[].role, messages[].content, request_context.*, agent_hints.*, tool_choice, expected_builtin_tools[], tool_parser_names_seen[], tool_parser_observed",
                "json_keys_before": '{"model":"...","system_prompt":"...","messages":[{"role":"...","content":"..."}],"request_context":{...},"agent_hints":{...},"tool_choice":"..."}',
                "json_keys_after": '{"model":"...","system_prompt":"...","messages":[{"role":"...","content":"..."}],"request_context":{...},"agent_hints":{...},"tool_choice":"...","expected_builtin_tools":["..."],"tool_parser_names_seen":["..."],"tool_parser_observed":"..."}',
                "added_keys": "expected_builtin_tools, tool_parser_names_seen, tool_parser_observed",
                "removed_keys": "none",
                "changed_keys": "runtime view now includes tool surface and parser metadata",
                "chars_before": formatted_prompt_chars + system_prompt_chars,
                "chars_after": formatted_prompt_chars + system_prompt_chars,
                "char_delta": 0,
                "expected_builtin_tools": expected_tools,
                "tool_parser_names_seen": tool_parser_usage["tool_parser_names_seen"],
                "tool_parser_observed": tool_parser_usage["tool_parser_observed"],
            },
            {
                "stage": "runtime_preprocessing",
                "component": PROMPT_EVOLUTION_STAGE_COMPONENTS["runtime_preprocessing"],
                "question_answered": "what parser/runtime behavior was actually active?",
                "changed_from": "tool_runtime_context",
                "change_summary": (
                    "Captured what the frontend/runtime actually applied before the worker generated tokens."
                ),
                "delta_summary": "Recorded parser activation, prompt token counts, and cache signals that describe how the request was prepared for SGLang execution.",
                "result_summary": (
                    f"parser_observed={tool_parser_usage['tool_parser_observed']} | prompt_tokens={measurement.get('prompt_tokens') or '-'} | "
                    f"cached_input_tokens={measurement.get('cached_input_tokens') or '-'}"
                ),
                "prompt_preview": _prompt_preview(prompt),
                "prompt_chars": formatted_prompt_chars,
                "major_additions": "Observed parser status, prompt tokens, and cached input token counts from runtime evidence.",
                "added_elements": "parser observation, prompt token count, cached input token count",
                "removed_elements": "none",
                "unchanged_core": "request content stayed the same; this stage only reports runtime preparation evidence",
                "key_facts": (
                    f"parser_observed={tool_parser_usage['tool_parser_observed']} | "
                    f"prompt_tokens={measurement.get('prompt_tokens') or '-'} | "
                    f"cached_input_tokens={measurement.get('cached_input_tokens') or '-'}"
                ),
                "structure_before": "tool-capable request with parser metadata",
                "structure_after": "runtime-prepared request with token and cache measurements",
                "keys_before": "model, system_prompt, messages[].role, messages[].content, request_context.*, agent_hints.*, tool_choice, expected_builtin_tools[], tool_parser_names_seen[], tool_parser_observed",
                "keys_after": "model, system_prompt, messages[].role, messages[].content, request_context.*, agent_hints.*, tool_choice, expected_builtin_tools[], tool_parser_names_seen[], tool_parser_observed, prompt_tokens, cached_prompt_tokens, cached_input_tokens",
                "json_keys_before": '{"model":"...","system_prompt":"...","messages":[{"role":"...","content":"..."}],"request_context":{...},"agent_hints":{...},"tool_choice":"...","expected_builtin_tools":["..."],"tool_parser_names_seen":["..."],"tool_parser_observed":"..."}',
                "json_keys_after": '{"model":"...","system_prompt":"...","messages":[{"role":"...","content":"..."}],"request_context":{...},"agent_hints":{...},"tool_choice":"...","expected_builtin_tools":["..."],"tool_parser_names_seen":["..."],"tool_parser_observed":"...","prompt_tokens":"...","cached_prompt_tokens":"...","cached_input_tokens":"..."}',
                "added_keys": "prompt_tokens, cached_prompt_tokens, cached_input_tokens",
                "removed_keys": "none",
                "changed_keys": "request now carries observed runtime preprocessing metrics",
                "chars_before": formatted_prompt_chars + system_prompt_chars,
                "chars_after": formatted_prompt_chars + system_prompt_chars,
                "char_delta": 0,
            },
            {
                "stage": "model_behavior",
                "component": PROMPT_EVOLUTION_STAGE_COMPONENTS["model_behavior"],
                "question_answered": "what did the model actually do?",
                "changed_from": "runtime_preprocessing",
                "change_summary": (
                    "Captured the model transcript, observed tool calls, and recorded whether the run actually changed the workspace."
                ),
                "delta_summary": "Observed the model’s actual behavior after execution, including tool use, finish reason, and whether any workspace edits were produced.",
                "result_summary": (
                    f"observed_tool_calls={observed_tool_call_count} | tools_used={tools_used_text} | "
                    f"workspace_changed={workspace_changed}"
                ),
                "prompt_preview": _prompt_preview(response_text),
                "prompt_chars": response_chars,
                "major_additions": "Model transcript, tool-call outcomes, finish reason, and workspace-change status.",
                "added_elements": "tool transcript, finish reason, response text, workspace change status",
                "removed_elements": "none",
                "unchanged_core": "the run still targets the same task, now with concrete behavior outcome attached",
                "key_facts": (
                    f"observed_tool_calls={observed_tool_call_count} | tools_used={tools_used_text} | "
                    f"finish_reason={measurement.get('finish_reason') or '-'} | workspace_changed={workspace_changed}"
                ),
                "structure_before": "runtime-prepared request state",
                "structure_after": "response/transcript with tool calls, tool results, finish reason, workspace outcome",
                "keys_before": "model, system_prompt, messages[].role, messages[].content, request_context.*, agent_hints.*, tool_choice, expected_builtin_tools[], tool_parser_names_seen[], tool_parser_observed, prompt_tokens, cached_prompt_tokens, cached_input_tokens",
                "keys_after": "messages[].type, messages[].name, messages[].content, messages[].tool_calls[].name, messages[].invalid_tool_calls[], observed_tool_call_names[], observed_tool_result_names[], observed_tool_call_count, finish_reason, response_text, workspace_changed",
                "json_keys_before": '{"model":"...","system_prompt":"...","messages":[{"role":"...","content":"..."}],"request_context":{...},"agent_hints":{...},"tool_choice":"...","expected_builtin_tools":["..."],"tool_parser_names_seen":["..."],"tool_parser_observed":"...","prompt_tokens":"...","cached_prompt_tokens":"...","cached_input_tokens":"..."}',
                "json_keys_after": '{"messages":[{"type":"...","name":"...","content":"...","tool_calls":[{"name":"..."}],"invalid_tool_calls":["..."]}],"observed_tool_call_names":["..."],"observed_tool_result_names":["..."],"observed_tool_call_count":"...","finish_reason":"...","response_text":"...","workspace_changed":"..."}',
                "added_keys": "observed_tool_call_names, observed_tool_result_names, finish_reason, response_text, workspace_changed",
                "removed_keys": "none",
                "changed_keys": "request state -> response and outcome state",
                "chars_before": formatted_prompt_chars + system_prompt_chars,
                "chars_after": response_chars,
                "char_delta": response_chars - (formatted_prompt_chars + system_prompt_chars),
                "observed_tool_call_names": observed_tool_call_names,
                "observed_tool_result_names": observed_tool_result_names,
                "observed_tool_call_count": observed_tool_call_count,
                "finish_reason": measurement.get("finish_reason"),
                "response_text": response_text,
            },
        ],
        "supporting_data": {
            "system_prompt_preview": _prompt_preview(system_prompt),
            "system_prompt_chars": len(system_prompt),
            "requirements_preview": _prompt_preview(requirements_text),
            "selected_tests": selected_tests_text,
            "validation_command": validation_command,
            "provider_response_id": measurement.get("provider_response_id"),
            "latency_ms": measurement.get("latency_ms"),
            "input_tokens": measurement.get("input_tokens"),
            "output_tokens": measurement.get("output_tokens"),
            "cached_input_tokens": measurement.get("cached_input_tokens"),
            "workspace_patch_nonempty": workspace_artifacts.get("patch_nonempty"),
            "git_status_nonempty": bool(str(workspace_artifacts.get("git_status") or "").strip()),
            "git_diff_stat_nonempty": bool(str(workspace_artifacts.get("git_diff_stat") or "").strip()),
            "message_count": len(messages),
            "tools_used": tools_used_text,
            "observed_tool_call_count": observed_tool_call_count,
        },
    }


def truncate_json_value_strings(value: Any, *, char_limit: int) -> Any:
    if char_limit <= 0:
        return value
    if isinstance(value, str):
        if len(value) <= char_limit:
            return value
        return value[: max(0, char_limit - 3)] + "..."
    if isinstance(value, list):
        return [truncate_json_value_strings(item, char_limit=char_limit) for item in value]
    if isinstance(value, dict):
        return {
            str(key): truncate_json_value_strings(item, char_limit=char_limit)
            for key, item in value.items()
        }
    return value


def prompt_evolution_value_stage_objects(
    *,
    task: dict,
    workflow: dict,
    frontend_url: str,
    model: str,
    app_variant: str,
    runtime_log_artifacts: dict[str, Any],
    workspace_metadata: dict[str, Any],
    workspace_artifacts: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline_result = workflow["result"]
    response = baseline_result.get("response")
    messages = _lineage_messages(response)
    system_prompt = load_agent_instructions(app_variant)
    tool_parser_usage = _extract_tool_parser_usage(
        runtime_log_artifacts.get("frontend_log_file")
        if isinstance(runtime_log_artifacts.get("frontend_log_file"), str)
        else None
    )
    observed_tool_call_names = sorted(
        {
            name
            for message in messages
            for name in message.get("tool_call_names", [])
            if isinstance(name, str) and name
        }
    )
    observed_tool_result_names = sorted(
        {
            message.get("name")
            for message in messages
            if message.get("type") == "tool" and isinstance(message.get("name"), str)
        }
    )
    observed_tool_call_count = sum(int(message.get("tool_call_count", 0)) for message in messages)
    measurement = baseline_result.get("measurement", {})
    request_context = measurement.get("request_context", {})
    baseline_hints = baseline_result.get("baseline_hints", {})
    prompt = workflow.get("prompt", "")
    validation_command = str(workflow.get("validation_command") or task.get("validation_command") or "")
    response_text = baseline_result.get("response_text", "")
    expected_tools = [
        "write_todos",
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
        "task",
    ]

    task_payload = {
        "repo": task.get("repo"),
        "base_commit": task.get("base_commit"),
        "problem_statement": task.get("problem_statement"),
        "requirements": task.get("requirements"),
        "selected_test_files_to_run": task.get("selected_test_files_to_run"),
        "validation_command": validation_command,
        "workspace_path": workspace_metadata.get("workspace_path"),
    }
    formatted_prompt = {"prompt": prompt, "validation_command": validation_command}
    final_model_request = {
        "model": model,
        "frontend_url": frontend_url,
        "messages": [{"role": "user", "content": prompt}],
        "request_context": request_context,
        "agent_hints": baseline_hints,
        "tool_choice": "auto",
    }
    system_context = {
        **final_model_request,
        "system_prompt": system_prompt,
    }
    tool_runtime_context = {
        **system_context,
        "expected_builtin_tools": expected_tools,
        "tool_parser_names_seen": tool_parser_usage["tool_parser_names_seen"],
        "tool_parser_observed": tool_parser_usage["tool_parser_observed"],
    }
    runtime_preprocessing = {
        **tool_runtime_context,
        "prompt_tokens": measurement.get("prompt_tokens"),
        "cached_prompt_tokens": measurement.get("cached_prompt_tokens"),
        "cached_input_tokens": measurement.get("cached_input_tokens"),
        "provider_response_id": measurement.get("provider_response_id"),
    }
    model_behavior = {
        "messages": messages,
        "observed_tool_call_names": observed_tool_call_names,
        "observed_tool_result_names": observed_tool_result_names,
        "observed_tool_call_count": observed_tool_call_count,
        "finish_reason": measurement.get("finish_reason"),
        "response_text": response_text,
        "workspace_changed": bool(workspace_artifacts.get("patch_nonempty")),
    }

    return [
        {"stage": "task_input", "before": None, "after": task_payload},
        {"stage": "formatted_prompt", "before": task_payload, "after": formatted_prompt},
        {"stage": "final_model_request", "before": formatted_prompt, "after": final_model_request},
        {"stage": "system_context", "before": final_model_request, "after": system_context},
        {"stage": "tool_runtime_context", "before": system_context, "after": tool_runtime_context},
        {"stage": "runtime_preprocessing", "before": tool_runtime_context, "after": runtime_preprocessing},
        {"stage": "model_behavior", "before": runtime_preprocessing, "after": model_behavior},
    ]


def write_prompt_evolution_stage_value_reports(
    *,
    run_dir: Path,
    prompt_evolution_report: dict[str, Any],
    task: dict,
    workflow: dict,
    frontend_url: str,
    model: str,
    app_variant: str,
    runtime_log_artifacts: dict[str, Any],
    workspace_metadata: dict[str, Any],
    workspace_artifacts: dict[str, Any],
    value_char_limit: int,
) -> dict[str, Any]:
    value_dir = run_dir / "prompt_evolution_values"
    value_dir.mkdir(parents=True, exist_ok=True)
    report_stages = {
        str(stage.get("stage")): stage
        for stage in prompt_evolution_report.get("stages", [])
        if stage.get("stage")
    }
    value_stages = prompt_evolution_value_stage_objects(
        task=task,
        workflow=workflow,
        frontend_url=frontend_url,
        model=model,
        app_variant=app_variant,
        runtime_log_artifacts=runtime_log_artifacts,
        workspace_metadata=workspace_metadata,
        workspace_artifacts=workspace_artifacts,
    )
    stage_files: list[dict[str, Any]] = []
    for index, value_stage in enumerate(value_stages, start=1):
        stage_name = str(value_stage["stage"])
        stage = report_stages.get(stage_name, {})
        before = value_stage.get("before")
        after = value_stage.get("after")
        body = {
            "stage": stage_name,
            "diff_summary": {
                "change_summary": stage.get("change_summary"),
                "delta_summary": stage.get("delta_summary"),
                "added_keys": stage.get("added_keys"),
                "removed_keys": stage.get("removed_keys"),
                "changed_keys": stage.get("changed_keys"),
            },
            "before": truncate_json_value_strings(before, char_limit=value_char_limit),
            "after": truncate_json_value_strings(after, char_limit=value_char_limit),
        }
        filename = f"{index:02d}_{stage_name}.json"
        path = value_dir / filename
        path.write_text(json.dumps(body, indent=2, ensure_ascii=False, default=stringify_unknown), encoding="utf-8")
        stage_files.append(
            {
                "stage": stage_name,
                "filename": filename,
                "path": str(path),
            }
        )

    index_body = {
        "run_id": run_dir.name,
        "char_limit": value_char_limit,
        "stages": [
            {
                "stage": stage_file["stage"],
                "file": stage_file["filename"],
            }
            for stage_file in stage_files
        ],
    }
    index_path = value_dir / "index.json"
    index_path.write_text(json.dumps(index_body, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "directory": str(value_dir),
        "index_file": str(index_path),
        "stage_files": stage_files,
    }


def render_prompt_evolution_markdown(report: dict) -> str:
    lines = ["# Prompt Evolution Report", ""]
    lines.extend(
        [
            "| Stage | Owned by | Answers | Came from | What changed | Key additions | Structure changes | Outcome |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for stage in report.get("stages", []):
        lines.append(
            "| {stage_name} | {component} | {question} | {changed_from} | {what_changed} | {key_additions} | {structure_changes} | {outcome} |".format(
                stage_name=markdown_value(stage.get("stage")),
                component=markdown_value(stage.get("component")),
                question=markdown_value(stage.get("question_answered")),
                changed_from=markdown_value(stage.get("changed_from")),
                what_changed=markdown_value(stage.get("delta_summary")),
                key_additions=markdown_value(stage.get("added_elements")),
                structure_changes=markdown_value(
                    f"before={stage.get('structure_before')} | after={stage.get('structure_after')}"
                ),
                outcome=markdown_value(stage.get("result_summary")),
            )
        )

    for stage in report.get("stages", []):
        lines.extend(["", f"## {str(stage.get('stage') or '').replace('_', ' ').title()}"])
        lines.extend(
            markdown_field_table(
                {
                    "owned_by": stage.get("component"),
                    "answers": stage.get("question_answered"),
                    "came_from": stage.get("changed_from"),
                    "what_changed": stage.get("change_summary"),
                    "delta": stage.get("delta_summary"),
                    "major_additions": stage.get("major_additions"),
                    "key_additions": stage.get("added_elements"),
                    "removed_items": stage.get("removed_elements"),
                    "what_stayed_same": stage.get("unchanged_core"),
                    "outcome": stage.get("result_summary"),
                    "key_facts": stage.get("key_facts"),
                    "structure_before": stage.get("structure_before"),
                    "structure_after": stage.get("structure_after"),
                    "keys_before": stage.get("keys_before"),
                    "keys_after": stage.get("keys_after"),
                    "json_keys_before": stage.get("json_keys_before"),
                    "json_keys_after": stage.get("json_keys_after"),
                    "added_keys": stage.get("added_keys"),
                    "removed_keys": stage.get("removed_keys"),
                    "changed_keys": stage.get("changed_keys"),
                    "size_before": stage.get("chars_before"),
                    "size_after": stage.get("chars_after"),
                    "size_change": stage.get("char_delta"),
                    "prompt_size": stage.get("prompt_chars"),
                },
                "prompt_evolution_report",
                [
                    ("owned_by", "Owned by"),
                    ("answers", "Answers"),
                    ("came_from", "Came from"),
                    ("what_changed", "What changed"),
                    ("delta", "Delta"),
                    ("major_additions", "Major additions"),
                    ("key_additions", "Key additions"),
                    ("removed_items", "Removed items"),
                    ("what_stayed_same", "What stayed the same"),
                    ("outcome", "Outcome"),
                    ("key_facts", "Key facts"),
                    ("structure_before", "Structure before"),
                    ("structure_after", "Structure after"),
                    ("keys_before", "Keys before"),
                    ("keys_after", "Keys after"),
                    ("json_keys_before", "JSON keys before"),
                    ("json_keys_after", "JSON keys after"),
                    ("added_keys", "Added keys"),
                    ("removed_keys", "Removed keys"),
                    ("changed_keys", "Changed keys"),
                    ("size_before", "Size before"),
                    ("size_after", "Size after"),
                    ("size_change", "Size change"),
                    ("prompt_size", "Prompt size"),
                ],
                include_provenance=False,
            )
        )
        if stage.get("stage") == "formatted_prompt":
            lines.extend(["", "### Full Formatted Prompt", "```text", stage.get("full_text", ""), "```"])
        elif stage.get("stage") == "final_model_request":
            lines.extend(
                [
                    "",
                    "### Initial Messages",
                    "```json",
                    json.dumps(stage.get("initial_messages", []), indent=2, default=stringify_unknown),
                    "```",
                    "",
                    "### Request Context",
                    "```json",
                    json.dumps(stage.get("request_context", {}), indent=2, default=stringify_unknown),
                    "```",
                    "",
                    "### Agent Hints",
                    "```json",
                    json.dumps(stage.get("agent_hints", {}), indent=2, default=stringify_unknown),
                    "```",
                ]
            )
        elif stage.get("stage") == "model_behavior":
            lines.extend(["", "### Final Response Text", "```text", stage.get("response_text", ""), "```"])

    lines.extend(["", "## Supporting Data"])
    lines.extend(
        markdown_field_table(
            report.get("supporting_data", {}),
            "prompt_evolution_report",
            [(field, field.replace("_", " ").title()) for field in report.get("supporting_data", {}).keys()],
            include_provenance=False,
        )
    )
    return "\n".join(lines) + "\n"


def build_prompt_evolution_csv_rows(report: dict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage in report.get("stages", []):
        rows.append(
            {
                "stage": stage.get("stage"),
                "owned_by": stage.get("component"),
                "answers": stage.get("question_answered"),
                "came_from": stage.get("changed_from"),
                "what_changed": stage.get("delta_summary"),
                "key_additions": stage.get("added_elements"),
                "what_stayed_same": stage.get("unchanged_core"),
                "key_facts": stage.get("key_facts"),
                "structure_before": stage.get("structure_before"),
                "structure_after": stage.get("structure_after"),
                "keys_before": stage.get("keys_before"),
                "keys_after": stage.get("keys_after"),
                "json_keys_before": stage.get("json_keys_before"),
                "json_keys_after": stage.get("json_keys_after"),
                "added_keys": stage.get("added_keys"),
                "removed_keys": stage.get("removed_keys"),
                "changed_keys": stage.get("changed_keys"),
                "outcome": stage.get("result_summary"),
                "size_change": stage.get("char_delta"),
            }
        )
    return rows


def write_excel_workbook(run_dir: Path, workbook_name: str, sheet_rows: dict[str, list[dict]]) -> Path:
    output_path = run_dir / workbook_name
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, rows in sheet_rows.items():
            sanitized_name = sheet_name[:31]
            pd.DataFrame(rows).to_excel(writer, sheet_name=sanitized_name, index=False)
    return output_path


def log_artifact_written_event(*, artifact_name: str, artifact_path: Path, related_phase: str | None = None) -> None:
    size_bytes = artifact_path.stat().st_size if artifact_path.exists() else None
    log_lifecycle_event(
        stage="artifact_written",
        payload={
            "event_kind": "artifact",
            "phase": related_phase,
            "artifact_name": artifact_name,
            "artifact_path": str(artifact_path),
            "artifact_format": artifact_path.suffix.lstrip("."),
            "artifact_size_bytes": size_bytes,
        },
    )


def task_source_label(
    *,
    dataset_name: str | None,
    split: str,
    csv_path: str | None,
    json_path: str | None,
) -> str:
    if json_path:
        return f"json:{json_path}"
    if csv_path:
        return f"csv:{csv_path}"
    return f"dataset:{dataset_name}:{split}"


def run_command(command: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    # Debugging note: every git/process hook in the wrapper flows through here.
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            check=check,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        program = command[0] if command else "command"
        raise SystemExit(
            f"Required executable not found: {program}. "
            "Install it first, or disable automatic SWE-bench repo checkout with "
            "--no-auto-repo-checkout if you only want dataset-backed task text."
        ) from exc


def git_checkout_with_fetch_repair(repo_dir: Path, checkout_commit: str) -> dict[str, object]:
    """Checkout a commit, fetching the missing object once if the local cache is stale."""
    attempts: list[dict[str, object]] = []

    def record(name: str, result: subprocess.CompletedProcess) -> None:
        attempts.append(
            {
                "name": name,
                "command": " ".join(result.args if isinstance(result.args, list) else [str(result.args)]),
                "returncode": result.returncode,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:],
            }
        )

    checkout = run_command(["git", "checkout", "--detach", checkout_commit], cwd=repo_dir, check=False)
    record("checkout_initial", checkout)
    if checkout.returncode == 0:
        return {"checked_out": True, "repair_needed": False, "attempts": attempts}

    fetch_all = run_command(["git", "fetch", "--all", "--tags", "--prune"], cwd=repo_dir, check=False)
    record("fetch_all_tags_prune", fetch_all)

    fetch_commit = run_command(["git", "fetch", "origin", checkout_commit], cwd=repo_dir, check=False)
    record("fetch_origin_commit", fetch_commit)

    object_check = run_command(["git", "cat-file", "-e", f"{checkout_commit}^{{commit}}"], cwd=repo_dir, check=False)
    record("cat_file_commit", object_check)

    checkout_retry = run_command(["git", "checkout", "--detach", checkout_commit], cwd=repo_dir, check=False)
    record("checkout_retry", checkout_retry)
    if checkout_retry.returncode == 0:
        return {"checked_out": True, "repair_needed": True, "attempts": attempts}

    details = "\n".join(
        (
            f"- {attempt['name']} rc={attempt['returncode']}\n"
            f"  command: {attempt['command']}\n"
            f"  stderr: {str(attempt['stderr']).strip() or '<empty>'}"
        )
        for attempt in attempts
    )
    raise SystemExit(
        "Unable to checkout the SWE-bench base commit after fetch repair.\n"
        f"repo_dir: {repo_dir}\n"
        f"checkout_commit: {checkout_commit}\n"
        f"{details}\n"
        "If this persists, remove the stale shared repo cache for this repository under "
        f"{REPOS_DIR} and rerun the same PROMPT_EVOLUTION_BATCH_ID to resume."
    )


def infer_swebench_repo_url(task: dict) -> str | None:
    # Debugging note: this is the SWE-bench -> GitHub adaptation hook.
    # It teaches the wrapper how to turn dataset repo metadata into a cloneable URL.
    repo = str(task.get("repo") or "").strip()
    if not repo or "/" not in repo or " " in repo:
        return None
    if repo.startswith(("http://", "https://")):
        return repo
    return f"https://github.com/{repo}.git"


def infer_swebench_base_commit(task: dict) -> str | None:
    for key in ("base_commit", "commit", "revision", "sha"):
        value = str(task.get(key) or "").strip()
        if value:
            return value
    return None


def repo_cache_dir_name(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    repo_path = parsed.path.strip("/")
    if repo_path.endswith(".git"):
        repo_path = repo_path[:-4]
    return repo_path.replace("/", "__") or "repo"


def ensure_shared_repo_checkout(repo_url: str) -> Path:
    # Debugging note: this is the shared single-GPU repo cache under agentbench/repos/.
    # Automatic SWE-bench runs reuse this checkout instead of inventing a new repo path each time.
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    shared_repo_dir = REPOS_DIR / repo_cache_dir_name(repo_url)
    if not shared_repo_dir.exists():
        run_command(["git", "clone", repo_url, str(shared_repo_dir)])
        return shared_repo_dir

    git_dir = shared_repo_dir / ".git"
    if not git_dir.exists():
        raise SystemExit(
            f"Shared repo path exists but is not a git checkout: {shared_repo_dir}"
        )

    run_command(["git", "fetch", "--all", "--tags"], cwd=shared_repo_dir)
    return shared_repo_dir


def clean_git_checkout(repo_dir: Path) -> dict[str, object]:
    """Reset tracked changes and remove untracked non-ignored files."""
    before = run_command(["git", "status", "--short"], cwd=repo_dir, check=False)
    reset = run_command(["git", "reset", "--hard"], cwd=repo_dir, check=False)
    clean = run_command(["git", "clean", "-fd"], cwd=repo_dir, check=False)
    after = run_command(["git", "status", "--short"], cwd=repo_dir, check=False)
    return {
        "cleaned": True,
        "status_before": before.stdout,
        "status_after": after.stdout,
        "reset_exit_code": reset.returncode,
        "clean_exit_code": clean.returncode,
        "clean_stdout": clean.stdout,
        "clean_stderr": clean.stderr,
    }


def should_auto_materialize_swebench_repo(
    *,
    dataset_name: str | None,
    csv_path: str | None,
    json_path: str | None,
) -> bool:
    if csv_path or json_path or not dataset_name:
        return False
    return "swe-bench" in dataset_name.lower()


def load_swebench_task(
    *,
    dataset_name: str | None,
    split: str,
    csv_path: str | None,
    json_path: str | None,
    index: int,
    instance_id: str | None,
) -> dict:
    # [CHECK_POINT 1] One SWE-bench Pro task enters the agent harness here.
    # Debugging note: this wrapper can load one task from three sources:
    # Hugging Face SWE-bench, CSV, or local JSON.
    if json_path:
        return json.loads(Path(json_path).read_text(encoding="utf-8"))

    if csv_path:
        rows = pd.read_csv(csv_path)
        if instance_id:
            matched = rows[rows["instance_id"] == instance_id]
            if matched.empty:
                raise SystemExit(f"instance_id not found in CSV: {instance_id}")
            return matched.iloc[0].to_dict()
        if index < 0 or index >= len(rows):
            raise SystemExit(f"index out of range for CSV: {index}")
        return rows.iloc[index].to_dict()

    if not dataset_name:
        raise SystemExit("Either --dataset or --csv-path is required.")

    ds = load_dataset(dataset_name, split=split)
    if instance_id:
        matches = [row for row in ds if row.get("instance_id") == instance_id]
        if not matches:
            raise SystemExit(f"instance_id not found in dataset: {instance_id}")
        return dict(matches[0])
    if index < 0 or index >= len(ds):
        raise SystemExit(f"index out of range for dataset: {index}")
    return dict(ds[index])


def save_result(run_dir: Path, payload: dict, *, filename: str = "result.json") -> None:
    # Debugging note: this is the saved-artifacts hook for the benchmark wrapper.
    # The final run summary is always materialized as result.json here.
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / filename).write_text(
        json.dumps(payload, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )


def recursion_soft_stop_enabled() -> bool:
    return env_flag("AGENTBENCH_SOFT_STOP_RECURSION", default=False)


def is_recursion_limit_error(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}"
    return "GraphRecursionError" in text or "Recursion limit" in text or "recursion limit" in text


def phase_results_from_lifecycle_events(events: list[dict]) -> list[dict]:
    phase_results: list[dict] = []
    seen: set[tuple[str, str]] = set()
    response_by_key: dict[tuple[str, str], dict] = {}
    response_by_phase: dict[str, dict] = {}
    for event in events:
        if event.get("event_kind") != "response":
            continue
        phase = str(event.get("phase") or "unknown")
        request_context = event.get("request_context")
        request_id = ""
        if isinstance(request_context, dict):
            request_id = str(request_context.get("request_id") or "")
        if request_id:
            response_by_key[(phase, request_id)] = event
        response_by_phase[phase] = event
    for event in events:
        if event.get("event_kind") != "request_dispatch":
            continue
        phase = str(event.get("phase") or "unknown")
        prompt = str(event.get("prompt") or "")
        if not prompt.strip():
            continue
        request_context = event.get("request_context")
        if not isinstance(request_context, dict):
            request_context = {"phase": phase, "step_title": phase.replace("_", " ").title()}
        key = (phase, request_context.get("request_id") or prompt[:128])
        if key in seen:
            continue
        seen.add(key)
        response_event = response_by_key.get((phase, str(request_context.get("request_id") or ""))) or response_by_phase.get(phase, {})
        phase_results.append(
            {
                "phase": phase,
                "sequence_index": len(
                    [row for row in phase_results if row.get("phase") == phase]
                ),
                "hints": event.get("hints") if isinstance(event.get("hints"), dict) else {},
                "request_context": request_context,
                "prompt": prompt,
                "response_text": response_event.get("response_text", ""),
                "measurement": response_event.get("measurement", {}),
                "tool_progress": response_event.get("tool_progress", {}),
                "tool_call_details": [],
                "status": "recursion_soft_stop",
            }
        )
    if phase_results:
        return phase_results

    for event in events:
        if event.get("stage") != "task_prompt_built":
            continue
        prompt = str(event.get("prompt") or "")
        if not prompt.strip():
            continue
        phase_results.append(
            {
                "phase": "task_prompt",
                "sequence_index": 0,
                "hints": {},
                "request_context": {
                    "phase": "task_prompt",
                    "step_title": "Initial SWE-bench task prompt",
                },
                "prompt": prompt,
                "response_text": "",
                "measurement": {},
                "tool_progress": {},
                "tool_call_details": [],
                "status": "recursion_soft_stop",
            }
        )
        break
    return phase_results


def first_prompt_from_lifecycle_events(events: list[dict], phase_results: list[dict]) -> str:
    for event in events:
        if event.get("stage") == "task_prompt_built" and isinstance(event.get("prompt"), str):
            return str(event["prompt"])
    for phase_result in phase_results:
        prompt = phase_result.get("prompt")
        if isinstance(prompt, str) and prompt.strip():
            return prompt
    return ""


def write_recursion_soft_stop_result(
    *,
    run_started_at: datetime,
    parent_run_id: str,
    legacy_instance_slug: str,
    args: argparse.Namespace,
    task: dict,
    task_source: str,
    base_hints: dict,
    auto_repo_checkout: dict,
    workspace_metadata: dict,
    checkpoint_log_path: Path,
    lifecycle_log_path: Path,
    others_dir: Path,
    exc: BaseException,
) -> None:
    raw_lifecycle_events = load_logged_events(lifecycle_log_path)
    phase_results = phase_results_from_lifecycle_events(raw_lifecycle_events)
    prompt = first_prompt_from_lifecycle_events(raw_lifecycle_events, phase_results)
    soft_stop = {
        "status": "recursion_soft_stop",
        "reason": "deepagents_recursion_limit",
        "exception_type": type(exc).__name__,
        "exception": str(exc),
        "message": (
            "Deep Agents reached the LangGraph recursion limit. The task was "
            "stopped after preserving any phase prompts already dispatched."
        ),
        "phase_prompt_count": len(phase_results),
    }
    result = {
        "status": "recursion_soft_stop",
        "response_text": "",
        "phase_results": phase_results,
        "soft_stop": soft_stop,
    }
    payload = {
        "run_started_at": run_started_at.isoformat(),
        "parent_run_id": parent_run_id,
        "legacy_instance_slug": legacy_instance_slug,
        "frontend_url": args.frontend_url,
        "model": args.model,
        "hint_profile": args.hint_profile,
        "hint_provider": args.hint_provider,
        "hint_json": base_hints,
        "task": task,
        "task_source": task_source,
        "active_harness": "agentbench.deepagents_app",
        "app_variant": args.app_variant,
        "checkpoint_log_file": str(checkpoint_log_path),
        "auto_repo_checkout": auto_repo_checkout,
        "workspace": workspace_metadata,
        "prompt": prompt,
        "decomposition_plan": {
            "steps": [
                {
                    "phase": phase_result.get("phase"),
                    "title": phase_result.get("request_context", {}).get("step_title", ""),
                    "status": "recursion_soft_stop",
                }
                for phase_result in phase_results
            ],
        },
        "step_results": phase_results,
        "execution_loop_trace": {
            "enabled": env_flag("AGENTBENCH_EXECUTION_LOOP", default=False),
            "completed": False,
            "final_reason": "recursion_soft_stop",
            "steps": [],
        },
        "measurements": [],
        "measurements_summary": summarize_measurements([]),
        "result": result,
        "soft_stop": soft_stop,
        "auto_run_report": {
            "enabled": False,
            "success": None,
            "reason": "recursion_soft_stop",
        },
    }
    (others_dir / "soft_stop.json").write_text(
        json.dumps(soft_stop, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )
    save_result(others_dir, annotate_with_provenance(payload, "result"))
    log_lifecycle_event(
        stage="workflow_recursion_soft_stopped",
        payload={
            "event_kind": "workflow",
            "parent_run_id": parent_run_id,
            "soft_stop": soft_stop,
        },
    )
    set_checkpoint_log_file(None)
    set_lifecycle_log_file(None)


def _strip_ansi(value: str) -> str:
    return ANSI_ESCAPE_RE.sub("", value)


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_float(value: object) -> float | None:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _format_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _diff_ms(start: str | None, end: str | None) -> float | None:
    start_dt = _parse_iso_timestamp(start)
    end_dt = _parse_iso_timestamp(end)
    if start_dt is None or end_dt is None:
        return None
    return round((end_dt - start_dt).total_seconds() * 1000.0, 3)


def parse_frontend_scheduler_events(log_path: str | None) -> list[dict]:
    if not log_path:
        return []
    path = Path(log_path)
    if not path.exists():
        return []

    events: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = _strip_ansi(raw_line)
        match = FRONTEND_SELECTION_RE.search(line)
        if not match:
            continue
        events.append(
            {
                "timestamp": match.group("timestamp"),
                "worker_id": match.group("worker_id"),
                "dp_rank": _format_int(match.group("dp_rank")),
                "logit": _format_float(match.group("logit")),
                "cached_blocks": _format_int(match.group("cached_blocks")),
                "tree_size": _format_int(match.group("tree_size")),
                "total_blocks": _format_int(match.group("total_blocks")),
            }
        )
    return events


def _finalize_worker_request_observation(observation: dict) -> dict:
    decode_events = observation.pop("decode_events", [])
    if decode_events:
        observation["first_decode_timestamp"] = decode_events[0]["timestamp"]
        observation["last_decode_timestamp"] = decode_events[-1]["timestamp"]
        observation["decode_event_count"] = len(decode_events)
        observation["max_decode_tokens"] = max(item["token"] for item in decode_events)
        observation["max_decode_queue_req"] = max(item["queue_req"] for item in decode_events)
        observation["max_gen_throughput_tps"] = max(item["gen_throughput_tps"] for item in decode_events)
        observation["decode_cuda_graph_seen"] = any(item["cuda_graph"] for item in decode_events)
    else:
        observation["first_decode_timestamp"] = None
        observation["last_decode_timestamp"] = None
        observation["decode_event_count"] = 0
        observation["max_decode_tokens"] = None
        observation["max_decode_queue_req"] = None
        observation["max_gen_throughput_tps"] = None
        observation["decode_cuda_graph_seen"] = False
    return observation


def parse_worker_request_observations(log_path: str | None) -> list[dict]:
    if not log_path:
        return []
    path = Path(log_path)
    if not path.exists():
        return []

    observations: list[dict] = []
    current: dict | None = None
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = _strip_ansi(raw_line)
        prefill_match = WORKER_PREFILL_RE.search(line)
        if prefill_match:
            if current is not None:
                observations.append(_finalize_worker_request_observation(current))
            current = {
                "prefill_timestamp": prefill_match.group("timestamp"),
                "new_seq_count": _format_int(prefill_match.group("new_seq")),
                "new_token_count": _format_int(prefill_match.group("new_token")),
                "cached_token_count": _format_int(prefill_match.group("cached_token")),
                "prefill_token_usage": _format_float(prefill_match.group("token_usage")),
                "prefill_running_req": _format_int(prefill_match.group("running_req")),
                "prefill_queue_req": _format_int(prefill_match.group("queue_req")),
                "input_throughput_tps": _format_float(prefill_match.group("input_throughput")),
                "prefill_cuda_graph": prefill_match.group("cuda_graph") == "True",
                "decode_events": [],
            }
            continue

        decode_match = WORKER_DECODE_RE.search(line)
        if decode_match and current is not None:
            current["decode_events"].append(
                {
                    "timestamp": decode_match.group("timestamp"),
                    "running_req": _format_int(decode_match.group("running_req")),
                    "token": _format_int(decode_match.group("token")),
                    "token_usage": _format_float(decode_match.group("token_usage")),
                    "cuda_graph": decode_match.group("cuda_graph") == "True",
                    "gen_throughput_tps": _format_float(decode_match.group("gen_throughput")),
                    "queue_req": _format_int(decode_match.group("queue_req")),
                }
            )

    if current is not None:
        observations.append(_finalize_worker_request_observation(current))
    return observations


def build_runtime_events(
    measurements: list[dict],
    *,
    frontend_scheduler_events: list[dict] | None = None,
    worker_request_observations: list[dict] | None = None,
) -> list[dict]:
    events = []
    frontend_scheduler_events = frontend_scheduler_events or []
    worker_request_observations = worker_request_observations or []

    for index, item in enumerate(measurements):
        request_context = item.get("request_context") or {}
        cached_token_count = item.get("cached_input_tokens")
        if cached_token_count is None:
            cached_token_count = item.get("cached_prompt_tokens")
        cache_hit = cached_token_count is not None and cached_token_count > 0
        input_tokens = item.get("input_tokens")
        recomputed_prefix_tokens = None
        if isinstance(input_tokens, int) and isinstance(cached_token_count, int):
            recomputed_prefix_tokens = max(input_tokens - cached_token_count, 0)

        frontend_event = frontend_scheduler_events[index] if index < len(frontend_scheduler_events) else None
        worker_observation = (
            worker_request_observations[index] if index < len(worker_request_observations) else None
        )
        timestamp = None
        worker_id = None
        router_mode = None
        scheduler = None
        worker_metrics = None
        source = "agentbench_response_proxy"
        ttft_ms = None
        decode_ms = None

        if frontend_event is not None:
            timestamp = frontend_event.get("timestamp")
            worker_id = frontend_event.get("worker_id")
            router_mode = "kv_router_scheduler"
            scheduler = {
                "dp_rank": frontend_event.get("dp_rank"),
                "logit": frontend_event.get("logit"),
                "cached_blocks": frontend_event.get("cached_blocks"),
                "tree_size": frontend_event.get("tree_size"),
                "total_blocks": frontend_event.get("total_blocks"),
            }
            source = "frontend_log_alignment"

        if worker_observation is not None:
            if timestamp is None:
                timestamp = worker_observation.get("prefill_timestamp")
            observed_cached = worker_observation.get("cached_token_count")
            if isinstance(observed_cached, int):
                cached_token_count = observed_cached
                cache_hit = observed_cached > 0
                if isinstance(input_tokens, int):
                    recomputed_prefix_tokens = max(input_tokens - observed_cached, 0)
            worker_metrics = {
                "prefill_timestamp": worker_observation.get("prefill_timestamp"),
                "first_decode_timestamp": worker_observation.get("first_decode_timestamp"),
                "last_decode_timestamp": worker_observation.get("last_decode_timestamp"),
                "new_seq_count": worker_observation.get("new_seq_count"),
                "new_token_count": worker_observation.get("new_token_count"),
                "prefill_token_usage": worker_observation.get("prefill_token_usage"),
                "prefill_running_req": worker_observation.get("prefill_running_req"),
                "prefill_queue_req": worker_observation.get("prefill_queue_req"),
                "input_throughput_tps": worker_observation.get("input_throughput_tps"),
                "prefill_cuda_graph": worker_observation.get("prefill_cuda_graph"),
                "decode_event_count": worker_observation.get("decode_event_count"),
                "max_decode_tokens": worker_observation.get("max_decode_tokens"),
                "max_decode_queue_req": worker_observation.get("max_decode_queue_req"),
                "max_gen_throughput_tps": worker_observation.get("max_gen_throughput_tps"),
                "decode_cuda_graph_seen": worker_observation.get("decode_cuda_graph_seen"),
            }
            ttft_ms = _diff_ms(timestamp or worker_observation.get("prefill_timestamp"), worker_observation.get("first_decode_timestamp"))
            decode_ms = _diff_ms(
                worker_observation.get("first_decode_timestamp"),
                worker_observation.get("last_decode_timestamp"),
            )
            source = "frontend_worker_log_alignment" if frontend_event is not None else "worker_log_alignment"

        events.append(
            {
                "timestamp": timestamp,
                "request_id": request_context.get("request_id"),
                "parent_run_id": request_context.get("parent_run_id"),
                "task_instance_id": request_context.get("task_instance_id"),
                "phase": item.get("phase"),
                "step_index": item.get("step_index"),
                "step_title": item.get("step_title"),
                "worker_id": worker_id,
                "worker_host": None,
                "model_name": item.get("model_name_reported") or item.get("model"),
                "router_mode": router_mode,
                "request_hints": item.get("hints"),
                "cache": {
                    "cache_hit": cache_hit,
                    "cached_token_count": cached_token_count,
                    "reused_prefix_tokens": cached_token_count,
                    "recomputed_prefix_tokens": recomputed_prefix_tokens,
                },
                "placement": {
                    "actual_tier": None,
                    "stayed_on_gpu": None,
                    "moved_to_cpu": None,
                    "moved_to_nvme": None,
                    "fetched_from_cpu": None,
                    "fetched_from_nvme": None,
                    "recomputed_instead_of_fetch": None,
                },
                "eviction": {
                    "eviction_happened": None,
                    "evicted_block_count": None,
                    "evicted_token_estimate": None,
                    "eviction_reason": None,
                },
                "latency": {
                    "ttft_ms": ttft_ms,
                    "end_to_end_ms": item.get("latency_ms"),
                    "prefill_ms": None,
                    "decode_ms": decode_ms,
                    "fetch_ms": None,
                    "recompute_ms": None,
                },
                "scheduler": scheduler,
                "worker_metrics": worker_metrics,
                "alignment": {
                    "strategy": "sequential_log_order",
                    "sequence_index": index,
                    "frontend_event_found": frontend_event is not None,
                    "worker_observation_found": worker_observation is not None,
                },
                "source": source,
            }
        )
    return events


def write_runtime_events_jsonl(run_dir: Path, runtime_events: list[dict]) -> Path:
    output_path = run_dir / "runtime_events.jsonl"
    lines = [json.dumps(item, default=stringify_unknown) for item in runtime_events]
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output_path


def write_runtime_events_json(run_dir: Path, runtime_events: list[dict]) -> Path:
    output_path = run_dir / "runtime_events.json"
    output_path.write_text(
        json.dumps(runtime_events, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )
    return output_path


def collect_runtime_logs(run_dir: Path, *, since_iso: str) -> dict[str, object]:
    if shutil.which("docker") is None:
        return {
            "docker_available": False,
            "frontend_log_file": None,
            "worker_log_file": None,
        }

    results: dict[str, object] = {
        "docker_available": True,
        "frontend_log_file": None,
        "worker_log_file": None,
    }
    targets = [
        (FRONTEND_CONTAINER_NAME, "frontend_runtime.log", "frontend_log_file"),
        (WORKER_CONTAINER_NAME, "worker_runtime.log", "worker_log_file"),
    ]
    for container_name, filename, metadata_key in targets:
        completed = run_command(
            ["docker", "logs", "--since", since_iso, container_name],
            check=False,
        )
        output_path = run_dir / filename
        output_path.write_text(
            (completed.stdout or "") + (completed.stderr or ""),
            encoding="utf-8",
        )
        results[metadata_key] = str(output_path)
        results[f"{container_name}_exit_code"] = completed.returncode

    boundary_log = os.environ.get("AGENTBENCH_FRONTEND_BOUNDARY_LOG")
    if boundary_log:
        source_path = Path(boundary_log).expanduser()
        copied_path = run_dir / "frontend_boundary_proxy.log"
        if source_path.exists():
            proxy_text = source_path.read_text(encoding="utf-8", errors="ignore")
            copied_path.write_text(proxy_text, encoding="utf-8")
            frontend_log_file = results.get("frontend_log_file")
            if isinstance(frontend_log_file, str):
                frontend_path = Path(frontend_log_file)
                existing = (
                    frontend_path.read_text(encoding="utf-8", errors="ignore")
                    if frontend_path.exists()
                    else ""
                )
                frontend_path.write_text(
                    existing
                    + ("\n" if existing and not existing.endswith("\n") else "")
                    + "# frontend boundary proxy log\n"
                    + proxy_text,
                    encoding="utf-8",
                )
            results["frontend_boundary_log_file"] = str(copied_path)
            results["frontend_boundary_log_found"] = True
        else:
            results["frontend_boundary_log_file"] = str(source_path)
            results["frontend_boundary_log_found"] = False
    return results


def summarize_measurements(measurements: list[dict]) -> dict:
    total_latency_ms = 0.0
    phase_counts: dict[str, int] = {}
    phases_over_limit: list[dict[str, object]] = []
    for item in measurements:
        phase = str(item.get("phase") or "unknown")
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        latency_ms = float(item.get("latency_ms") or 0.0)
        total_latency_ms += latency_ms
        prompt_tokens = item.get("prompt_tokens")
        if isinstance(prompt_tokens, int) and prompt_tokens >= 3500:
            phases_over_limit.append(
                {
                    "phase": phase,
                    "step_index": item.get("step_index"),
                    "prompt_tokens": prompt_tokens,
                }
            )

    return {
        "call_count": len(measurements),
        "phase_counts": phase_counts,
        "total_model_latency_ms": round(total_latency_ms, 3),
        "large_prompt_calls": phases_over_limit,
    }


def _classify_prefill_decode(item: dict) -> str:
    input_tokens = item.get("input_tokens")
    output_tokens = item.get("output_tokens")
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        if input_tokens >= max(2 * output_tokens, 2000):
            return "prefill-heavy"
        if output_tokens >= max(2 * input_tokens, 1000):
            return "decode-heavy"
        return "mixed"
    prompt_chars = item.get("prompt_chars")
    if isinstance(prompt_chars, int) and prompt_chars >= 8000:
        return "likely prefill-heavy"
    return "unknown"


def _classify_reuse(item: dict) -> str:
    cached_input_tokens = item.get("cached_input_tokens")
    cached_prompt_tokens = item.get("cached_prompt_tokens")
    cached = 0
    if isinstance(cached_input_tokens, int):
        cached = max(cached, cached_input_tokens)
    if isinstance(cached_prompt_tokens, int):
        cached = max(cached, cached_prompt_tokens)
    if cached > 0:
        return f"yes ({cached} cached tokens)"
    if cached_input_tokens is None and cached_prompt_tokens is None:
        return "unknown"
    return "no"


def _classify_pressure(item: dict) -> str:
    input_tokens = item.get("input_tokens")
    prompt_tokens = item.get("prompt_tokens")
    prompt_chars = item.get("prompt_chars")
    finish_reason = item.get("finish_reason")
    max_prompt_tokens = None
    for value in (input_tokens, prompt_tokens):
        if isinstance(value, int):
            max_prompt_tokens = max(value, max_prompt_tokens or value)
    if isinstance(max_prompt_tokens, int):
        if max_prompt_tokens >= 12000:
            return "very high"
        if max_prompt_tokens >= 3500:
            return "high"
        if max_prompt_tokens >= 1500:
            return "moderate"
    if isinstance(prompt_chars, int):
        if prompt_chars >= 50000:
            return "very high"
        if prompt_chars >= 10000:
            return "high"
        if prompt_chars >= 5000:
            return "moderate"
    if finish_reason == "length":
        return "high"
    return "low"


def build_measurement_analysis(measurements: list[dict]) -> dict:
    rows = []
    for item in measurements:
        rows.append(
            {
                "phase": item.get("phase"),
                "step_index": item.get("step_index"),
                "latency_ms": item.get("latency_ms"),
                "input_tokens": item.get("input_tokens"),
                "output_tokens": item.get("output_tokens"),
                "cached_input_tokens": item.get("cached_input_tokens"),
                "finish_reason": item.get("finish_reason"),
                "prefill_decode_profile": _classify_prefill_decode(item),
                "reuse_signal": _classify_reuse(item),
                "pressure_risk": _classify_pressure(item),
            }
        )

    most_prefill_heavy = None
    highest_input_tokens = -1
    highest_pressure = None
    pressure_rank = {"low": 0, "moderate": 1, "high": 2, "very high": 3}
    strongest_reuse = None
    strongest_cached = -1
    longest_call = None
    longest_latency = -1.0

    for item in measurements:
        phase = item.get("phase")
        input_tokens = item.get("input_tokens")
        if isinstance(input_tokens, int) and input_tokens > highest_input_tokens:
            highest_input_tokens = input_tokens
            most_prefill_heavy = phase

        risk = _classify_pressure(item)
        if highest_pressure is None or pressure_rank[risk] > pressure_rank[highest_pressure["risk"]]:
            highest_pressure = {"phase": phase, "risk": risk}

        cached = 0
        for key in ("cached_input_tokens", "cached_prompt_tokens"):
            value = item.get(key)
            if isinstance(value, int):
                cached = max(cached, value)
        if cached > strongest_cached:
            strongest_cached = cached
            strongest_reuse = phase if cached > 0 else strongest_reuse

        latency_ms = item.get("latency_ms")
        if isinstance(latency_ms, (int, float)) and latency_ms > longest_latency:
            longest_latency = float(latency_ms)
            longest_call = phase

    return {
        "summary": {
            "most_prefill_heavy_phase": most_prefill_heavy,
            "strongest_reuse_phase": strongest_reuse,
            "highest_pressure_phase": highest_pressure["phase"] if highest_pressure else None,
            "highest_pressure_risk": highest_pressure["risk"] if highest_pressure else None,
            "slowest_phase": longest_call,
            "slowest_phase_latency_ms": round(longest_latency, 3) if longest_latency >= 0 else None,
        },
        "rows": rows,
    }


def _normalized_ratio(numerator: float | int | None, denominator: float | int | None) -> float:
    if numerator is None or denominator in (None, 0):
        return 0.0
    return max(0.0, min(float(numerator) / float(denominator), 1.0))


def _phase_future_turn_likelihood(phase: str) -> float:
    if phase == "planning":
        return 0.45
    if phase == "synthesis":
        return 0.2
    if phase.startswith("step_"):
        return 0.75
    return 0.4


def _phase_recency_proxy(phase: str, step_index: int | None, total_steps: int) -> float:
    if phase == "planning":
        return 0.35
    if phase == "synthesis":
        return 0.3
    if phase.startswith("step_") and step_index is not None and total_steps > 0:
        return max(0.2, min(step_index / total_steps, 1.0))
    return 0.4


def _priority_score(hints: dict) -> float:
    priority = hints.get("priority")
    if isinstance(priority, (int, float)):
        return max(0.0, min(float(priority) / 10.0, 1.0))
    return 0.5


def _reuse_score(item: dict) -> float:
    hints = item.get("hints") or {}
    hint_reuse = hints.get("reuse_likelihood")
    if not isinstance(hint_reuse, (int, float)):
        hint_reuse = 0.5
    cached_input = item.get("cached_input_tokens")
    input_tokens = item.get("input_tokens")
    observed_reuse = _normalized_ratio(cached_input, input_tokens)
    return round((0.6 * float(hint_reuse)) + (0.4 * observed_reuse), 4)


def _latency_value_score(item: dict, max_latency_ms: float) -> float:
    latency_ms = item.get("latency_ms")
    if not isinstance(latency_ms, (int, float)) or max_latency_ms <= 0:
        return 0.0
    return round(max(0.0, min(float(latency_ms) / max_latency_ms, 1.0)), 4)


def _size_penalty_score(item: dict, max_prompt_tokens: int) -> float:
    prompt_tokens = item.get("prompt_tokens") or item.get("input_tokens")
    if not isinstance(prompt_tokens, int) or max_prompt_tokens <= 0:
        return 0.0
    return round(max(0.0, min(prompt_tokens / max_prompt_tokens, 1.0)), 4)


def build_cache_value_analysis(measurements: list[dict]) -> dict:
    max_latency_ms = max(
        (float(item.get("latency_ms")) for item in measurements if isinstance(item.get("latency_ms"), (int, float))),
        default=0.0,
    )
    max_prompt_tokens = max(
        (
            int(item.get("prompt_tokens") or item.get("input_tokens"))
            for item in measurements
            if isinstance(item.get("prompt_tokens") or item.get("input_tokens"), int)
        ),
        default=0,
    )
    total_steps = sum(1 for item in measurements if str(item.get("phase") or "").startswith("step_"))

    rows = []
    for item in measurements:
        phase = str(item.get("phase") or "unknown")
        step_index = item.get("step_index")
        hints = item.get("hints") or {}

        reuse = _reuse_score(item)
        priority = _priority_score(hints)
        recency = _phase_recency_proxy(phase, step_index if isinstance(step_index, int) else None, total_steps)
        future_turn = _phase_future_turn_likelihood(phase)
        latency_value = _latency_value_score(item, max_latency_ms)
        size_penalty = _size_penalty_score(item, max_prompt_tokens)

        value_score = round(
            (
                0.28 * reuse
                + 0.18 * priority
                + 0.12 * recency
                + 0.18 * future_turn
                + 0.18 * latency_value
                - 0.12 * size_penalty
            ),
            4,
        )

        keep_recommendation = "keep"
        if value_score < 0.35:
            keep_recommendation = "evict-first"
        elif value_score < 0.55:
            keep_recommendation = "spill-or-recompute"

        rows.append(
            {
                "phase": phase,
                "step_index": step_index,
                "reuse_score": reuse,
                "priority_score": round(priority, 4),
                "recency_score": round(recency, 4),
                "future_turn_score": round(future_turn, 4),
                "latency_value_score": latency_value,
                "size_penalty_score": size_penalty,
                "cache_value_score": value_score,
                "keep_recommendation": keep_recommendation,
            }
        )

    sorted_rows = sorted(rows, key=lambda row: row["cache_value_score"], reverse=True)
    return {
        "formula_notes": {
            "description": "Higher scores mean the cached context is more worth keeping in fast memory.",
            "weights": {
                "reuse_score": 0.28,
                "priority_score": 0.18,
                "recency_score": 0.12,
                "future_turn_score": 0.18,
                "latency_value_score": 0.18,
                "size_penalty_score": -0.12,
            },
        },
        "summary": {
            "highest_value_phase": sorted_rows[0]["phase"] if sorted_rows else None,
            "lowest_value_phase": sorted_rows[-1]["phase"] if sorted_rows else None,
            "keep_candidates": [row["phase"] for row in sorted_rows if row["keep_recommendation"] == "keep"],
            "evict_first_candidates": [row["phase"] for row in sorted_rows if row["keep_recommendation"] == "evict-first"],
        },
        "rows": sorted_rows,
    }


def build_measurements_table(measurements: list[dict]) -> list[dict]:
    return [row_with_provenance(dict(item), "measurements") for item in measurements]


def build_execution_loop_table(trace: dict) -> list[dict]:
    rows: list[dict] = []
    for step in trace.get("steps", []) or []:
        tool_progress = step.get("tool_progress") or {}
        workspace = step.get("workspace") or {}
        request_context = step.get("request_context") or {}
        rows.append(
            {
                "enabled": trace.get("enabled"),
                "completed": trace.get("completed"),
                "final_reason": trace.get("final_reason"),
                "max_steps": trace.get("max_steps"),
                "require_test": trace.get("require_test"),
                "step_index": step.get("step_index"),
                "step_type": step.get("step_type"),
                "input_reason": step.get("input_reason"),
                "tool_call_count": tool_progress.get("tool_call_count"),
                "tool_call_names": ", ".join(tool_progress.get("tool_call_names") or []),
                "has_read_file": tool_progress.get("has_read_file"),
                "has_write_or_edit": tool_progress.get("has_write_or_edit"),
                "has_execute": tool_progress.get("has_execute"),
                "workspace_changed": workspace.get("workspace_changed"),
                "patch_nonempty": workspace.get("patch_nonempty"),
                "execute_failed": step.get("execute_failed"),
                "request_id": request_context.get("request_id"),
                "hint_probe_id": (step.get("hints") or {}).get("hint_probe_id"),
                "execute_result_preview": step.get("execute_result_preview"),
            }
        )
    if not rows:
        rows.append(
            {
                "enabled": trace.get("enabled"),
                "completed": trace.get("completed"),
                "final_reason": trace.get("final_reason"),
                "max_steps": trace.get("max_steps"),
                "require_test": trace.get("require_test"),
            }
        )
    return rows


def build_measurement_analysis_table(analysis: dict) -> list[dict]:
    return [row_with_provenance(dict(row), "measurement_analysis") for row in analysis.get("rows", [])]


def build_measurement_summary_table(analysis: dict) -> list[dict]:
    return [row_with_provenance(dict(analysis.get("summary", {})), "measurement_analysis")]


def build_cache_value_table(analysis: dict) -> list[dict]:
    return [row_with_provenance(dict(row), "cache_value_analysis") for row in analysis.get("rows", [])]


def build_cache_value_summary_table(analysis: dict) -> list[dict]:
    return [row_with_provenance(dict(analysis.get("summary", {})), "cache_value_analysis")]


def build_kv_hierarchy_table(analysis: dict) -> list[dict]:
    return [row_with_provenance(dict(row), "kv_hierarchy_analysis") for row in analysis.get("rows", [])]


def build_kv_hierarchy_summary_table(analysis: dict) -> list[dict]:
    return [row_with_provenance(dict(analysis.get("summary", {})), "kv_hierarchy_analysis")]


def build_runtime_events_table(runtime_events: list[dict]) -> list[dict]:
    rows = []
    for event in runtime_events:
        cache = event.get("cache") or {}
        placement = event.get("placement") or {}
        eviction = event.get("eviction") or {}
        latency = event.get("latency") or {}
        scheduler = event.get("scheduler") or {}
        worker_metrics = event.get("worker_metrics") or {}
        row = {
            "timestamp": event.get("timestamp"),
            "request_id": event.get("request_id"),
            "parent_run_id": event.get("parent_run_id"),
            "task_instance_id": event.get("task_instance_id"),
            "phase": event.get("phase"),
            "step_index": event.get("step_index"),
            "step_title": event.get("step_title"),
            "worker_id": event.get("worker_id"),
            "worker_host": event.get("worker_host"),
            "model_name": event.get("model_name"),
            "router_mode": event.get("router_mode"),
            "cache_hit": cache.get("cache_hit"),
            "cached_token_count": cache.get("cached_token_count"),
            "reused_prefix_tokens": cache.get("reused_prefix_tokens"),
            "recomputed_prefix_tokens": cache.get("recomputed_prefix_tokens"),
            "actual_tier": placement.get("actual_tier"),
            "stayed_on_gpu": placement.get("stayed_on_gpu"),
            "moved_to_cpu": placement.get("moved_to_cpu"),
            "moved_to_nvme": placement.get("moved_to_nvme"),
            "fetched_from_cpu": placement.get("fetched_from_cpu"),
            "fetched_from_nvme": placement.get("fetched_from_nvme"),
            "recomputed_instead_of_fetch": placement.get("recomputed_instead_of_fetch"),
            "eviction_happened": eviction.get("eviction_happened"),
            "evicted_block_count": eviction.get("evicted_block_count"),
            "evicted_token_estimate": eviction.get("evicted_token_estimate"),
            "eviction_reason": eviction.get("eviction_reason"),
            "ttft_ms": latency.get("ttft_ms"),
            "end_to_end_ms": latency.get("end_to_end_ms"),
            "prefill_ms": latency.get("prefill_ms"),
            "decode_ms": latency.get("decode_ms"),
            "fetch_ms": latency.get("fetch_ms"),
            "recompute_ms": latency.get("recompute_ms"),
            "scheduler_dp_rank": scheduler.get("dp_rank"),
            "scheduler_logit": scheduler.get("logit"),
            "scheduler_cached_blocks": scheduler.get("cached_blocks"),
            "scheduler_tree_size": scheduler.get("tree_size"),
            "scheduler_total_blocks": scheduler.get("total_blocks"),
            "worker_prefill_timestamp": worker_metrics.get("prefill_timestamp"),
            "worker_first_decode_timestamp": worker_metrics.get("first_decode_timestamp"),
            "worker_last_decode_timestamp": worker_metrics.get("last_decode_timestamp"),
            "worker_new_seq_count": worker_metrics.get("new_seq_count"),
            "worker_new_token_count": worker_metrics.get("new_token_count"),
            "worker_prefill_token_usage": worker_metrics.get("prefill_token_usage"),
            "worker_input_throughput_tps": worker_metrics.get("input_throughput_tps"),
            "worker_decode_event_count": worker_metrics.get("decode_event_count"),
            "worker_max_decode_tokens": worker_metrics.get("max_decode_tokens"),
            "worker_max_gen_throughput_tps": worker_metrics.get("max_gen_throughput_tps"),
            "source": event.get("source"),
        }
        rows.append(row_with_provenance(row, "runtime_events"))
    return rows


def build_runtime_alignment_table(analysis: dict) -> list[dict]:
    return [
        {
            "phase": row.get("phase"),
            "decision_type": row.get("decision_type"),
            "agent_component": row.get("agent_component"),
            "runtime_component": row.get("runtime_component"),
            "agent_side_decision": row.get("agent_side_decision"),
            "runtime_side_response": row.get("runtime_side_response"),
            "evidence": row.get("evidence"),
            "alignment_judgment": row.get("alignment_judgment"),
            "agreement_status": row.get("agreement_status"),
            "worker_id": row.get("worker_id"),
            "ttft_ms": row.get("ttft_ms"),
            "decode_ms": row.get("decode_ms"),
            "end_to_end_ms": row.get("end_to_end_ms"),
        }
        for row in analysis.get("rows", [])
    ]


def build_runtime_alignment_summary_table(analysis: dict) -> list[dict]:
    return [dict(analysis.get("summary", {}))]


def build_runtime_hint_alignment_table(analysis: dict) -> list[dict]:
    return [
        {
            "phase": row.get("phase"),
            "hint_name": row.get("hint_name"),
            "hint_value_sent": row.get("hint_value_sent"),
            "hint_source": row.get("hint_source"),
            "request_wrapper_observed": row.get("request_wrapper_observed"),
            "dynamo_frontend_observed": row.get("dynamo_frontend_observed"),
            "dynamo_frontend_state": row.get("dynamo_frontend_state"),
            "sglang_worker_observed": row.get("sglang_worker_observed"),
            "sglang_worker_state": row.get("sglang_worker_state"),
            "expected_runtime_effect": row.get("expected_runtime_effect"),
            "observed_runtime_effect": row.get("observed_runtime_effect"),
            "claim_level": row.get("claim_level"),
            "status": row.get("status"),
            "evidence": row.get("evidence"),
        }
        for row in analysis.get("rows", [])
    ]


def build_runtime_hint_alignment_summary_table(analysis: dict) -> list[dict]:
    return [dict(analysis.get("summary", {}))]


def build_run_summary_table(
    *,
    parent_run_id: str,
    task: dict,
    model: str,
    workspace_metadata: dict,
    measurement_analysis: dict,
    cache_value_analysis: dict,
    kv_hierarchy_analysis: dict,
    runtime_alignment_analysis: dict,
    workspace_artifacts: dict,
) -> list[dict]:
    phase_rows = measurement_analysis.get("rows", [])
    planning_latency = next((row.get("latency_ms") for row in phase_rows if row.get("phase") == "planning"), None)
    synthesis_latency = next((row.get("latency_ms") for row in phase_rows if row.get("phase") == "synthesis"), None)
    total_step_latency = round(
        sum(
            float(row.get("latency_ms") or 0.0)
            for row in phase_rows
            if str(row.get("phase") or "").startswith("step_")
        ),
        3,
    )
    row = {
        "parent_run_id": parent_run_id,
        "instance_id": task.get("instance_id"),
        "repo": task.get("repo"),
        "model": model,
        "workspace_mode": workspace_metadata.get("workspace_mode"),
        "planning_latency_ms": planning_latency,
        "total_step_latency_ms": total_step_latency,
        "synthesis_latency_ms": synthesis_latency,
        "most_prefill_heavy_phase": measurement_analysis.get("summary", {}).get("most_prefill_heavy_phase"),
        "highest_pressure_phase": measurement_analysis.get("summary", {}).get("highest_pressure_phase"),
        "strongest_reuse_phase": measurement_analysis.get("summary", {}).get("strongest_reuse_phase"),
        "best_cache_value_phase": cache_value_analysis.get("summary", {}).get("highest_value_phase"),
        "best_gpu_candidate_phase": (kv_hierarchy_analysis.get("summary", {}).get("gpu_candidates") or [None])[0],
        "runtime_alignment_status_summary": runtime_alignment_analysis.get("summary", {}).get("best_supported_gpu_candidate"),
        "patch_nonempty": workspace_artifacts.get("patch_nonempty"),
        "git_diff_nonempty": bool(workspace_artifacts.get("git_diff_stat")),
    }
    return [row_with_provenance(row, "runtime_alignment_analysis")]


def build_runtime_lifecycle_events(runtime_events: list[dict]) -> list[dict]:
    lifecycle_events: list[dict] = []
    for runtime_event in runtime_events:
        request_context = {
            "request_id": runtime_event.get("request_id"),
            "parent_run_id": runtime_event.get("parent_run_id"),
            "task_instance_id": runtime_event.get("task_instance_id"),
            "phase": runtime_event.get("phase"),
            "step_index": runtime_event.get("step_index"),
            "step_title": runtime_event.get("step_title"),
        }
        base_payload = {
            "event_kind": "runtime_observation",
            "phase": runtime_event.get("phase"),
            "step_index": runtime_event.get("step_index"),
            "step_title": runtime_event.get("step_title"),
            "request_context": request_context,
            "worker_id": runtime_event.get("worker_id"),
            "router_mode": runtime_event.get("router_mode"),
            "source": runtime_event.get("source"),
            "scheduler": runtime_event.get("scheduler"),
            "worker_metrics": runtime_event.get("worker_metrics"),
            "cache": runtime_event.get("cache"),
            "latency": runtime_event.get("latency"),
            "alignment": runtime_event.get("alignment"),
        }

        if runtime_event.get("timestamp") is not None:
            lifecycle_events.append(
                {
                    "timestamp": runtime_event.get("timestamp"),
                    "stage": "frontend_dynamo_runtime_observed",
                    **base_payload,
                }
            )

        scheduler = runtime_event.get("scheduler") or {}
        if scheduler:
            lifecycle_events.append(
                {
                    "timestamp": runtime_event.get("timestamp"),
                    "stage": "kv_router_worker_selected",
                    **base_payload,
                }
            )

        worker_metrics = runtime_event.get("worker_metrics") or {}
        if worker_metrics.get("prefill_timestamp") is not None:
            lifecycle_events.append(
                {
                    "timestamp": worker_metrics.get("prefill_timestamp"),
                    "stage": "sglang_worker_prefill_observed",
                    **base_payload,
                }
            )
        if worker_metrics.get("first_decode_timestamp") is not None:
            lifecycle_events.append(
                {
                    "timestamp": worker_metrics.get("first_decode_timestamp"),
                    "stage": "sglang_worker_first_decode_observed",
                    **base_payload,
                }
            )
        if worker_metrics.get("last_decode_timestamp") is not None:
            lifecycle_events.append(
                {
                    "timestamp": worker_metrics.get("last_decode_timestamp"),
                    "stage": "sglang_worker_decode_completed",
                    **base_payload,
                }
            )
    return lifecycle_events


def sort_lifecycle_events(events: list[dict]) -> list[dict]:
    def event_sort_key(item: dict, index: int) -> tuple[int, float, int, int]:
        timestamp = _parse_iso_timestamp(item.get("timestamp"))
        if timestamp is None:
            return (1, 0.0, int(item.get("sequence_index", 0) or 0), index)
        return (0, timestamp.timestamp(), int(item.get("sequence_index", 0) or 0), index)

    sorted_events = sorted(
        enumerate(events),
        key=lambda pair: event_sort_key(pair[1], pair[0]),
    )
    normalized: list[dict] = []
    for new_index, (_, event) in enumerate(sorted_events, start=1):
        normalized_event = dict(event)
        normalized_event["sequence_index"] = new_index
        normalized.append(normalized_event)
    return normalized


def build_task_lifecycle_trace(
    events: list[dict],
    *,
    metadata: dict[str, object],
    runtime_events: list[dict] | None = None,
) -> dict:
    all_events = list(events)
    if runtime_events:
        all_events.extend(build_runtime_lifecycle_events(runtime_events))
    ordered_events = sort_lifecycle_events(all_events)
    stage_counts: dict[str, int] = {}
    phases_seen: list[str] = []
    for event in ordered_events:
        stage = str(event.get("stage") or "unknown")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        phase = event.get("phase")
        if isinstance(phase, str) and phase not in phases_seen:
            phases_seen.append(phase)

    return {
        **metadata,
        "summary": {
            "event_count": len(ordered_events),
            "stage_counts": stage_counts,
            "stages_seen": list(stage_counts.keys()),
            "phases_seen": phases_seen,
            "prompt_event_count": sum(1 for event in ordered_events if event.get("event_kind") == "prompt"),
            "request_event_count": sum(1 for event in ordered_events if event.get("event_kind") == "request_dispatch"),
            "response_event_count": sum(1 for event in ordered_events if event.get("event_kind") == "response"),
            "artifact_event_count": sum(1 for event in ordered_events if event.get("event_kind") == "artifact"),
        },
        "events": ordered_events,
    }


def build_task_lifecycle_table(trace: dict) -> list[dict]:
    def build_summary(event: dict, stage_metadata: dict[str, str]) -> str:
        artifact_name = event.get("artifact_name")
        if artifact_name:
            return f"Artifact written: {artifact_name}"

        response_preview = event.get("response_preview")
        if isinstance(response_preview, str) and response_preview.strip():
            return f"{stage_metadata['description']} Response preview: {_prompt_preview(response_preview, 140)}"

        prompt_preview = event.get("prompt_preview")
        if isinstance(prompt_preview, str) and prompt_preview.strip():
            return f"{stage_metadata['description']} Prompt preview: {_prompt_preview(prompt_preview, 140)}"

        return stage_metadata["description"]

    rows: list[dict] = []
    for event in trace.get("events", []):
        if not isinstance(event, dict):
            continue
        stage_metadata = task_lifecycle_stage_metadata(event.get("stage"))
        row = {
            "seq": event.get("sequence_index"),
            "timestamp": event.get("timestamp"),
            "stage": event.get("stage"),
            "stage_description": stage_metadata["description"],
            "component": stage_metadata["component"],
            "kind": event.get("event_kind"),
            "phase": event.get("phase"),
            "summary": build_summary(event, stage_metadata),
        }
        rows.append(row)
    return rows


def render_task_lifecycle_markdown(trace: dict) -> str:
    summary = trace.get("summary", {})
    events = trace.get("events", [])
    lines = [
        "# Task Lifecycle Trace",
        "",
        "## Summary",
        *markdown_field_table(
            {
                "parent_run_id": trace.get("parent_run_id"),
                "task_instance_id": trace.get("task_instance_id"),
                "task_source": trace.get("task_source"),
                "app_variant": trace.get("app_variant"),
                "model": trace.get("model"),
                "frontend_url": trace.get("frontend_url"),
                "event_count": summary.get("event_count"),
                "stages_seen": summary.get("stages_seen"),
                "phases_seen": summary.get("phases_seen"),
                "prompt_event_count": summary.get("prompt_event_count"),
                "request_event_count": summary.get("request_event_count"),
                "response_event_count": summary.get("response_event_count"),
                "artifact_event_count": summary.get("artifact_event_count"),
            },
            "stage_lifecycle_trace",
            [
                ("parent_run_id", "Parent run id"),
                ("task_instance_id", "Task instance id"),
                ("task_source", "Task source"),
                ("app_variant", "App variant"),
                ("model", "Model"),
                ("frontend_url", "Frontend URL"),
                ("event_count", "Event count"),
                ("stages_seen", "Stages seen"),
                ("phases_seen", "Phases seen"),
                ("prompt_event_count", "Prompt event count"),
                ("request_event_count", "Request event count"),
                ("response_event_count", "Response event count"),
                ("artifact_event_count", "Artifact event count"),
            ],
            include_provenance=False,
        ),
        "",
        "## Event Table",
        "",
        "| Seq | Timestamp | Stage | Component | Category | Description | Kind | Phase | Step | Prompt preview | Response preview | Artifact |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for event in events:
        request_context = event.get("request_context") if isinstance(event.get("request_context"), dict) else {}
        stage_metadata = task_lifecycle_stage_metadata(event.get("stage"))
        step_value = event.get("step_index")
        if step_value is None:
            step_value = request_context.get("step_index")
        lines.append(
            "| {seq} | {ts} | {stage} | {component} | {category} | {description} | {kind} | {phase} | {step} | {prompt} | {response} | {artifact} |".format(
                seq=markdown_value(event.get("sequence_index")),
                ts=markdown_value(event.get("timestamp")),
                stage=markdown_value(event.get("stage")),
                component=markdown_value(stage_metadata["component"]),
                category=markdown_value(stage_metadata["category"]),
                description=markdown_value(stage_metadata["description"]),
                kind=markdown_value(event.get("event_kind")),
                phase=markdown_value(event.get("phase")),
                step=markdown_value(step_value),
                prompt=markdown_value(event.get("prompt_preview")),
                response=markdown_value(event.get("response_preview")),
                artifact=markdown_value(event.get("artifact_name")),
            )
        )
    return "\n".join(lines) + "\n"


def render_cache_value_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    notes = analysis["formula_notes"]
    rows = analysis["rows"]
    lines = [
        "# Cache Value Analysis",
        "",
        "## Summary",
        *markdown_field_table(
            summary,
            "cache_value_analysis",
            [
                ("highest_value_phase", "Highest-value phase"),
                ("lowest_value_phase", "Lowest-value phase"),
                ("keep_candidates", "Keep candidates"),
                ("evict_first_candidates", "Evict-first candidates"),
            ],
        ),
        "",
        "## Formula Notes",
        *markdown_field_table(
            {
                "description": notes["description"],
                "score_inputs": "reuse, priority, recency, future-turn likelihood, latency cost, and prompt-size penalty",
            },
            "cache_value_analysis",
            [
                ("description", "Formula description"),
                ("score_inputs", "Score inputs"),
            ],
        ),
        "",
        "## Phase Table",
        "",
        "| Phase | Phase provenance | Step | Step provenance | Reuse | Reuse provenance | Priority | Priority provenance | Recency | Recency provenance | Future turn | Future-turn provenance | Latency value | Latency provenance | Size penalty | Size provenance | Cache value | Cache-value provenance | Recommendation | Recommendation provenance |",
        "| --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        annotated = row_with_provenance(dict(row), "cache_value_analysis")
        lines.append(
            "| {phase} | {phase_p} | {step} | {step_p} | {reuse} | {reuse_p} | {priority} | {priority_p} | {recency} | {recency_p} | {future_turn} | {future_turn_p} | {latency} | {latency_p} | {size} | {size_p} | {value} | {value_p} | {recommendation} | {recommendation_p} |".format(
                phase=markdown_value(annotated.get("phase")),
                phase_p=annotated.get("phase_provenance", "-"),
                step=markdown_value(annotated.get("step_index")),
                step_p=annotated.get("step_index_provenance", "-"),
                reuse=markdown_value(annotated.get("reuse_score")),
                reuse_p=annotated.get("reuse_score_provenance", "-"),
                priority=markdown_value(annotated.get("priority_score")),
                priority_p=annotated.get("priority_score_provenance", "-"),
                recency=markdown_value(annotated.get("recency_score")),
                recency_p=annotated.get("recency_score_provenance", "-"),
                future_turn=markdown_value(annotated.get("future_turn_score")),
                future_turn_p=annotated.get("future_turn_score_provenance", "-"),
                latency=markdown_value(annotated.get("latency_value_score")),
                latency_p=annotated.get("latency_value_score_provenance", "-"),
                size=markdown_value(annotated.get("size_penalty_score")),
                size_p=annotated.get("size_penalty_score_provenance", "-"),
                value=markdown_value(annotated.get("cache_value_score")),
                value_p=annotated.get("cache_value_score_provenance", "-"),
                recommendation=markdown_value(annotated.get("keep_recommendation")),
                recommendation_p=annotated.get("keep_recommendation_provenance", "-"),
            )
        )
    return "\n".join(lines) + "\n"


def build_kv_hierarchy_analysis(measurements: list[dict], cache_value_analysis: dict) -> dict:
    cache_rows = {
        (row["phase"], row["step_index"]): row
        for row in cache_value_analysis.get("rows", [])
    }
    rows = []
    for item in measurements:
        phase = item.get("phase")
        step_index = item.get("step_index")
        cache_row = cache_rows.get((phase, step_index), {})
        prompt_tokens = item.get("prompt_tokens") or item.get("input_tokens")
        pressure = _classify_pressure(item)
        cache_value_score = float(cache_row.get("cache_value_score", 0.0))
        reuse_score = float(cache_row.get("reuse_score", 0.0))

        recommended_tier = "drop"
        reason = "low estimated reuse value"
        if cache_value_score >= 0.62 and pressure in {"moderate", "high"}:
            recommended_tier = "gpu"
            reason = "high value and still worth preserving in fastest memory"
        elif cache_value_score >= 0.48:
            recommended_tier = "cpu"
            reason = "worth keeping, but cheaper off-GPU residency is acceptable"
        elif cache_value_score >= 0.35:
            recommended_tier = "nvme"
            reason = "lower-value context; preserve only in colder storage if needed"

        movement_priority = "low"
        if recommended_tier == "gpu" and pressure in {"high", "very high"}:
            movement_priority = "high"
        elif recommended_tier in {"cpu", "nvme"}:
            movement_priority = "medium"

        rows.append(
            {
                "phase": phase,
                "step_index": step_index,
                "prompt_tokens": prompt_tokens,
                "pressure_risk": pressure,
                "reuse_score": reuse_score,
                "cache_value_score": cache_value_score,
                "recommended_tier": recommended_tier,
                "movement_priority": movement_priority,
                "reason": reason,
            }
        )

    gpu_candidates = [row["phase"] for row in rows if row["recommended_tier"] == "gpu"]
    cpu_candidates = [row["phase"] for row in rows if row["recommended_tier"] == "cpu"]
    nvme_candidates = [row["phase"] for row in rows if row["recommended_tier"] == "nvme"]
    drop_candidates = [row["phase"] for row in rows if row["recommended_tier"] == "drop"]

    return {
        "summary": {
            "gpu_candidates": gpu_candidates,
            "cpu_candidates": cpu_candidates,
            "nvme_candidates": nvme_candidates,
            "drop_candidates": drop_candidates,
        },
        "rows": rows,
    }


def render_kv_hierarchy_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    rows = analysis["rows"]
    lines = [
        "# KV Hierarchy Analysis",
        "",
        "## Summary",
        *markdown_field_table(
            summary,
            "kv_hierarchy_analysis",
            [
                ("gpu_candidates", "GPU candidates"),
                ("cpu_candidates", "CPU candidates"),
                ("nvme_candidates", "NVMe candidates"),
                ("drop_candidates", "Drop candidates"),
            ],
        ),
        "",
        "## Phase Table",
        "",
        "| Phase | Phase provenance | Step | Step provenance | Prompt tokens | Prompt-token provenance | Pressure | Pressure provenance | Reuse | Reuse provenance | Cache value | Cache-value provenance | Recommended tier | Tier provenance | Movement priority | Movement provenance | Reason | Reason provenance |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        annotated = row_with_provenance(dict(row), "kv_hierarchy_analysis")
        lines.append(
            "| {phase} | {phase_p} | {step} | {step_p} | {prompt_tokens} | {prompt_p} | {pressure} | {pressure_p} | {reuse} | {reuse_p} | {value} | {value_p} | {tier} | {tier_p} | {priority} | {priority_p} | {reason} | {reason_p} |".format(
                phase=markdown_value(annotated.get("phase")),
                phase_p=annotated.get("phase_provenance", "-"),
                step=markdown_value(annotated.get("step_index")),
                step_p=annotated.get("step_index_provenance", "-"),
                prompt_tokens=markdown_value(annotated.get("prompt_tokens")),
                prompt_p=annotated.get("prompt_tokens_provenance", "-"),
                pressure=markdown_value(annotated.get("pressure_risk")),
                pressure_p=annotated.get("pressure_risk_provenance", "-"),
                reuse=markdown_value(annotated.get("reuse_score")),
                reuse_p=annotated.get("reuse_score_provenance", "-"),
                value=markdown_value(annotated.get("cache_value_score")),
                value_p=annotated.get("cache_value_score_provenance", "-"),
                tier=markdown_value(annotated.get("recommended_tier")),
                tier_p=annotated.get("recommended_tier_provenance", "-"),
                priority=markdown_value(annotated.get("movement_priority")),
                priority_p=annotated.get("movement_priority_provenance", "-"),
                reason=markdown_value(annotated.get("reason")),
                reason_p=annotated.get("reason_provenance", "-"),
            )
        )
    return "\n".join(lines) + "\n"


def _runtime_reuse_strength(runtime_event: dict) -> str:
    cache = runtime_event.get("cache") or {}
    cached = cache.get("cached_token_count")
    recomputed = cache.get("recomputed_prefix_tokens")
    if isinstance(cached, int) and isinstance(recomputed, int):
        total = cached + recomputed
        if total > 0:
            ratio = cached / total
            if ratio >= 0.9:
                return "very strong"
            if ratio >= 0.7:
                return "strong"
            if ratio >= 0.4:
                return "moderate"
            return "weak"
    if isinstance(cached, int) and cached > 0:
        return "present"
    return "unknown"


def _runtime_alignment_status(recommended_tier: str | None, runtime_event: dict) -> str:
    actual_tier = (runtime_event.get("placement") or {}).get("actual_tier")
    if actual_tier:
        return "direct-match" if actual_tier == recommended_tier else "direct-mismatch"

    scheduler = runtime_event.get("scheduler") or {}
    cache = runtime_event.get("cache") or {}
    cached_blocks = scheduler.get("cached_blocks")
    cached_tokens = cache.get("cached_token_count")
    reuse_strength = _runtime_reuse_strength(runtime_event)

    if recommended_tier == "gpu":
        if isinstance(cached_blocks, int) and cached_blocks > 0 and reuse_strength in {"strong", "very strong"}:
            return "indirect-support"
        if reuse_strength in {"strong", "very strong"}:
            return "partial-support"
        return "insufficient-runtime-evidence"

    if recommended_tier in {"cpu", "nvme", "drop"}:
        if actual_tier is None and (cached_blocks is not None or cached_tokens is not None):
            return "not-directly-verifiable"
    return "insufficient-runtime-evidence"


def build_runtime_alignment_analysis(
    runtime_events: list[dict],
    cache_value_analysis: dict,
    kv_hierarchy_analysis: dict,
    baseline_result: dict,
    runtime_log_artifacts: dict[str, Any],
) -> dict:
    messages = _lineage_messages(baseline_result.get("response"))
    tool_parser_usage = _extract_tool_parser_usage(
        runtime_log_artifacts.get("frontend_log_file")
        if isinstance(runtime_log_artifacts.get("frontend_log_file"), str)
        else None
    )
    observed_tool_call_names = sorted(
        {
            name
            for message in messages
            for name in message.get("tool_call_names", [])
            if isinstance(name, str) and name
        }
    )
    observed_tool_result_names = sorted(
        {
            message.get("name")
            for message in messages
            if message.get("type") == "tool" and isinstance(message.get("name"), str)
        }
    )
    execute_failure = _extract_execute_failure(messages)
    measurement = baseline_result.get("measurement", {})
    response_text = str(baseline_result.get("response_text") or "")

    def add_row(
        rows: list[dict[str, Any]],
        *,
        phase: str | None,
        decision_type: str,
        agent_component: str,
        runtime_component: str,
        agent_side_decision: str,
        runtime_side_response: str,
        evidence: str,
        alignment_judgment: str,
        agreement_status: str,
        worker_id: Any,
        ttft_ms: Any,
        decode_ms: Any,
        end_to_end_ms: Any,
    ) -> None:
        rows.append(
            {
                "phase": phase,
                "decision_type": decision_type,
                "agent_component": agent_component,
                "runtime_component": runtime_component,
                "agent_side_decision": agent_side_decision,
                "runtime_side_response": runtime_side_response,
                "evidence": evidence,
                "alignment_judgment": alignment_judgment,
                "agreement_status": agreement_status,
                "worker_id": worker_id,
                "ttft_ms": ttft_ms,
                "decode_ms": decode_ms,
                "end_to_end_ms": end_to_end_ms,
            }
        )

    observed_workers: set[str] = set()
    rows: list[dict[str, Any]] = []

    for event in runtime_events:
        phase = event.get("phase")
        worker_metrics = event.get("worker_metrics") or {}
        has_frontend = bool((event.get("alignment") or {}).get("frontend_event_found"))
        has_worker = bool((event.get("alignment") or {}).get("worker_observation_found"))
        worker_id = event.get("worker_id")
        ttft_ms = (event.get("latency") or {}).get("ttft_ms")
        decode_ms = (event.get("latency") or {}).get("decode_ms")
        end_to_end_ms = (event.get("latency") or {}).get("end_to_end_ms")
        prefill_seen = bool(worker_metrics.get("prefill_timestamp"))
        decode_seen = bool(
            worker_metrics.get("first_decode_timestamp")
            or worker_metrics.get("last_decode_timestamp")
            or worker_metrics.get("decode_event_count")
        )
        cached_token_count = (event.get("cache") or {}).get("cached_token_count")
        recomputed_prefix_tokens = (event.get("cache") or {}).get("recomputed_prefix_tokens")
        parser_observed = tool_parser_usage["tool_parser_observed"]
        tool_call_count = sum(int(message.get("tool_call_count", 0)) for message in messages)

        if worker_id:
            observed_workers.add(str(worker_id))

        add_row(
            rows,
            phase=phase,
            decision_type="request_dispatch",
            agent_component="deepagents_app",
            runtime_component="frontend_dynamo",
            agent_side_decision="Sent one baseline model request for the task.",
            runtime_side_response=(
                f"Frontend observed the request and routed it to worker {worker_id}."
                if has_frontend and worker_id
                else "Frontend observation for this request was not found."
            ),
            evidence=(
                f"frontend_event_found={has_frontend}; worker_observation_found={has_worker}; "
                f"request_id={event.get('request_id') or '-'}; worker_id={worker_id or '-'}"
            ),
            alignment_judgment=(
                "Request dispatch aligned with runtime routing evidence."
                if has_frontend
                else "Agent request was recorded, but frontend routing evidence is missing."
            ),
            agreement_status="agreed" if has_frontend else "insufficient_evidence",
            worker_id=worker_id,
            ttft_ms=ttft_ms,
            decode_ms=decode_ms,
            end_to_end_ms=end_to_end_ms,
        )

        add_row(
            rows,
            phase=phase,
            decision_type="tool_availability",
            agent_component="deepagents_app",
            runtime_component="frontend_dynamo",
            agent_side_decision="Expected a tool-capable execution path for coding work.",
            runtime_side_response=(
                f"Frontend/runtime reported tool parser(s): {', '.join(tool_parser_usage['tool_parser_names_seen'])}."
                if parser_observed
                else "No tool parser observation was found in frontend runtime logs."
            ),
            evidence=(
                f"tool_parser_observed={parser_observed}; parsers={', '.join(tool_parser_usage['tool_parser_names_seen']) or '-'}; "
                f"tool_call_count={tool_call_count}"
            ),
            alignment_judgment=(
                "Runtime exposed a tool-capable path consistent with agent expectations."
                if parser_observed
                else "Tool-capable execution was expected, but runtime parser evidence is missing."
            ),
            agreement_status="agreed" if parser_observed else "insufficient_evidence",
            worker_id=worker_id,
            ttft_ms=ttft_ms,
            decode_ms=decode_ms,
            end_to_end_ms=end_to_end_ms,
        )

        add_row(
            rows,
            phase=phase,
            decision_type="tool_use",
            agent_component="deepagents_app",
            runtime_component="frontend_dynamo",
            agent_side_decision=(
                f"Chose tool calls: {', '.join(observed_tool_call_names)}."
                if observed_tool_call_names
                else "Did not emit structured tool calls."
            ),
            runtime_side_response=(
                f"Runtime returned tool results for: {', '.join(observed_tool_result_names)}."
                if observed_tool_result_names
                else "No tool result messages were observed."
            ),
            evidence=(
                f"tool_call_count={tool_call_count}; tool_calls={', '.join(observed_tool_call_names) or '-'}; "
                f"tool_results={', '.join(observed_tool_result_names) or '-'}"
            ),
            alignment_judgment=(
                "Agent tool-use decisions aligned with runtime tool execution."
                if observed_tool_call_names and observed_tool_result_names
                else "Agent/runtime tool behavior diverged or remained incomplete."
            ),
            agreement_status=(
                "agreed"
                if observed_tool_call_names and observed_tool_result_names
                else ("diverged" if tool_call_count == 0 else "partially_agreed")
            ),
            worker_id=worker_id,
            ttft_ms=ttft_ms,
            decode_ms=decode_ms,
            end_to_end_ms=end_to_end_ms,
        )

        add_row(
            rows,
            phase=phase,
            decision_type="runtime_execution",
            agent_component="deepagents_app",
            runtime_component="sglang_worker",
            agent_side_decision="Expected the request to execute on a routed worker.",
            runtime_side_response=(
                "Worker showed both prefill and decode activity."
                if prefill_seen and decode_seen
                else (
                    "Worker showed prefill activity only."
                    if prefill_seen
                    else ("Worker showed decode activity only." if decode_seen else "Worker activity was not observed.")
                )
            ),
            evidence=(
                f"prefill_seen={prefill_seen}; decode_seen={decode_seen}; "
                f"cached_token_count={cached_token_count if cached_token_count is not None else '-'}; "
                f"recomputed_prefix_tokens={recomputed_prefix_tokens if recomputed_prefix_tokens is not None else '-'}"
            ),
            alignment_judgment=(
                "Worker execution evidence aligned with the model request."
                if has_worker and (prefill_seen or decode_seen)
                else "Runtime execution evidence is too weak to confirm worker-side execution details."
            ),
            agreement_status=(
                "agreed"
                if has_worker and (prefill_seen or decode_seen)
                else ("partially_agreed" if has_worker else "insufficient_evidence")
            ),
            worker_id=worker_id,
            ttft_ms=ttft_ms,
            decode_ms=decode_ms,
            end_to_end_ms=end_to_end_ms,
        )

        stop_status = "agreed"
        stop_judgment = "Agent stopped in a way that is consistent with runtime/tool outcomes."
        if execute_failure:
            if "npm" in execute_failure.lower() and "not available" in response_text.lower():
                stop_status = "agreed"
                stop_judgment = "Agent acknowledged the runtime command failure and stopped consistently with that outcome."
            elif "npm" in execute_failure.lower():
                stop_status = "partially_agreed"
                stop_judgment = "Runtime returned a command failure, but the final response only partially reflected that failure."
        elif tool_call_count == 0:
            stop_status = "insufficient_evidence"
            stop_judgment = "No concrete tool or failure evidence was available to explain the stop behavior."

        add_row(
            rows,
            phase=phase,
            decision_type="stop_behavior",
            agent_component="deepagents_app",
            runtime_component="frontend_dynamo/sglang_worker",
            agent_side_decision="Produced a final response and ended the run.",
            runtime_side_response=(
                f"Runtime/tool outcome included execute failure: {execute_failure}"
                if execute_failure
                else f"Run ended with finish_reason={measurement.get('finish_reason') or '-'}."
            ),
            evidence=(
                f"finish_reason={measurement.get('finish_reason') or '-'}; "
                f"response_preview={_prompt_preview(response_text, 140)}"
            ),
            alignment_judgment=stop_judgment,
            agreement_status=stop_status,
            worker_id=worker_id,
            ttft_ms=ttft_ms,
            decode_ms=decode_ms,
            end_to_end_ms=end_to_end_ms,
        )

    return {
        "summary": {
            "decision_row_count": len(rows),
            "observed_worker_count": len(observed_workers),
            "observed_workers": sorted(observed_workers),
            "agreed_count": sum(1 for row in rows if row.get("agreement_status") == "agreed"),
            "partially_agreed_count": sum(
                1 for row in rows if row.get("agreement_status") == "partially_agreed"
            ),
            "diverged_count": sum(1 for row in rows if row.get("agreement_status") == "diverged"),
            "insufficient_evidence_count": sum(
                1 for row in rows if row.get("agreement_status") == "insufficient_evidence"
            ),
            "tool_parser_names_seen": tool_parser_usage["tool_parser_names_seen"],
            "observed_tool_call_names": observed_tool_call_names,
        },
        "rows": rows,
    }


def _runtime_hint_effect(
    hint_name: str,
    hint_value: Any,
    *,
    event: dict[str, Any],
    measurement: dict[str, Any],
) -> tuple[str, str, str]:
    cache = event.get("cache") or {}
    latency = event.get("latency") or {}
    scheduler = event.get("scheduler") or {}
    phase = event.get("phase")

    if hint_name == "hint_probe_id":
        return (
            "The probe marker was available for layer-by-layer propagation checks.",
            "probe_marker",
            f"hint_probe_id={hint_value}.",
        )

    if hint_name == "expected_output_tokens":
        completion_tokens = measurement.get("completion_tokens") or measurement.get("output_tokens")
        finish_reason = measurement.get("finish_reason")
        if isinstance(hint_value, int) and completion_tokens == hint_value and finish_reason == "length":
            return (
                "Completion stopped at the hinted token budget.",
                "behavior_supported",
                (
                    f"completion_tokens={completion_tokens}; finish_reason={finish_reason}. "
                    "This supports a token-budget effect, but does not by itself prove the worker used nvext.agent_hints directly."
                ),
            )
        if completion_tokens is not None:
            return (
                "Completion token count was recorded, but it did not prove the hint controlled generation.",
                "not_proven",
                f"completion_tokens={completion_tokens}; finish_reason={finish_reason or '-'}.",
            )
        return (
            "No completion token evidence was available for this hint.",
            "not_proven",
            "completion_tokens=-; finish_reason=-.",
        )

    if hint_name == "reuse_likelihood":
        cached_token_count = cache.get("cached_token_count")
        recomputed_prefix_tokens = cache.get("recomputed_prefix_tokens")
        if isinstance(cached_token_count, int) and cached_token_count > 0:
            return (
                "Cache reuse was observed for the request.",
                "behavior_supported",
                (
                    f"cached_token_count={cached_token_count}; "
                    f"recomputed_prefix_tokens={recomputed_prefix_tokens if recomputed_prefix_tokens is not None else '-'}. "
                    "This is consistent with the reuse hint, but not causal proof by itself."
                ),
            )
        return (
            "No cache reuse evidence was observed for this request.",
            "not_proven",
            f"cached_token_count={cached_token_count if cached_token_count is not None else '-'}.",
        )

    if hint_name == "priority":
        if scheduler:
            return (
                "The scheduler selected a worker, but no priority-specific decision was logged.",
                "not_proven",
                (
                    f"worker_id={event.get('worker_id') or '-'}; "
                    f"dp_rank={scheduler.get('dp_rank') if scheduler.get('dp_rank') is not None else '-'}; "
                    f"logit={scheduler.get('logit') if scheduler.get('logit') is not None else '-'}. "
                    "Priority needs queue/competition evidence to prove it was respected."
                ),
            )
        return (
            "No scheduler evidence was available to evaluate priority.",
            "not_proven",
            "scheduler=-.",
        )

    if hint_name == "latency_sensitivity":
        ttft_ms = latency.get("ttft_ms")
        end_to_end_ms = latency.get("end_to_end_ms")
        if ttft_ms is not None or end_to_end_ms is not None:
            return (
                "Latency was measured, but no latency policy decision was logged.",
                "not_proven",
                (
                    f"ttft_ms={ttft_ms if ttft_ms is not None else '-'}; "
                    f"end_to_end_ms={end_to_end_ms if end_to_end_ms is not None else '-'}. "
                    "Latency sensitivity needs routing or queue-policy evidence to prove it was respected."
                ),
            )
        return (
            "No latency evidence was available for this hint.",
            "not_proven",
            "ttft_ms=-; end_to_end_ms=-.",
        )

    if hint_name == "agent_phase":
        if phase == hint_value:
            return (
                "The phase label matched the runtime event phase.",
                "metadata_matched",
                f"event_phase={phase}; hint_agent_phase={hint_value}.",
            )
        return (
            "The phase label did not match the runtime event phase.",
            "not_proven",
            f"event_phase={phase or '-'}; hint_agent_phase={hint_value}.",
        )

    if hint_name in HINT_METADATA_ONLY:
        return (
            "This hint is treated as trace metadata, not a worker behavior instruction.",
            "metadata_only",
            "metadata-only hint; no runtime effect expected unless a component explicitly consumes it.",
        )

    return (
        "No runtime-effect rule has been defined for this hint yet.",
        "not_proven",
        "effect_rule=-.",
    )


def build_runtime_hint_alignment_analysis(
    runtime_events: list[dict],
    baseline_result: dict,
    runtime_log_artifacts: dict[str, Any],
) -> dict:
    frontend_log_summary = _runtime_hint_log_summary(
        runtime_log_artifacts.get("frontend_log_file")
        if isinstance(runtime_log_artifacts.get("frontend_log_file"), str)
        else None
    )
    worker_log_summary = _runtime_hint_log_summary(
        runtime_log_artifacts.get("worker_log_file")
        if isinstance(runtime_log_artifacts.get("worker_log_file"), str)
        else None
    )
    measurement = baseline_result.get("measurement", {})

    rows: list[dict[str, Any]] = []
    for event in runtime_events:
        request_hints = event.get("request_hints")
        if not isinstance(request_hints, dict) or not request_hints:
            request_hints = baseline_result.get("baseline_hints")
        if not isinstance(request_hints, dict) or not request_hints:
            continue

        for hint_name in sorted(key for key in request_hints if not str(key).startswith("_")):
            hint_value = request_hints[hint_name]
            request_wrapper_observed = (
                isinstance(event.get("request_hints"), dict)
                and hint_name in event.get("request_hints", {})
            )
            frontend_observed = _hint_observed(frontend_log_summary, hint_name, hint_value)
            worker_observed = _hint_observed(worker_log_summary, hint_name, hint_value)
            frontend_state = _hint_component_state(frontend_log_summary, hint_name, hint_value)
            worker_state = _hint_component_state(worker_log_summary, hint_name, hint_value)
            effect_text, effect_status, effect_evidence = _runtime_hint_effect(
                hint_name,
                hint_value,
                event=event,
                measurement=measurement,
            )

            if hint_name == "hint_probe_id" and request_wrapper_observed:
                if worker_observed:
                    claim_level = "probe_observed_by_worker"
                    status = "observed_by_worker"
                elif frontend_observed:
                    claim_level = "probe_observed_by_frontend"
                    status = "observed_by_frontend"
                else:
                    claim_level = "probe_present_request_only"
                    status = "request_only"
            elif effect_status in {"behavior_supported", "metadata_matched", "metadata_only"}:
                if worker_observed:
                    claim_level = f"observed_by_worker_plus_{effect_status}"
                elif frontend_observed:
                    claim_level = f"observed_by_frontend_plus_{effect_status}"
                else:
                    claim_level = effect_status
                status = effect_status
            elif worker_observed:
                claim_level = "observed_by_worker"
                status = "observed_by_worker"
            elif frontend_observed:
                claim_level = "observed_by_frontend"
                status = "observed_by_frontend"
            elif request_wrapper_observed:
                claim_level = "propagated_to_request"
                status = "not_proven"
            else:
                claim_level = effect_status
                status = effect_status

            rows.append(
                {
                    "phase": event.get("phase"),
                    "hint_name": hint_name,
                    "hint_value_sent": hint_value,
                    "hint_source": "AgentBench Runner -> Deep Agents Request Wrapper",
                    "request_wrapper_observed": request_wrapper_observed,
                    "dynamo_frontend_observed": frontend_observed,
                    "dynamo_frontend_state": frontend_state,
                    "sglang_worker_observed": worker_observed,
                    "sglang_worker_state": worker_state,
                    "expected_runtime_effect": HINT_RUNTIME_EXPECTATIONS.get(
                        hint_name,
                        "No expected runtime effect has been defined for this hint.",
                    ),
                    "observed_runtime_effect": effect_text,
                    "claim_level": claim_level,
                    "status": status,
                    "evidence": (
                        f"request_wrapper_observed={request_wrapper_observed}; "
                        f"dynamo_frontend_state={frontend_state}; "
                        f"sglang_worker_state={worker_state}; {effect_evidence}"
                    ),
                }
            )

    probe_row = next((row for row in rows if row.get("hint_name") == "hint_probe_id"), None)
    summary = {
        "hint_row_count": len(rows),
        "propagated_count": sum(1 for row in rows if row.get("request_wrapper_observed")),
        "frontend_observed_count": sum(1 for row in rows if row.get("dynamo_frontend_observed")),
        "worker_observed_count": sum(1 for row in rows if row.get("sglang_worker_observed")),
        "behavior_supported_count": sum(
            1 for row in rows if row.get("status") == "behavior_supported"
        ),
        "metadata_matched_count": sum(1 for row in rows if row.get("status") == "metadata_matched"),
        "metadata_only_count": sum(1 for row in rows if row.get("status") == "metadata_only"),
        "not_proven_count": sum(1 for row in rows if row.get("status") == "not_proven"),
        "direct_sglang_hint_evidence": any(row.get("sglang_worker_observed") for row in rows),
        "hint_probe_id": probe_row.get("hint_value_sent") if probe_row else None,
        "probe_status": probe_row.get("status") if probe_row else "missing",
        "probe_request_wrapper_observed": bool(probe_row and probe_row.get("request_wrapper_observed")),
        "probe_frontend_observed": bool(probe_row and probe_row.get("dynamo_frontend_observed")),
        "probe_worker_observed": bool(probe_row and probe_row.get("sglang_worker_observed")),
        "frontend_runtime_json_event_count": frontend_log_summary.get("runtime_json_event_count"),
        "frontend_agent_hints_non_null_count": frontend_log_summary.get("agent_hints_non_null_count"),
        "frontend_agent_hints_sources": frontend_log_summary.get("agent_hints_sources"),
        "worker_runtime_json_event_count": worker_log_summary.get("runtime_json_event_count"),
        "worker_agent_hints_null_count": worker_log_summary.get("agent_hints_null_count"),
        "worker_agent_hints_non_null_count": worker_log_summary.get("agent_hints_non_null_count"),
        "worker_agent_hints_sources": worker_log_summary.get("agent_hints_sources"),
    }
    return {
        "summary": summary,
        "notes": [
            "This report separates hint propagation from proof that the runtime respected a hint.",
            "A hint can be behavior-supported even when direct SGLang worker hint evidence is missing, but that is not causal proof.",
            "Hints such as agent_phase, program_id, and context_type are treated as trace metadata unless a runtime component explicitly consumes them.",
        ],
        "rows": rows,
    }


def render_runtime_alignment_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    rows = analysis["rows"]
    lines = [
        "# Runtime Alignment Analysis",
        "",
        "## Summary",
        *markdown_field_table(
            summary,
            "runtime_alignment_analysis",
            [
                ("decision_row_count", "Decision rows"),
                ("observed_worker_count", "Observed worker count"),
                ("observed_workers", "Observed workers"),
                ("agreed_count", "Agreed rows"),
                ("partially_agreed_count", "Partially-agreed rows"),
                ("diverged_count", "Diverged rows"),
                ("insufficient_evidence_count", "Insufficient-evidence rows"),
                ("tool_parser_names_seen", "Tool parser names seen"),
                ("observed_tool_call_names", "Observed tool call names"),
            ],
            include_provenance=False,
        ),
        "",
        "## Notes",
        "- This report compares major Deep Agents decisions with the frontend and SGLang worker response observed in runtime evidence.",
        "- Each row represents one decision point, the runtime-side reaction, the evidence we saw, and a short judgment of agreement or divergence.",
        "",
        "## Decision Table",
        "",
        "| Phase | Decision type | Agent component | Runtime component | Agent-side decision | Runtime-side response | Evidence | Judgment | Status | Worker | TTFT (ms) | Decode (ms) | End to end (ms) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {phase} | {decision_type} | {agent_component} | {runtime_component} | {agent_decision} | {runtime_response} | {evidence} | {judgment} | {status} | {worker} | {ttft} | {decode} | {e2e} |".format(
                phase=markdown_value(row.get("phase")),
                decision_type=markdown_value(row.get("decision_type")),
                agent_component=markdown_value(row.get("agent_component")),
                runtime_component=markdown_value(row.get("runtime_component")),
                agent_decision=markdown_value(row.get("agent_side_decision")),
                runtime_response=markdown_value(row.get("runtime_side_response")),
                evidence=markdown_value(row.get("evidence")),
                judgment=markdown_value(row.get("alignment_judgment")),
                status=markdown_value(row.get("agreement_status")),
                worker=markdown_value(row.get("worker_id")),
                ttft=markdown_value(row.get("ttft_ms")),
                decode=markdown_value(row.get("decode_ms")),
                e2e=markdown_value(row.get("end_to_end_ms")),
            )
        )
    return "\n".join(lines) + "\n"


def render_runtime_hint_alignment_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    rows = analysis["rows"]
    lines = [
        "# Runtime Hint Alignment Analysis",
        "",
        "## Summary",
        *markdown_field_table(
            summary,
            "runtime_hint_alignment_analysis",
            [
                ("hint_row_count", "Hint rows"),
                ("propagated_count", "Hints present in request wrapper events"),
                ("frontend_observed_count", "Hints directly observed in Dynamo frontend logs"),
                ("worker_observed_count", "Hints directly observed in SGLang worker logs"),
                ("behavior_supported_count", "Hints with behavior-supported evidence"),
                ("metadata_matched_count", "Metadata hints that matched trace context"),
                ("metadata_only_count", "Metadata-only hints"),
                ("not_proven_count", "Hints not proven to affect runtime behavior"),
                ("direct_sglang_hint_evidence", "Direct SGLang hint evidence"),
                ("hint_probe_id", "Hint probe id"),
                ("probe_status", "Probe status"),
                ("probe_request_wrapper_observed", "Probe seen in request wrapper"),
                ("probe_frontend_observed", "Probe seen in Dynamo frontend logs"),
                ("probe_worker_observed", "Probe seen in SGLang worker logs"),
                ("frontend_agent_hints_sources", "Dynamo frontend hint sources"),
                ("worker_agent_hints_sources", "SGLang worker hint sources"),
                ("worker_agent_hints_null_count", "Worker log events with null agent_hints"),
                ("worker_agent_hints_non_null_count", "Worker log events with non-null agent_hints"),
            ],
            include_provenance=False,
        ),
        "",
        "## Notes",
        "- This report checks whether AgentBench hints were sent, observed by runtime logs, and supported by behavior evidence.",
        "- Propagation is not the same as proof that SGLang used a hint.",
        "- Worker-side proof requires SGLang logs to show non-null agent_hints or explicit runtime fields derived from the hints.",
        "",
        "## Probe Layer Check",
        "",
        "| Layer | Did the probe appear? |",
        "| --- | --- |",
        f"| AgentBench / Request Wrapper | {markdown_value(summary.get('probe_request_wrapper_observed'))} |",
        f"| Dynamo Frontend Logs | {markdown_value(summary.get('probe_frontend_observed'))} |",
        f"| SGLang Worker Logs | {markdown_value(summary.get('probe_worker_observed'))} |",
        "",
        "## Hint Table",
        "",
        "| Phase | Hint | Value sent | Request wrapper | Dynamo frontend | SGLang worker | Expected effect | Observed effect | Claim level | Status | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {phase} | {hint} | {value} | {wrapper} | {frontend} | {worker} | {expected} | {observed} | {claim} | {status} | {evidence} |".format(
                phase=markdown_value(row.get("phase")),
                hint=markdown_value(row.get("hint_name")),
                value=markdown_value(row.get("hint_value_sent")),
                wrapper=markdown_value(row.get("request_wrapper_observed")),
                frontend=markdown_value(row.get("dynamo_frontend_state")),
                worker=markdown_value(row.get("sglang_worker_state")),
                expected=markdown_value(row.get("expected_runtime_effect")),
                observed=markdown_value(row.get("observed_runtime_effect")),
                claim=markdown_value(row.get("claim_level")),
                status=markdown_value(row.get("status")),
                evidence=markdown_value(row.get("evidence")),
            )
        )
    return "\n".join(lines) + "\n"


def render_measurement_analysis_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    rows = analysis["rows"]
    lines = [
        "# Measurement Analysis",
        "",
        "## Summary",
        *markdown_field_table(
            summary,
            "measurement_analysis",
            [
                ("most_prefill_heavy_phase", "Most prefill-heavy phase"),
                ("strongest_reuse_phase", "Strongest reuse phase"),
                ("highest_pressure_phase", "Highest pressure phase"),
                ("highest_pressure_risk", "Highest pressure risk"),
                ("slowest_phase", "Slowest phase"),
                ("slowest_phase_latency_ms", "Slowest phase latency (ms)"),
            ],
        ),
        "",
        "## Phase Table",
        "",
        "| Phase | Phase provenance | Step | Step provenance | Latency (ms) | Latency provenance | Input tokens | Input provenance | Output tokens | Output provenance | Cached input | Cached-input provenance | Finish | Finish provenance | Profile | Profile provenance | Reuse | Reuse provenance | Pressure | Pressure provenance |",
        "| --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        annotated = row_with_provenance(dict(row), "measurement_analysis")
        lines.append(
            "| {phase} | {phase_p} | {step} | {step_p} | {latency} | {latency_p} | {input_tokens} | {input_p} | {output_tokens} | {output_p} | {cached_input_tokens} | {cached_input_p} | {finish_reason} | {finish_p} | {profile} | {profile_p} | {reuse} | {reuse_p} | {pressure} | {pressure_p} |".format(
                phase=markdown_value(annotated.get("phase")),
                phase_p=annotated.get("phase_provenance", "-"),
                step=markdown_value(annotated.get("step_index")),
                step_p=annotated.get("step_index_provenance", "-"),
                latency=markdown_value(annotated.get("latency_ms")),
                latency_p=annotated.get("latency_ms_provenance", "-"),
                input_tokens=markdown_value(annotated.get("input_tokens")),
                input_p=annotated.get("input_tokens_provenance", "-"),
                output_tokens=markdown_value(annotated.get("output_tokens")),
                output_p=annotated.get("output_tokens_provenance", "-"),
                cached_input_tokens=markdown_value(annotated.get("cached_input_tokens")),
                cached_input_p=annotated.get("cached_input_tokens_provenance", "-"),
                finish_reason=markdown_value(annotated.get("finish_reason")),
                finish_p=annotated.get("finish_reason_provenance", "-"),
                profile=markdown_value(annotated.get("prefill_decode_profile")),
                profile_p=annotated.get("prefill_decode_profile_provenance", "-"),
                reuse=markdown_value(annotated.get("reuse_signal")),
                reuse_p=annotated.get("reuse_signal_provenance", "-"),
                pressure=markdown_value(annotated.get("pressure_risk")),
                pressure_p=annotated.get("pressure_risk_provenance", "-"),
            )
        )
    return "\n".join(lines) + "\n"


def stringify_unknown(value):
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:  # noqa: BLE001
            pass
    if hasattr(value, "dict"):
        try:
            return value.dict()
        except Exception:  # noqa: BLE001
            pass
    return repr(value)


def _prompt_preview(text: str | None, limit: int = 240) -> str:
    """Create a short single-line preview for long prompt or response text."""
    if not text:
        return ""
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


RUN_SLUG_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def slugify_piece(value: Any, *, max_words: int | None = None, max_chars: int = 48) -> str:
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z0-9]+", str(value or ""))
        if word and word.lower() not in RUN_SLUG_STOPWORDS
    ]
    if max_words is not None:
        words = words[:max_words]
    slug = "-".join(words).strip("-")
    if not slug:
        return ""
    return slug[:max_chars].strip("-")


def result_directory_name(task: dict[str, Any], *, run_id: str, index: int) -> str:
    del task, index
    return f"agentbench-{run_id}"


def unique_result_directory(base_name: str) -> Path:
    candidate = RESULTS_DIR / base_name
    if not candidate.exists():
        return candidate
    for suffix in range(2, 1000):
        candidate = RESULTS_DIR / f"{base_name}_{suffix:02d}"
        if not candidate.exists():
            return candidate
    raise SystemExit(f"Could not find an unused result directory name for: {base_name}")


def prepare_workspace(
    *,
    run_dir: Path,
    repo_path: str | None,
    repo_url: str | None,
    checkout_commit: str | None = None,
    inferred_from_task: bool = False,
    shared_repo_source: Path | None = None,
    clean_shared_checkout: bool = True,
) -> tuple[Path | None, dict]:
    # [CHECK_POINT 2] A writable repo workspace for the agent is prepared here.
    # Debugging note: this wrapper supports three workspace modes:
    # 1. explicit local repo path
    # 2. explicit remote repo URL
    # 3. automatic SWE-bench shared checkout under agentbench/repos/
    if not repo_path and not repo_url:
        return None, {"workspace_mode": "none"}

    workspace_dir = run_dir / "workspace"
    metadata: dict[str, str] = {"workspace_mode": "none"}

    if repo_path:
        source_repo = Path(repo_path).expanduser().resolve()
        if not source_repo.exists():
            raise SystemExit(f"--repo-path does not exist: {source_repo}")
        try:
            run_command(["git", "clone", "--no-hardlinks", str(source_repo), str(workspace_dir)])
            metadata = {
                "workspace_mode": "local_clone",
                "source_repo_path": str(source_repo),
                "workspace_path": str(workspace_dir),
            }
        except Exception:  # noqa: BLE001
            shutil.copytree(source_repo, workspace_dir, dirs_exist_ok=True)
            git_dir = workspace_dir / ".git"
            if not git_dir.exists():
                metadata = {
                    "workspace_mode": "local_copy_non_git",
                    "source_repo_path": str(source_repo),
                    "workspace_path": str(workspace_dir),
                }
            else:
                metadata = {
                    "workspace_mode": "local_copy_git_repo",
                    "source_repo_path": str(source_repo),
                    "workspace_path": str(workspace_dir),
                }
        if checkout_commit and (workspace_dir / ".git").exists():
            checkout_metadata = git_checkout_with_fetch_repair(workspace_dir, checkout_commit)
            metadata["checked_out_commit"] = checkout_commit
            metadata["checkout_metadata"] = checkout_metadata
        return workspace_dir, metadata

    if shared_repo_source is not None:
        # Debugging note: automatic SWE-bench runs operate directly inside a shared checkout.
        # Clean it by default so generated files from previous tasks cannot leak into this run.
        clean_metadata: dict[str, object] = {"cleaned": False}
        if clean_shared_checkout:
            clean_metadata = clean_git_checkout(shared_repo_source)
        if checkout_commit:
            checkout_metadata = git_checkout_with_fetch_repair(shared_repo_source, checkout_commit)
        else:
            checkout_metadata = {"checked_out": False, "repair_needed": False, "attempts": []}
        metadata = {
            "workspace_mode": "shared_checkout_in_place",
            "source_repo_url": repo_url,
            "workspace_path": str(shared_repo_source),
            "shared_repo_path": str(shared_repo_source),
            "clean_shared_checkout": clean_shared_checkout,
            "clean_metadata": clean_metadata,
            "checkout_metadata": checkout_metadata,
        }
        if checkout_commit:
            metadata["checked_out_commit"] = checkout_commit
        return shared_repo_source, metadata

    assert repo_url is not None
    run_command(["git", "clone", "--no-hardlinks", repo_url, str(workspace_dir)])
    metadata = {
        "workspace_mode": "auto_remote_clone" if inferred_from_task else "remote_clone",
        "source_repo_url": repo_url,
        "workspace_path": str(workspace_dir),
    }
    if checkout_commit:
        checkout_metadata = git_checkout_with_fetch_repair(workspace_dir, checkout_commit)
        metadata["checked_out_commit"] = checkout_commit
        metadata["checkout_metadata"] = checkout_metadata
    return workspace_dir, metadata


def collect_workspace_artifacts(
    report_dir: Path,
    workspace_dir: Path | None,
    *,
    auxiliary_dir: Path | None = None,
) -> dict:
    # [CHECK_POINT 6] Git patch and workspace artifacts are captured here.
    # Debugging note: this is where repo-aware runs become benchmark artifacts:
    # patch file, git status, git diff stat, and workspace metadata.
    if workspace_dir is None:
        return {"workspace_present": False}

    artifacts: dict[str, object] = {
        "workspace_present": True,
        "workspace_path": str(workspace_dir),
        "git_repo": False,
    }
    git_dir = workspace_dir / ".git"
    if not git_dir.exists():
        return artifacts

    artifacts["git_repo"] = True
    status = run_command(["git", "status", "--short"], cwd=workspace_dir, check=False)
    untracked = run_command(["git", "ls-files", "--others", "--exclude-standard"], cwd=workspace_dir, check=False)
    untracked_files = [line for line in untracked.stdout.splitlines() if line.strip()]
    if untracked_files:
        # Mark untracked files intent-to-add so `git diff` emits a real patch for new files.
        run_command(["git", "add", "-N", "--", *untracked_files], cwd=workspace_dir, check=False)
    diff = run_command(["git", "diff", "--binary"], cwd=workspace_dir, check=False)
    diff_stat = run_command(["git", "diff", "--stat"], cwd=workspace_dir, check=False)
    if untracked_files:
        run_command(["git", "reset", "-q", "--", *untracked_files], cwd=workspace_dir, check=False)
    head = run_command(["git", "rev-parse", "HEAD"], cwd=workspace_dir, check=False)

    artifact_dir = auxiliary_dir or report_dir
    patch_path = report_dir / "workspace.patch"
    patch_path.write_text(diff.stdout, encoding="utf-8")
    legacy_patch_path = artifact_dir / "workspace.patch"
    if legacy_patch_path != patch_path and legacy_patch_path.exists():
        legacy_patch_path.unlink()
    (artifact_dir / "git_status.txt").write_text(status.stdout, encoding="utf-8")
    (artifact_dir / "git_diff_stat.txt").write_text(diff_stat.stdout, encoding="utf-8")
    (artifact_dir / "git_untracked_files.txt").write_text(untracked.stdout, encoding="utf-8")

    artifacts.update(
        {
            "git_head": head.stdout.strip(),
            "git_status": status.stdout,
            "git_diff_stat": diff_stat.stdout,
            "git_untracked_files": untracked.stdout,
            "patch_file": str(patch_path),
            "patch_nonempty": bool(diff.stdout.strip()),
        }
    )
    return artifacts


def resolve_agent_hints(*, hint_profile: str, hint_json: str) -> dict[str, object]:
    try:
        hint_overrides = json.loads(hint_json or "{}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--hint-json must be a JSON object: {exc}") from exc
    if not isinstance(hint_overrides, dict):
        raise SystemExit("--hint-json must be a JSON object.")

    profile_values = HINT_PROFILES.get(hint_profile)
    if profile_values is None:
        raise SystemExit(f"Unknown --hint-profile {hint_profile!r}. Choose one of: {', '.join(sorted(HINT_PROFILES))}")

    hints: dict[str, object] = dict(DEFAULT_HINTS)
    hints.update(profile_values)
    hints.update(hint_overrides)
    hints["hint_profile"] = hint_profile
    return hints


def env_flag(name: str, *, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def resolve_host_path(path: Path | str) -> Path:
    resolved = Path(path).expanduser()
    if resolved.is_absolute():
        return resolved
    return REPO_ROOT / resolved


def default_sglang_transfer_log_dir() -> Path:
    return resolve_host_path(
        os.environ.get(
            "SGLANG_TRANSFER_LOG_DIR",
            str(REPO_ROOT / "experiments/raw/sglang_transfer_logs"),
        )
    )


def resolve_sglang_transfer_log(
    *,
    explicit_log: Path | None,
    run_started_at: datetime,
) -> Path | None:
    if explicit_log is not None:
        return resolve_host_path(explicit_log)

    log_dir = default_sglang_transfer_log_dir()
    env_log_path = os.environ.get("SGLANG_TRANSFER_LOG_PATH")
    candidates: list[Path] = []
    if env_log_path:
        if env_log_path.startswith("/transfer-logs/"):
            candidates.append(log_dir / Path(env_log_path).name)
        else:
            candidates.append(resolve_host_path(env_log_path))

    latest_link = log_dir / "latest_sglang_transfer_events.jsonl"
    if latest_link.exists() or latest_link.is_symlink():
        candidates.append(latest_link)

    if log_dir.exists():
        candidates.extend(
            sorted(
                log_dir.glob("sglang_transfer_events*.jsonl"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        )

    run_started_epoch = run_started_at.timestamp()
    for candidate in candidates:
        if candidate.is_symlink() and not candidate.exists():
            return candidate
        if not candidate.exists():
            continue
        try:
            if candidate.stat().st_mtime + 5 >= run_started_epoch:
                return candidate
        except OSError:
            continue
    return None


def build_curated_run_report(
    *,
    run_dir: Path,
    parent_run_id: str,
    transfer_log: Path | None,
) -> dict[str, object]:
    report_script = REPO_ROOT / "experiments/scripts/agentbench_report/build_run_report.py"
    if not report_script.exists():
        return {
            "enabled": True,
            "success": False,
            "reason": "report_script_missing",
            "report_script": str(report_script),
        }

    selected_transfer_log = transfer_log or (run_dir / "others/sglang_transfer_log_not_found.jsonl")
    command = [
        sys.executable,
        str(report_script),
        "--agentbench-result-dir",
        str(run_dir),
        "--transfer-log",
        str(selected_transfer_log),
        "--run-id",
        parent_run_id,
    ]
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    report_dir = REPO_ROOT / "experiments/reports/runs" / parent_run_id
    return {
        "enabled": True,
        "success": completed.returncode == 0,
        "exit_code": completed.returncode,
        "command": command,
        "transfer_log": str(selected_transfer_log),
        "report_dir": str(report_dir),
        "summary_file": str(report_dir / "run_overview.md"),
        "run_metrics_file": str(report_dir / "runtime_metrics.json"),
        "latest_runs_overview_file": str(REPO_ROOT / "experiments/reports/latest_runs_overview.md"),
        "all_runs_overview_file": str(REPO_ROOT / "experiments/reports/all_runs_overview.csv"),
        "latest_runs_execution_prompts_file": str(REPO_ROOT / "experiments/reports/latest_runs_execution_prompts.md"),
        "all_runs_execution_prompts_file": str(REPO_ROOT / "experiments/reports/all_runs_execution_prompts.csv"),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> None:
    # Debugging note: main() is the wrapper entry point.
    # It is responsible for the outer pipeline:
    # load task -> choose workspace -> call Deep Agents app -> save artifacts.
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="ScaleAI/SWE-bench_Pro")
    parser.add_argument("--split", default="test")
    parser.add_argument("--csv-path")
    parser.add_argument("--json-path")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--instance-id")
    parser.add_argument(
        "--repo-path",
        help="Local repo checkout to clone into the run workspace before invoking the agent.",
    )
    parser.add_argument(
        "--repo-url",
        help="Remote git URL to clone into the run workspace before invoking the agent.",
    )
    parser.add_argument(
        "--no-auto-repo-checkout",
        action="store_true",
        help="Disable automatic GitHub repo clone + base-commit checkout for SWE-bench dataset tasks.",
    )
    parser.add_argument(
        "--keep-shared-workspace-changes",
        action="store_true",
        help=(
            "Do not reset/clean the automatic shared checkout before a run. "
            "Use only when deliberately debugging a dirty workspace."
        ),
    )
    parser.add_argument(
        "--frontend-url",
        default="http://127.0.0.1:8000/v1/chat/completions",
    )
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B")
    parser.add_argument(
        "--app-variant",
        default="local",
        choices=["local", "upstream_deploy_coding_agent"],
        help="Choose whether to run the local Deep Agents app or the cloned upstream deploy-coding-agent instructions/skills.",
    )
    parser.add_argument(
        "--hint-profile",
        default="baseline",
        choices=sorted(HINT_PROFILES),
        help="Named AgentBench hint profile for repeatable cache/scheduling experiments.",
    )
    parser.add_argument(
        "--hint-provider",
        default=os.environ.get("AGENTBENCH_HINT_PROVIDER", HINT_PROVIDER_AGENTBENCH),
        choices=HINT_PROVIDERS,
        help=(
            "Choose who produces nvext.agent_hints: agentbench uses the selected "
            "profile, deepagents derives deterministic hints from runtime phase "
            "state, none sends request context without agent hints."
        ),
    )
    parser.add_argument(
        "--hint-json",
        default="{}",
        help="JSON object merged on top of the selected --hint-profile before sending nvext.agent_hints.",
    )
    parser.add_argument(
        "--results-timezone",
        default=DEFAULT_RESULTS_TIMEZONE,
    )
    parser.add_argument(
        "--step-limit",
        type=int,
        default=4,
        help="Maximum number of explicit decomposition steps to dispatch.",
    )
    parser.add_argument(
        "--prompt-evolution-value-char-limit",
        type=int,
        default=1000,
        help=(
            "Character cap for string values inside per-stage prompt evolution before/after payloads. "
            "Long string fields are truncated with '...'."
        ),
    )
    parser.add_argument(
        "--no-run-report",
        action="store_true",
        help="Disable automatic curated report generation at the end of the run.",
    )
    parser.add_argument(
        "--quiet-checkpoints",
        action="store_true",
        help="Do not print # [CHECK_POINT] blocks to the terminal; checkpoint artifacts are still written.",
    )
    parser.add_argument(
        "--sglang-transfer-log",
        type=Path,
        default=None,
        help="Specific SGLang transfer JSONL to use in the automatic curated report.",
    )
    args = parser.parse_args()
    args.hint_provider = normalize_hint_provider(args.hint_provider)
    if args.quiet_checkpoints:
        os.environ["AGENTBENCH_PRINT_CHECKPOINTS"] = "0"

    results_tz = ZoneInfo(args.results_timezone)
    run_started_at = datetime.now(results_tz)
    run_id = run_started_at.strftime("%Y%m%d_%H%M%S")

    task_source = task_source_label(
        dataset_name=args.dataset,
        split=args.split,
        csv_path=args.csv_path,
        json_path=args.json_path,
    )
    task = load_swebench_task(
        dataset_name=args.dataset,
        split=args.split,
        csv_path=args.csv_path,
        json_path=args.json_path,
        index=args.index,
        instance_id=args.instance_id,
    )
    legacy_instance_slug = str(task.get("instance_id", f"task_{args.index}")).replace("/", "__")
    parent_run_id_base = result_directory_name(task, run_id=run_id, index=args.index)
    run_dir = unique_result_directory(parent_run_id_base)
    parent_run_id = run_dir.name
    run_dir.mkdir(parents=True, exist_ok=True)
    others_dir = run_dir / "others"
    others_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_log_path = others_dir / "checkpoints.json"
    lifecycle_log_path = others_dir / "stage_lifecycle_trace_raw.json"
    set_checkpoint_log_file(checkpoint_log_path)
    set_lifecycle_log_file(lifecycle_log_path)
    log_lifecycle_event(
        stage="run_initialized",
        payload={
            "event_kind": "workflow",
            "parent_run_id": parent_run_id,
            "task_index": args.index,
            "task_source": task_source,
            "app_variant": args.app_variant,
            "frontend_url": args.frontend_url,
            "model": args.model,
            "dataset": args.dataset,
            "split": args.split,
            "instance_id": task.get("instance_id"),
            "hint_profile": args.hint_profile,
            "hint_provider": args.hint_provider,
            "results_timezone": args.results_timezone,
            "step_limit": args.step_limit,
            "run_started_at": run_started_at.isoformat(),
        },
    )
    log_lifecycle_event(
        stage="task_retrieved",
        payload={
            "event_kind": "task_state",
            "parent_run_id": parent_run_id,
            "task_source": task_source,
            "task_index": args.index,
            "task": task,
        },
    )
    # [CHECK_POINT 1] SWE-bench task loaded before entering the Deep Agents harness.
    # [CHECK_POINT 1] Normalized task payload logged here before prompt expansion.
    log_checkpoint(
        check_point="1. SWE-bench task loaded before Deep Agents harness",
        task_index=args.index,
        payload={
            "task_source": task_source,
            "parent_run_id": parent_run_id,
            "app_variant": args.app_variant,
            "task": task,
        },
    )

    # Debugging note: this block is the automatic SWE-bench repo materialization decision.
    # If the task came from the dataset and no manual repo override was passed,
    # the wrapper will infer a GitHub repo + commit from the task metadata.
    auto_repo_checkout = {
        "enabled": False,
        "repo_url": None,
        "checkout_commit": None,
        "used": False,
    }
    repo_path = args.repo_path
    repo_url = args.repo_url
    inferred_checkout_commit: str | None = None
    inferred_from_task = False
    shared_repo_source: Path | None = None
    if (
        not args.no_auto_repo_checkout
        and repo_path is None
        and repo_url is None
        and should_auto_materialize_swebench_repo(
            dataset_name=args.dataset,
            csv_path=args.csv_path,
            json_path=args.json_path,
        )
    ):
        inferred_repo_url = infer_swebench_repo_url(task)
        inferred_checkout_commit = infer_swebench_base_commit(task)
        auto_repo_checkout = {
            "enabled": True,
            "repo_url": inferred_repo_url,
            "checkout_commit": inferred_checkout_commit,
            "used": bool(inferred_repo_url),
        }
        if inferred_repo_url:
            repo_url = inferred_repo_url
            inferred_from_task = True
            shared_repo_source = ensure_shared_repo_checkout(inferred_repo_url)
    log_lifecycle_event(
        stage="auto_repo_checkout_evaluated",
        payload={
            "event_kind": "workspace",
            "parent_run_id": parent_run_id,
            "task_source": task_source,
            "auto_repo_checkout": auto_repo_checkout,
            "repo_path": repo_path,
            "repo_url": repo_url,
            "inferred_from_task": inferred_from_task,
            "shared_repo_source": str(shared_repo_source) if shared_repo_source is not None else None,
        },
    )

    workspace_dir, workspace_metadata = prepare_workspace(
        run_dir=run_dir,
        repo_path=repo_path,
        repo_url=repo_url,
        checkout_commit=inferred_checkout_commit if inferred_from_task else None,
        inferred_from_task=inferred_from_task,
        shared_repo_source=shared_repo_source,
        clean_shared_checkout=not args.keep_shared_workspace_changes,
    )
    log_lifecycle_event(
        stage="workspace_prepared",
        payload={
            "event_kind": "workspace",
            "parent_run_id": parent_run_id,
            "workspace": workspace_metadata,
            "workspace_dir": str(workspace_dir) if workspace_dir is not None else None,
        },
    )
    task = dict(task)
    if workspace_dir is not None:
        task["workspace_path"] = str(workspace_dir)
        log_lifecycle_event(
            stage="workspace_path_attached_to_task",
            payload={
                "event_kind": "task_state",
                "parent_run_id": parent_run_id,
                "workspace_path": str(workspace_dir),
                "task": task,
            },
        )

    base_hints = resolve_agent_hints(hint_profile=args.hint_profile, hint_json=args.hint_json)
    if "hint_probe_id" not in base_hints:
        base_hints["hint_probe_id"] = f"{parent_run_id}::hint_probe"
    log_lifecycle_event(
        stage="workflow_invocation_started",
        payload={
            "event_kind": "workflow",
            "parent_run_id": parent_run_id,
            "task_source": task_source,
            "hint_profile": args.hint_profile,
            "hint_provider": args.hint_provider,
            "base_hints": base_hints,
            "app_variant": args.app_variant,
        },
    )
    try:
        workflow = run_task_workflow(
            # Debugging note: this is the exact hand-off from the outer wrapper
            # into the Deep Agents app layer.
            frontend_url=args.frontend_url,
            model=args.model,
            task=task,
            base_hints=base_hints,
            step_limit=args.step_limit,
            workspace_dir=workspace_dir,
            app_variant=args.app_variant,
            task_index=args.index,
            task_source=task_source,
            parent_run_id=parent_run_id,
            hint_provider=args.hint_provider,
        )
    except Exception as exc:
        if not (recursion_soft_stop_enabled() and is_recursion_limit_error(exc)):
            raise
        write_recursion_soft_stop_result(
            run_started_at=run_started_at,
            parent_run_id=parent_run_id,
            legacy_instance_slug=legacy_instance_slug,
            args=args,
            task=task,
            task_source=task_source,
            base_hints=base_hints,
            auto_repo_checkout=auto_repo_checkout,
            workspace_metadata=workspace_metadata,
            checkpoint_log_path=checkpoint_log_path,
            lifecycle_log_path=lifecycle_log_path,
            others_dir=others_dir,
            exc=exc,
        )
        print(f"AgentBench run recursion_soft_stop: {parent_run_id}")
        print(f"Run directory: {run_dir}")
        print(f"Result file: {others_dir / 'result.json'}")
        print(f"Soft-stop file: {others_dir / 'soft_stop.json'}")
        print(f"GraphRecursionError: {exc}", file=sys.stderr)
        raise SystemExit(RECURSION_SOFT_STOP_EXIT_CODE) from exc
    log_lifecycle_event(
        stage="workflow_invocation_completed",
        payload={
            "event_kind": "workflow",
            "parent_run_id": parent_run_id,
            "task_source": task_source,
            "measurement_count": len(workflow["measurements"]),
            "step_count": len(workflow["step_results"]),
            "final_response_preview": workflow["result"]["response_text"][:300],
        },
    )
    prompt = workflow["prompt"]
    decomposition_plan = workflow["decomposition_plan"]
    plan_file = write_json_artifact(others_dir, "plan.json", decomposition_plan, "plan")
    log_artifact_written_event(artifact_name="plan", artifact_path=plan_file, related_phase="planning")

    step_results = workflow["step_results"]
    step_results_report = strip_provenance(step_results)
    step_results_file = write_json_artifact(
        run_dir,
        "step_results.json",
        step_results_report,
        "step_results",
        annotate=False,
    )
    log_artifact_written_event(artifact_name="step_results", artifact_path=step_results_file)
    execution_loop_trace = workflow.get("execution_loop_trace") or {}
    execution_loop_trace_file = write_json_artifact(
        others_dir,
        "execution_loop_trace.json",
        execution_loop_trace,
        "execution_loop_trace",
    )
    log_artifact_written_event(artifact_name="execution_loop_trace", artifact_path=execution_loop_trace_file)
    execution_loop_table = build_execution_loop_table(execution_loop_trace)
    execution_loop_table_file = write_csv_table(
        others_dir,
        "execution_loop_table.csv",
        execution_loop_table,
    )
    log_artifact_written_event(artifact_name="execution_loop_table", artifact_path=execution_loop_table_file)
    measurements = workflow["measurements"]
    measurements_file = write_json_artifact(others_dir, "measurements.json", measurements, "measurements")
    log_artifact_written_event(artifact_name="measurements", artifact_path=measurements_file)
    measurement_analysis = build_measurement_analysis(measurements)
    measurement_analysis_file = write_json_artifact(
        others_dir, "measurement_analysis.json", measurement_analysis, "measurement_analysis"
    )
    log_artifact_written_event(artifact_name="measurement_analysis", artifact_path=measurement_analysis_file)
    measurement_analysis_markdown_file = others_dir / "measurement_analysis.md"
    measurement_analysis_markdown_file.write_text(
        render_measurement_analysis_markdown(measurement_analysis),
        encoding="utf-8",
    )
    log_artifact_written_event(artifact_name="measurement_analysis_markdown", artifact_path=measurement_analysis_markdown_file)
    cache_value_analysis = build_cache_value_analysis(measurements)
    cache_value_analysis_file = write_json_artifact(
        others_dir, "cache_value_analysis.json", cache_value_analysis, "cache_value_analysis"
    )
    log_artifact_written_event(artifact_name="cache_value_analysis", artifact_path=cache_value_analysis_file)
    cache_value_analysis_markdown_file = others_dir / "cache_value_analysis.md"
    cache_value_analysis_markdown_file.write_text(
        render_cache_value_markdown(cache_value_analysis),
        encoding="utf-8",
    )
    log_artifact_written_event(artifact_name="cache_value_analysis_markdown", artifact_path=cache_value_analysis_markdown_file)
    kv_hierarchy_analysis = build_kv_hierarchy_analysis(measurements, cache_value_analysis)
    kv_hierarchy_analysis_file = write_json_artifact(
        others_dir, "kv_hierarchy_analysis.json", kv_hierarchy_analysis, "kv_hierarchy_analysis"
    )
    log_artifact_written_event(artifact_name="kv_hierarchy_analysis", artifact_path=kv_hierarchy_analysis_file)
    kv_hierarchy_analysis_markdown_file = others_dir / "kv_hierarchy_analysis.md"
    kv_hierarchy_analysis_markdown_file.write_text(
        render_kv_hierarchy_markdown(kv_hierarchy_analysis),
        encoding="utf-8",
    )
    log_artifact_written_event(artifact_name="kv_hierarchy_analysis_markdown", artifact_path=kv_hierarchy_analysis_markdown_file)
    runtime_log_artifacts = collect_runtime_logs(others_dir, since_iso=run_started_at.isoformat())
    log_lifecycle_event(
        stage="runtime_logs_collected",
        payload={
            "event_kind": "runtime_observation",
            "parent_run_id": parent_run_id,
            "runtime_log_artifacts": runtime_log_artifacts,
        },
    )
    frontend_scheduler_events = parse_frontend_scheduler_events(
        runtime_log_artifacts.get("frontend_log_file")
        if isinstance(runtime_log_artifacts.get("frontend_log_file"), str)
        else None
    )
    worker_request_observations = parse_worker_request_observations(
        runtime_log_artifacts.get("worker_log_file")
        if isinstance(runtime_log_artifacts.get("worker_log_file"), str)
        else None
    )
    runtime_events = build_runtime_events(
        measurements,
        frontend_scheduler_events=frontend_scheduler_events,
        worker_request_observations=worker_request_observations,
    )
    log_lifecycle_event(
        stage="runtime_events_built",
        payload={
            "event_kind": "runtime_observation",
            "parent_run_id": parent_run_id,
            "runtime_event_count": len(runtime_events),
        },
    )
    runtime_events_file = write_runtime_events_jsonl(others_dir, runtime_events)
    log_artifact_written_event(artifact_name="runtime_events_jsonl", artifact_path=runtime_events_file)
    runtime_events_pretty_file = write_json_artifact(
        others_dir, "runtime_events.json", runtime_events, "runtime_events"
    )
    log_artifact_written_event(artifact_name="runtime_events", artifact_path=runtime_events_pretty_file)
    runtime_alignment_analysis = build_runtime_alignment_analysis(
        runtime_events,
        cache_value_analysis,
        kv_hierarchy_analysis,
        workflow["result"],
        runtime_log_artifacts,
    )
    runtime_alignment_analysis_file = write_json_artifact(
        run_dir,
        "runtime_alignment_analysis.json",
        runtime_alignment_analysis,
        "runtime_alignment_analysis",
        annotate=False,
    )
    log_artifact_written_event(artifact_name="runtime_alignment_analysis", artifact_path=runtime_alignment_analysis_file)
    runtime_alignment_analysis_markdown_file = run_dir / "runtime_alignment_analysis.md"
    runtime_alignment_analysis_markdown_file.write_text(
        render_runtime_alignment_markdown(runtime_alignment_analysis),
        encoding="utf-8",
    )
    log_artifact_written_event(artifact_name="runtime_alignment_analysis_markdown", artifact_path=runtime_alignment_analysis_markdown_file)
    runtime_hint_alignment_analysis = build_runtime_hint_alignment_analysis(
        runtime_events,
        workflow["result"],
        runtime_log_artifacts,
    )
    runtime_hint_alignment_analysis_file = write_json_artifact(
        run_dir,
        "runtime_hint_alignment_analysis.json",
        runtime_hint_alignment_analysis,
        "runtime_hint_alignment_analysis",
        annotate=False,
    )
    log_artifact_written_event(
        artifact_name="runtime_hint_alignment_analysis",
        artifact_path=runtime_hint_alignment_analysis_file,
    )
    runtime_hint_alignment_analysis_markdown_file = run_dir / "runtime_hint_alignment_analysis.md"
    runtime_hint_alignment_analysis_markdown_file.write_text(
        render_runtime_hint_alignment_markdown(runtime_hint_alignment_analysis),
        encoding="utf-8",
    )
    log_artifact_written_event(
        artifact_name="runtime_hint_alignment_analysis_markdown",
        artifact_path=runtime_hint_alignment_analysis_markdown_file,
    )

    result = workflow["result"]
    final_summary_file = run_dir / "final_summary.txt"
    final_summary_file.write_text(result["response_text"], encoding="utf-8")
    log_artifact_written_event(artifact_name="final_summary", artifact_path=final_summary_file, related_phase="synthesis")

    workspace_artifacts = collect_workspace_artifacts(run_dir, workspace_dir, auxiliary_dir=others_dir)
    log_lifecycle_event(
        stage="workspace_artifacts_collected",
        payload={
            "event_kind": "workspace",
            "parent_run_id": parent_run_id,
            "workspace_artifacts": workspace_artifacts,
        },
    )
    prompt_evolution_report = build_prompt_evolution_report(
        task=task,
        workflow=workflow,
        frontend_url=args.frontend_url,
        model=args.model,
        app_variant=args.app_variant,
        runtime_log_artifacts=runtime_log_artifacts,
        workspace_metadata=workspace_metadata,
        workspace_artifacts=workspace_artifacts,
    )
    prompt_evolution_report_file = write_json_artifact(
        run_dir,
        "prompt_evolution_report.json",
        prompt_evolution_report,
        "prompt_evolution_report",
        annotate=False,
    )
    log_artifact_written_event(artifact_name="prompt_evolution_report", artifact_path=prompt_evolution_report_file)
    prompt_evolution_report_markdown_file = run_dir / "prompt_evolution_report.md"
    prompt_evolution_report_markdown_file.write_text(
        render_prompt_evolution_markdown(prompt_evolution_report),
        encoding="utf-8",
    )
    log_artifact_written_event(
        artifact_name="prompt_evolution_report_markdown",
        artifact_path=prompt_evolution_report_markdown_file,
    )
    prompt_evolution_report_table_file = write_csv_table(
        run_dir,
        "prompt_evolution_report.csv",
        build_prompt_evolution_csv_rows(prompt_evolution_report),
    )
    log_artifact_written_event(
        artifact_name="prompt_evolution_report_table",
        artifact_path=prompt_evolution_report_table_file,
    )
    prompt_evolution_value_reports = write_prompt_evolution_stage_value_reports(
        run_dir=run_dir,
        prompt_evolution_report=prompt_evolution_report,
        task=task,
        workflow=workflow,
        frontend_url=args.frontend_url,
        model=args.model,
        app_variant=args.app_variant,
        runtime_log_artifacts=runtime_log_artifacts,
        workspace_metadata=workspace_metadata,
        workspace_artifacts=workspace_artifacts,
        value_char_limit=args.prompt_evolution_value_char_limit,
    )
    log_artifact_written_event(
        artifact_name="prompt_evolution_values_index",
        artifact_path=Path(prompt_evolution_value_reports["index_file"]),
    )
    for stage_file in prompt_evolution_value_reports["stage_files"]:
        log_artifact_written_event(
            artifact_name=f"prompt_evolution_values_{stage_file['stage']}",
            artifact_path=Path(stage_file["path"]),
        )
    run_summary_table = build_run_summary_table(
        parent_run_id=parent_run_id,
        task=task,
        model=args.model,
        workspace_metadata=workspace_metadata,
        measurement_analysis=measurement_analysis,
        cache_value_analysis=cache_value_analysis,
        kv_hierarchy_analysis=kv_hierarchy_analysis,
        runtime_alignment_analysis=runtime_alignment_analysis,
        workspace_artifacts=workspace_artifacts,
    )
    measurements_table_file = write_csv_table(others_dir, "measurements_table.csv", build_measurements_table(measurements))
    log_artifact_written_event(artifact_name="measurements_table", artifact_path=measurements_table_file)
    measurement_analysis_table_file = write_csv_table(
        others_dir,
        "measurement_analysis_table.csv",
        build_measurement_analysis_table(measurement_analysis),
    )
    log_artifact_written_event(artifact_name="measurement_analysis_table", artifact_path=measurement_analysis_table_file)
    measurement_summary_table_file = write_csv_table(
        others_dir,
        "measurement_summary_table.csv",
        build_measurement_summary_table(measurement_analysis),
    )
    log_artifact_written_event(artifact_name="measurement_summary_table", artifact_path=measurement_summary_table_file)
    cache_value_table_file = write_csv_table(
        others_dir,
        "cache_value_table.csv",
        build_cache_value_table(cache_value_analysis),
    )
    log_artifact_written_event(artifact_name="cache_value_table", artifact_path=cache_value_table_file)
    cache_value_summary_table_file = write_csv_table(
        others_dir,
        "cache_value_summary_table.csv",
        build_cache_value_summary_table(cache_value_analysis),
    )
    log_artifact_written_event(artifact_name="cache_value_summary_table", artifact_path=cache_value_summary_table_file)
    kv_hierarchy_table_file = write_csv_table(
        others_dir,
        "kv_hierarchy_table.csv",
        build_kv_hierarchy_table(kv_hierarchy_analysis),
    )
    log_artifact_written_event(artifact_name="kv_hierarchy_table", artifact_path=kv_hierarchy_table_file)
    kv_hierarchy_summary_table_file = write_csv_table(
        others_dir,
        "kv_hierarchy_summary_table.csv",
        build_kv_hierarchy_summary_table(kv_hierarchy_analysis),
    )
    log_artifact_written_event(artifact_name="kv_hierarchy_summary_table", artifact_path=kv_hierarchy_summary_table_file)
    runtime_events_table_file = write_csv_table(
        others_dir,
        "runtime_events_table.csv",
        build_runtime_events_table(runtime_events),
    )
    log_artifact_written_event(artifact_name="runtime_events_table", artifact_path=runtime_events_table_file)
    runtime_alignment_table_file = write_csv_table(
        run_dir,
        "runtime_alignment_table.csv",
        build_runtime_alignment_table(runtime_alignment_analysis),
    )
    log_artifact_written_event(artifact_name="runtime_alignment_table", artifact_path=runtime_alignment_table_file)
    runtime_alignment_summary_table_file = write_csv_table(
        others_dir,
        "runtime_alignment_summary_table.csv",
        build_runtime_alignment_summary_table(runtime_alignment_analysis),
    )
    log_artifact_written_event(artifact_name="runtime_alignment_summary_table", artifact_path=runtime_alignment_summary_table_file)
    runtime_hint_alignment_table_file = write_csv_table(
        run_dir,
        "runtime_hint_alignment_table.csv",
        build_runtime_hint_alignment_table(runtime_hint_alignment_analysis),
    )
    log_artifact_written_event(
        artifact_name="runtime_hint_alignment_table",
        artifact_path=runtime_hint_alignment_table_file,
    )
    runtime_hint_alignment_summary_table_file = write_csv_table(
        others_dir,
        "runtime_hint_alignment_summary_table.csv",
        build_runtime_hint_alignment_summary_table(runtime_hint_alignment_analysis),
    )
    log_artifact_written_event(
        artifact_name="runtime_hint_alignment_summary_table",
        artifact_path=runtime_hint_alignment_summary_table_file,
    )
    run_summary_table_file = write_csv_table(others_dir, "run_summary_table.csv", run_summary_table)
    log_artifact_written_event(artifact_name="run_summary_table", artifact_path=run_summary_table_file)
    raw_lifecycle_events = load_logged_events(lifecycle_log_path)
    set_lifecycle_log_file(None)
    stage_lifecycle_trace = build_task_lifecycle_trace(
        raw_lifecycle_events,
        metadata={
            "parent_run_id": parent_run_id,
            "task_instance_id": task.get("instance_id"),
            "task_source": task_source,
            "app_variant": args.app_variant,
            "frontend_url": args.frontend_url,
            "model": args.model,
        },
        runtime_events=runtime_events,
    )
    stage_lifecycle_trace_file = write_json_artifact(
        run_dir,
        "stage_lifecycle_trace.json",
        stage_lifecycle_trace,
        "stage_lifecycle_trace",
        annotate=False,
    )
    stage_lifecycle_markdown_file = run_dir / "stage_lifecycle_trace.md"
    stage_lifecycle_markdown_file.write_text(
        render_task_lifecycle_markdown(stage_lifecycle_trace),
        encoding="utf-8",
    )
    stage_lifecycle_table = build_task_lifecycle_table(stage_lifecycle_trace)
    stage_lifecycle_table_file = write_csv_table(
        run_dir,
        "stage_lifecycle_table.csv",
        stage_lifecycle_table,
    )
    workbook_file = write_excel_workbook(
        others_dir,
        "run_analysis.xlsx",
        {
            "measurements": build_measurements_table(measurements),
            "measurement_summary": build_measurement_summary_table(measurement_analysis),
            "measurement_analysis": build_measurement_analysis_table(measurement_analysis),
            "cache_value": build_cache_value_table(cache_value_analysis),
            "cache_summary": build_cache_value_summary_table(cache_value_analysis),
            "kv_hierarchy": build_kv_hierarchy_table(kv_hierarchy_analysis),
            "kv_summary": build_kv_hierarchy_summary_table(kv_hierarchy_analysis),
            "runtime_events": build_runtime_events_table(runtime_events),
            "runtime_alignment": build_runtime_alignment_table(runtime_alignment_analysis),
            "runtime_summary": build_runtime_alignment_summary_table(runtime_alignment_analysis),
            "runtime_hint_alignment": build_runtime_hint_alignment_table(runtime_hint_alignment_analysis),
            "runtime_hint_summary": build_runtime_hint_alignment_summary_table(runtime_hint_alignment_analysis),
            "stage_lifecycle": stage_lifecycle_table,
            "prompt_evolution_report": build_prompt_evolution_csv_rows(prompt_evolution_report),
            "execution_loop": execution_loop_table,
            "run_summary": run_summary_table,
        },
    )

    auto_run_report = {
        "enabled": env_flag("AGENTBENCH_AUTO_RUN_REPORT", default=True) and not args.no_run_report,
        "success": None,
        "reason": "pending",
    }

    payload = {
        "run_started_at": run_started_at.isoformat(),
        "parent_run_id": parent_run_id,
        "legacy_instance_slug": legacy_instance_slug,
        "frontend_url": args.frontend_url,
        "model": args.model,
        "hint_profile": args.hint_profile,
        "hint_provider": args.hint_provider,
        "hint_json": workflow["resolved_hints"],
        "task": task,
        "active_harness": "agentbench.deepagents_app",
        "app_variant": workflow["app_variant"],
        "deepagents_runtime_source": workflow["deepagents_runtime_source"],
        "task_overrides": workflow.get("task_overrides"),
        "checkpoint_log_file": str(checkpoint_log_path),
        "auto_repo_checkout": auto_repo_checkout,
        "workspace": workspace_metadata,
        "workspace_artifacts": workspace_artifacts,
        "prompt_evolution_report_file": str(prompt_evolution_report_file),
        "prompt_evolution_report_markdown_file": str(prompt_evolution_report_markdown_file),
        "prompt_evolution_report_table_file": str(prompt_evolution_report_table_file),
        "prompt_evolution_value_reports_dir": prompt_evolution_value_reports["directory"],
        "prompt_evolution_value_reports_index_file": prompt_evolution_value_reports["index_file"],
        "prompt_evolution_value_report_files": prompt_evolution_value_reports["stage_files"],
        "prompt_evolution_value_char_limit": args.prompt_evolution_value_char_limit,
        "prompt_evolution_report": prompt_evolution_report,
        "prompt": prompt,
        "decomposition_plan": decomposition_plan,
        "step_results": step_results,
        "plan_file": str(plan_file),
        "step_results_file": str(step_results_file),
        "execution_loop_trace": execution_loop_trace,
        "execution_loop_trace_file": str(execution_loop_trace_file),
        "execution_loop_table_file": str(execution_loop_table_file),
        "measurements_file": str(measurements_file),
        "measurements_summary": summarize_measurements(measurements),
        "measurements_table_file": str(measurements_table_file),
        "measurement_analysis_file": str(measurement_analysis_file),
        "measurement_analysis_markdown_file": str(measurement_analysis_markdown_file),
        "measurement_analysis_table_file": str(measurement_analysis_table_file),
        "measurement_summary_table_file": str(measurement_summary_table_file),
        "measurement_analysis": measurement_analysis,
        "runtime_events_file": str(runtime_events_file),
        "runtime_events_pretty_file": str(runtime_events_pretty_file),
        "runtime_events_table_file": str(runtime_events_table_file),
        "runtime_events": runtime_events,
        "runtime_log_artifacts": runtime_log_artifacts,
        "runtime_alignment_analysis_file": str(runtime_alignment_analysis_file),
        "runtime_alignment_analysis_markdown_file": str(runtime_alignment_analysis_markdown_file),
        "runtime_alignment_table_file": str(runtime_alignment_table_file),
        "runtime_alignment_summary_table_file": str(runtime_alignment_summary_table_file),
        "runtime_alignment_analysis": runtime_alignment_analysis,
        "runtime_hint_alignment_analysis_file": str(runtime_hint_alignment_analysis_file),
        "runtime_hint_alignment_analysis_markdown_file": str(runtime_hint_alignment_analysis_markdown_file),
        "runtime_hint_alignment_table_file": str(runtime_hint_alignment_table_file),
        "runtime_hint_alignment_summary_table_file": str(runtime_hint_alignment_summary_table_file),
        "runtime_hint_alignment_analysis": runtime_hint_alignment_analysis,
        "stage_lifecycle_trace_file": str(stage_lifecycle_trace_file),
        "stage_lifecycle_markdown_file": str(stage_lifecycle_markdown_file),
        "stage_lifecycle_table_file": str(stage_lifecycle_table_file),
        "stage_lifecycle_trace": stage_lifecycle_trace,
        "cache_value_analysis_file": str(cache_value_analysis_file),
        "cache_value_analysis_markdown_file": str(cache_value_analysis_markdown_file),
        "cache_value_table_file": str(cache_value_table_file),
        "cache_value_summary_table_file": str(cache_value_summary_table_file),
        "cache_value_analysis": cache_value_analysis,
        "kv_hierarchy_analysis_file": str(kv_hierarchy_analysis_file),
        "kv_hierarchy_analysis_markdown_file": str(kv_hierarchy_analysis_markdown_file),
        "kv_hierarchy_table_file": str(kv_hierarchy_table_file),
        "kv_hierarchy_summary_table_file": str(kv_hierarchy_summary_table_file),
        "kv_hierarchy_analysis": kv_hierarchy_analysis,
        "run_summary_table_file": str(run_summary_table_file),
        "analysis_workbook_file": str(workbook_file),
        "measurements": measurements,
        "result": result,
        "auto_run_report": auto_run_report,
    }
    save_result(others_dir, annotate_with_provenance(payload, "result"))
    set_checkpoint_log_file(None)

    if auto_run_report["enabled"]:
        transfer_log = resolve_sglang_transfer_log(
            explicit_log=args.sglang_transfer_log,
            run_started_at=run_started_at,
        )
        auto_run_report = build_curated_run_report(
            run_dir=run_dir,
            parent_run_id=parent_run_id,
            transfer_log=transfer_log,
        )
        (others_dir / "auto_run_report.json").write_text(
            json.dumps(auto_run_report, indent=2, default=stringify_unknown),
            encoding="utf-8",
        )
        payload["auto_run_report"] = auto_run_report
        save_result(others_dir, annotate_with_provenance(payload, "result"))
    else:
        auto_run_report["reason"] = "disabled"
        (others_dir / "auto_run_report.json").write_text(
            json.dumps(auto_run_report, indent=2, default=stringify_unknown),
            encoding="utf-8",
        )
        payload["auto_run_report"] = auto_run_report
        save_result(others_dir, annotate_with_provenance(payload, "result"))

    print(f"AgentBench run complete: {parent_run_id}")
    print(f"Run directory: {run_dir}")
    print(f"Result file: {others_dir / 'result.json'}")
    if auto_run_report.get("enabled"):
        print(f"Run report: {auto_run_report.get('report_dir')}")
        print(f"Latest overview: {auto_run_report.get('latest_runs_overview_file')}")
        print(f"All runs overview: {auto_run_report.get('all_runs_overview_file')}")
        print(f"Latest execution prompts: {auto_run_report.get('latest_runs_execution_prompts_file')}")
        print(f"All execution prompts: {auto_run_report.get('all_runs_execution_prompts_file')}")
        if not auto_run_report.get("success"):
            print(f"Run report generation failed: {auto_run_report.get('stderr')}", file=sys.stderr)


if __name__ == "__main__":
    main()
