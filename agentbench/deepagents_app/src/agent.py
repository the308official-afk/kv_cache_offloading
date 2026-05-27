"""Deep Agents app wiring for local Dynamo-backed coding runs.

This is the target location for moving model construction and hint-aware
phase logic out of the repo-local runner and into a source-level Deep Agents app.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any
from collections.abc import Mapping

from agentbench.log_utils import log_checkpoint, log_lifecycle_event

THIS_FILE = Path(__file__).resolve()
APP_ROOT = THIS_FILE.parents[1]
AGENTBENCH_ROOT = APP_ROOT.parents[1]
UPSTREAM_ROOT = AGENTBENCH_ROOT / "upstream" / "deepagents"
CLONED_DEEPAGENTS_LIB_ROOT = UPSTREAM_ROOT / "libs" / "deepagents"
if CLONED_DEEPAGENTS_LIB_ROOT.exists() and str(CLONED_DEEPAGENTS_LIB_ROOT) not in sys.path:
    # Debugging note: this is the "use the downloaded GitHub repo first" hook.
    sys.path.insert(0, str(CLONED_DEEPAGENTS_LIB_ROOT))

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, LocalShellBackend, StateBackend
from langchain_openai import ChatOpenAI

from .prompts import (
    DYNAMO_HINT_NOTES,
    PLANNING_NOTES,
    SYSTEM_PROMPT,
    format_swebench_task_prompt,
)

SKILLS_DIR = APP_ROOT / "skills"
AGENTS_FILE = APP_ROOT / "AGENTS.md"
UPSTREAM_DEPLOY_CODING_AGENT_ROOT = UPSTREAM_ROOT / "examples" / "deploy-coding-agent"

DEFAULT_DYNAMO_HINTS: dict[str, Any] = {
    "priority": 5,
    "reuse_likelihood": 0.9,
    "agent_phase": "execution",
    "latency_sensitivity": 0.7,
    "program_id": "agentbench.deepagents_app",
    "context_type": "software_engineering_long_horizon",
    "expected_output_tokens": 512,
}

DEEPAGENTS_RUNTIME_SOURCE = (
    str(CLONED_DEEPAGENTS_LIB_ROOT)
    if CLONED_DEEPAGENTS_LIB_ROOT.exists()
    else "python_environment"
)

# Builds the per-request tracking payload that we send through logs and Dynamo hints.
def build_request_context(
    *,
    parent_run_id: str | None,
    task_instance_id: str | None,
    phase: str,
    app_variant: str | None,
    step_index: int | None = None,
    step_title: str | None = None,
) -> dict[str, Any]:
    request_id = f"{parent_run_id or 'run'}::{phase}"
    if step_index is not None:
        request_id += f"::{step_index}"
    return {
        "request_id": request_id,
        "parent_run_id": parent_run_id,
        "task_instance_id": task_instance_id,
        "phase": phase,
        "step_index": step_index,
        "step_title": step_title,
        "app_variant": app_variant,
    }


# Pulls out the final AI message from a LangChain / Deep Agents response object.
def _extract_last_ai_message(response: Any) -> Any:
    messages = None
    if isinstance(response, Mapping):
        messages = response.get("messages")
    elif hasattr(response, "get"):
        try:
            messages = response.get("messages")
        except Exception:  # noqa: BLE001
            messages = None
    if messages is None:
        messages = getattr(response, "messages", None)

    if isinstance(messages, list):
        for message in reversed(messages):
            message_type = None
            if isinstance(message, Mapping):
                message_type = message.get("type")
            if message_type is None:
                message_type = getattr(message, "type", None)
            if message_type == "ai":
                return message
    return response


# Reads provider metadata like finish reason and token usage from the final AI message.
def _response_metadata(response: Any) -> dict[str, Any]:
    message = _extract_last_ai_message(response)
    metadata = getattr(message, "response_metadata", None)
    if isinstance(metadata, dict):
        return metadata
    if isinstance(message, dict):
        raw = message.get("response_metadata")
        if isinstance(raw, dict):
            return raw
    return {}


# Reads normalized usage numbers from the final AI message when they are present.
def _usage_metadata(response: Any) -> dict[str, Any]:
    message = _extract_last_ai_message(response)
    metadata = getattr(message, "usage_metadata", None)
    if isinstance(metadata, dict):
        return metadata
    if isinstance(message, dict):
        raw = message.get("usage_metadata")
        if isinstance(raw, dict):
            return raw
    return {}


# Builds the measurement row we save for one model call.
def build_measurement_record(
    *,
    phase: str,
    model: str,
    frontend_url: str,
    prompt: str,
    hints: dict[str, Any],
    response: Any,
    started_at_perf: float,
    finished_at_perf: float,
    task_index: int | None,
    task_source: str | None,
    task_metadata: dict[str, Any] | None,
    request_context: dict[str, Any] | None = None,
    step_index: int | None = None,
    step_title: str | None = None,
    app_variant: str | None = None,
) -> dict[str, Any]:
    response_metadata = _response_metadata(response)
    usage_metadata = _usage_metadata(response)
    token_usage = response_metadata.get("token_usage", {}) if isinstance(response_metadata, dict) else {}
    prompt_token_details = token_usage.get("prompt_tokens_details", {}) if isinstance(token_usage, dict) else {}

    return {
        "task_index": task_index,
        "task_source": task_source,
        "task_metadata": task_metadata or {},
        "app_variant": app_variant,
        "request_context": request_context or {},
        "phase": phase,
        "step_index": step_index,
        "step_title": step_title,
        "frontend_url": frontend_url,
        "model": model,
        "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        "hints": hints,
        "latency_ms": round((finished_at_perf - started_at_perf) * 1000, 3),
        "prompt_chars": len(prompt),
        "prompt_lines": len(prompt.splitlines()),
        "prompt_preview": _prompt_preview(prompt),
        "finish_reason": response_metadata.get("finish_reason"),
        "provider_response_id": response_metadata.get("id"),
        "model_name_reported": response_metadata.get("model_name"),
        "input_tokens": usage_metadata.get("input_tokens"),
        "output_tokens": usage_metadata.get("output_tokens"),
        "total_tokens": usage_metadata.get("total_tokens"),
        "cached_input_tokens": (
            usage_metadata.get("input_token_details", {}) or {}
        ).get("cache_read"),
        "prompt_tokens": token_usage.get("prompt_tokens") if isinstance(token_usage, dict) else None,
        "completion_tokens": token_usage.get("completion_tokens") if isinstance(token_usage, dict) else None,
        "total_tokens_reported": token_usage.get("total_tokens") if isinstance(token_usage, dict) else None,
        "cached_prompt_tokens": prompt_token_details.get("cached_tokens") if isinstance(prompt_token_details, dict) else None,
    }


# Stores the full prompt plus a few lightweight prompt stats for debugging.
def build_prompt_snapshot(prompt: str) -> dict[str, Any]:
    return {
        "prompt": prompt,
        "prompt_chars": len(prompt),
        "prompt_lines": len(prompt.splitlines()),
        "prompt_preview": _prompt_preview(prompt),
    }


# Stores the final response text plus the metadata we may want to inspect later.
def build_response_snapshot(response: Any) -> dict[str, Any]:
    response_metadata = _response_metadata(response)
    usage_metadata = _usage_metadata(response)
    text = response_text(response)
    return {
        "response_text": text,
        "response_preview": _prompt_preview(text),
        "response_metadata": response_metadata,
        "usage_metadata": usage_metadata,
    }


# Creates a short one-line preview so logs stay readable.
def _prompt_preview(prompt: str) -> str:
    lines = [line.strip() for line in prompt.splitlines() if line.strip()]
    if not lines:
        return ""
    return " ".join(lines[:3])


# Writes a structured checkpoint entry for major harness events.
def log_outbound_harness_request(
    *,
    check_point: str,
    task_index: int | None,
    payload: dict[str, Any],
) -> None:
    log_checkpoint(
        check_point=check_point,
        task_index=task_index,
        payload=payload,
    )


# Chooses which instruction bundle to use: our local app or the upstream example app.
def resolve_app_root(app_variant: str = "local") -> Path:
    # Debugging note: this selects which instruction/skill surface the run uses.
    # "local" = our adapted app; "upstream_deploy_coding_agent" = cloned upstream example content.
    if app_variant == "local":
        return APP_ROOT
    if app_variant == "upstream_deploy_coding_agent":
        return UPSTREAM_DEPLOY_CODING_AGENT_ROOT
    raise ValueError(f"Unsupported app_variant: {app_variant}")


# Loads AGENTS.md and skills text into one system prompt for the selected app variant.
def load_agent_instructions(app_variant: str = "local") -> str:
    """Load the app-level instructions from AGENTS.md and skill docs.

    This makes `deepagents_app/` the active configuration surface instead of
    keeping the main workflow guidance embedded in the outer runner.
    """
    # Debugging note: this is where AGENTS.md and skills are folded into the live agent prompt.

    app_root = resolve_app_root(app_variant)
    agents_file = app_root / "AGENTS.md"
    skills_dir = app_root / "skills"

    if app_variant == "local":
        parts = [SYSTEM_PROMPT, PLANNING_NOTES, DYNAMO_HINT_NOTES]
    else:
        parts = []
    if agents_file.exists():
        parts.append(agents_file.read_text(encoding="utf-8").strip())

    if skills_dir.exists():
        for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
            skill_text = skill_path.read_text(encoding="utf-8").strip()
            if skill_text:
                parts.append(f"Skill reference: {skill_path.parent.name}\n{skill_text}")

    return "\n\n".join(part for part in parts if part)


# Converts a full chat-completions URL into the base /v1 URL expected by ChatOpenAI.
def frontend_base_url(frontend_url: str) -> str:
    # Debugging note: AgentBench receives a chat-completions URL,
    # but the OpenAI-compatible client wants the /v1 base URL.
    if "/v1/chat/completions" in frontend_url:
        return frontend_url.replace("/v1/chat/completions", "/v1")
    return frontend_url.rstrip("/")


# Merges default Dynamo hints with caller overrides and stamps the current phase on them.
def build_phase_hints(base_hints: dict[str, Any] | None = None, *, phase: str = "execution") -> dict[str, Any]:
    # Debugging note: this is the hint adaptation hook for Dynamo.
    # Every planning/step/synthesis request gets its own phase-tagged hint payload.
    hints = dict(DEFAULT_DYNAMO_HINTS)
    if base_hints:
        hints.update(base_hints)
    hints["agent_phase"] = phase
    return hints


def ensure_hint_probe_id(hints: dict[str, Any], *, parent_run_id: str | None) -> dict[str, Any]:
    """Attach a stable probe marker so hint propagation can be traced across layers."""
    resolved = dict(hints)
    if not resolved.get("hint_probe_id"):
        resolved["hint_probe_id"] = f"{parent_run_id or 'run'}::hint_probe"
    return resolved


def build_phase_probe_id(*, parent_run_id: str | None, phase: str, sequence_index: int) -> str:
    return f"{parent_run_id or 'run'}::{phase}::{sequence_index}"


# Builds the ChatOpenAI client that sends requests to the local Dynamo frontend.
def build_dynamo_chat_model(
    *,
    frontend_url: str,
    model: str,
    hint_payload: dict[str, Any] | None = None,
    request_context: dict[str, Any] | None = None,
    max_tokens: int = 2048,
) -> ChatOpenAI:
    # Debugging note: this is the Deep Agents -> Dynamo adaptation hook.
    # Instead of sending requests to a cloud model endpoint, the app points ChatOpenAI at local Dynamo.
    payload = hint_payload or dict(DEFAULT_DYNAMO_HINTS)
    context = request_context or {}
    extra_body = {
        "nvext": {
            "agent_hints": payload,
            "request_context": context,
        },
    }
    if os.environ.get("AGENTBENCH_SEND_TOP_LEVEL_EXTRA_ARGS", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        runtime_observability = {
            "agent_hints": payload,
            "agent_hints_source": "agentbench.request_wrapper",
            "agent_hints_keys": sorted(str(key) for key in payload),
            "hint_probe_id": payload.get("hint_probe_id"),
            "request_context": context,
            "nvext": {
                "agent_hints": payload,
                "request_context": context,
            },
        }
        extra_body["extra_args"] = {
            "runtime_observability": runtime_observability,
        }
    return ChatOpenAI(
        model=model,
        base_url=frontend_base_url(frontend_url),
        api_key="dummy",
        temperature=0.0,
        max_tokens=max_tokens,
        timeout=300,
        extra_body=extra_body,
    )


# Builds the Deep Agents filesystem/shell backend rooted at the task workspace.
def build_agent_backend(workspace_dir: Path | None):
    root_dir = str(workspace_dir or Path.cwd())
    ephemeral_backend = StateBackend()
    shell_backend = LocalShellBackend(
        root_dir=root_dir,
        inherit_env=True,
        env=os.environ.copy(),
    )
    return CompositeBackend(
        default=shell_backend,
        routes={
            "/memories/": ephemeral_backend,
            "/conversation_history/": ephemeral_backend,
        },
    )


# Creates the actual Deep Agents coding agent wired to local Dynamo.
def build_coding_agent(
    *,
    frontend_url: str,
    model: str,
    workspace_dir: Path | None,
    base_hints: dict[str, Any] | None = None,
    phase: str = "execution",
    app_variant: str = "local",
    request_context: dict[str, Any] | None = None,
    prompt_stage: str = "step_agent_system_prompt_loaded",
):
    """Create the Deep Agents coding harness backed by a local Dynamo endpoint.
    """
    # Debugging note: this is the Deep Agents harness construction point.
    # The returned agent is powered by create_deep_agent(...) but wired to local Dynamo.

    system_prompt = load_agent_instructions(app_variant)
    log_lifecycle_event(
        stage=prompt_stage,
        payload={
            "event_kind": "prompt_context",
            "phase": phase,
            "app_variant": app_variant,
            "request_context": request_context or {},
            "system_prompt": system_prompt,
            "system_prompt_chars": len(system_prompt),
            "system_prompt_lines": len(system_prompt.splitlines()),
            "system_prompt_preview": _prompt_preview(system_prompt),
        },
    )
    llm = build_dynamo_chat_model(
        frontend_url=frontend_url,
        model=model,
        hint_payload=build_phase_hints(base_hints, phase=phase),
        request_context=request_context,
    )
    backend = build_agent_backend(workspace_dir)
    return create_deep_agent(
        model=llm,
        system_prompt=system_prompt,
        backend=backend,
    )


# Extracts plain text from the final response object no matter how it is nested.
def response_text(response) -> str:
    if isinstance(response, Mapping):
        message = _extract_last_ai_message(response)
        if message is not response:
            return response_text(message)
        content = response.get("content")
        if content is not None:
            return response_text(content)
    content = getattr(response, "content", None)
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
    if isinstance(response, str):
        return response
    return str(content if content is not None else response)


# Runs one end-to-end baseline Deep Agents call for a single SWE-bench task.
def execute_baseline_agent(
    *,
    frontend_url: str,
    model: str,
    base_hints: dict[str, Any],
    task_prompt: str,
    workspace_dir: Path | None,
    app_variant: str = "local",
    task_index: int | None = None,
    task_source: str | None = None,
    task_metadata: dict[str, Any] | None = None,
    parent_run_id: str | None = None,
) -> dict:
    baseline_hints = build_phase_hints(base_hints, phase="baseline_execution")
    baseline_hints["expected_output_tokens"] = 2048
    request_context = build_request_context(
        parent_run_id=parent_run_id,
        task_instance_id=(task_metadata or {}).get("instance_id"),
        phase="baseline_execution",
        app_variant=app_variant,
    )
    log_lifecycle_event(
        stage="baseline_agent_request_prepared",
        payload={
            "event_kind": "request_context",
            "phase": "baseline_execution",
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "frontend_url": frontend_url,
            "model": model,
            "hints": baseline_hints,
            "request_context": request_context,
            "workspace_dir": str(workspace_dir) if workspace_dir is not None else None,
        },
    )
    agent = build_coding_agent(
        frontend_url=frontend_url,
        model=model,
        workspace_dir=workspace_dir,
        base_hints=baseline_hints,
        phase="baseline_execution",
        app_variant=app_variant,
        request_context=request_context,
        prompt_stage="baseline_agent_system_prompt_loaded",
    )
    log_outbound_harness_request(
        check_point="2. Baseline Deep Agents request leaving harness",
        task_index=task_index,
        payload={
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "phase": "baseline_execution",
            "prompt_preview": _prompt_preview(task_prompt),
            "prompt": task_prompt,
            "hints": baseline_hints,
            "request_context": request_context,
            "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        },
    )
    log_lifecycle_event(
        stage="baseline_agent_request_dispatched",
        payload={
            "event_kind": "request_dispatch",
            "phase": "baseline_execution",
            "frontend_url": frontend_url,
            "model": model,
            "hints": baseline_hints,
            "request_context": request_context,
            **build_prompt_snapshot(task_prompt),
        },
    )
    original_cwd = Path.cwd()
    try:
        if workspace_dir is not None:
            os.chdir(workspace_dir)
        started_at_perf = time.perf_counter()
        response = agent.invoke({"messages": [{"role": "user", "content": task_prompt}]})
        finished_at_perf = time.perf_counter()
    finally:
        os.chdir(original_cwd)
    measurement = build_measurement_record(
        phase="baseline_execution",
        model=model,
        frontend_url=frontend_url,
        prompt=task_prompt,
        hints=baseline_hints,
        response=response,
        started_at_perf=started_at_perf,
        finished_at_perf=finished_at_perf,
        task_index=task_index,
        task_source=task_source,
        task_metadata=task_metadata,
        request_context=request_context,
        app_variant=task_metadata.get("app_variant") if task_metadata else None,
    )
    log_lifecycle_event(
        stage="baseline_agent_response_received",
        payload={
            "event_kind": "response",
            "phase": "baseline_execution",
            "request_context": request_context,
            "measurement": measurement,
            **build_response_snapshot(response),
        },
    )
    return {
        "baseline_hints": baseline_hints,
        "baseline_prompt": task_prompt,
        "response": response,
        "response_text": response_text(response),
        "measurement": measurement,
    }


def build_phase_prompt(
    *,
    phase: str,
    task_prompt: str,
    planning_text: str = "",
    execution_text: str = "",
    patch_text: str = "",
) -> str:
    if phase == "planning":
        return (
            "Phase: planning\n\n"
            "Read the SWE-bench task and produce a concise implementation plan. "
            "Do not edit files in this phase. Identify likely files, risks, and the "
            "smallest next coding steps.\n\n"
            f"{task_prompt}"
        )
    if phase == "execution":
        return (
            "Phase: execution\n\n"
            "Use the plan to implement the SWE-bench fix in the workspace. "
            "Make focused code changes only. Run lightweight checks if practical.\n\n"
            "Planning output:\n"
            f"{planning_text or '(no planning output captured)'}\n\n"
            f"{task_prompt}"
        )
    if phase == "patch_generation":
        return (
            "Phase: patch_generation\n\n"
            "Inspect the current workspace changes and consolidate the final patch. "
            "Do not start a broad refactor. If no edits are needed, summarize why. "
            "Return the changed files, intended behavior, and any checks run.\n\n"
            "Planning output:\n"
            f"{planning_text or '(no planning output captured)'}\n\n"
            "Execution output:\n"
            f"{execution_text or '(no execution output captured)'}"
        )
    if phase == "review":
        return (
            "Phase: review\n\n"
            "Review the current patch for bugs, missing tests, and behavioral risk. "
            "Keep the review concise and actionable. Do not undo unrelated changes.\n\n"
            "Planning output:\n"
            f"{planning_text or '(no planning output captured)'}\n\n"
            "Execution output:\n"
            f"{execution_text or '(no execution output captured)'}\n\n"
            "Patch-generation output:\n"
            f"{patch_text or '(no patch-generation output captured)'}"
        )
    raise ValueError(f"Unsupported phase: {phase}")


def execute_phase_agent(
    *,
    phase: str,
    sequence_index: int,
    frontend_url: str,
    model: str,
    base_hints: dict[str, Any],
    prompt: str,
    workspace_dir: Path | None,
    app_variant: str = "local",
    task_index: int | None = None,
    task_source: str | None = None,
    task_metadata: dict[str, Any] | None = None,
    parent_run_id: str | None = None,
    step_title: str | None = None,
    expected_output_tokens: int = 1024,
) -> dict:
    phase_hints = build_phase_hints(base_hints, phase=phase)
    phase_hints["hint_probe_id"] = build_phase_probe_id(
        parent_run_id=parent_run_id,
        phase=phase,
        sequence_index=sequence_index,
    )
    phase_hints["expected_output_tokens"] = expected_output_tokens
    phase_hints["phase_sequence_index"] = sequence_index
    request_context = build_request_context(
        parent_run_id=parent_run_id,
        task_instance_id=(task_metadata or {}).get("instance_id"),
        phase=phase,
        app_variant=app_variant,
        step_index=sequence_index,
        step_title=step_title or phase.replace("_", " ").title(),
    )
    log_lifecycle_event(
        stage=f"{phase}_request_prepared",
        payload={
            "event_kind": "request_context",
            "phase": phase,
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "frontend_url": frontend_url,
            "model": model,
            "hints": phase_hints,
            "request_context": request_context,
            "workspace_dir": str(workspace_dir) if workspace_dir is not None else None,
        },
    )
    agent = build_coding_agent(
        frontend_url=frontend_url,
        model=model,
        workspace_dir=workspace_dir,
        base_hints=phase_hints,
        phase=phase,
        app_variant=app_variant,
        request_context=request_context,
        prompt_stage=f"{phase}_agent_system_prompt_loaded",
    )
    log_outbound_harness_request(
        check_point=f"2. Deep Agents {phase} request leaving harness",
        task_index=task_index,
        payload={
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "phase": phase,
            "prompt_preview": _prompt_preview(prompt),
            "prompt": prompt,
            "hints": phase_hints,
            "request_context": request_context,
            "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        },
    )
    log_lifecycle_event(
        stage=f"{phase}_request_dispatched",
        payload={
            "event_kind": "request_dispatch",
            "phase": phase,
            "frontend_url": frontend_url,
            "model": model,
            "hints": phase_hints,
            "request_context": request_context,
            **build_prompt_snapshot(prompt),
        },
    )
    original_cwd = Path.cwd()
    try:
        if workspace_dir is not None:
            os.chdir(workspace_dir)
        started_at_perf = time.perf_counter()
        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        finished_at_perf = time.perf_counter()
    finally:
        os.chdir(original_cwd)
    measurement = build_measurement_record(
        phase=phase,
        model=model,
        frontend_url=frontend_url,
        prompt=prompt,
        hints=phase_hints,
        response=response,
        started_at_perf=started_at_perf,
        finished_at_perf=finished_at_perf,
        task_index=task_index,
        task_source=task_source,
        task_metadata=task_metadata,
        request_context=request_context,
        step_index=sequence_index,
        step_title=step_title,
        app_variant=app_variant,
    )
    log_lifecycle_event(
        stage=f"{phase}_response_received",
        payload={
            "event_kind": "response",
            "phase": phase,
            "request_context": request_context,
            "measurement": measurement,
            **build_response_snapshot(response),
        },
    )
    return {
        "phase": phase,
        "sequence_index": sequence_index,
        "hints": phase_hints,
        "request_context": request_context,
        "prompt": prompt,
        "response": response,
        "response_text": response_text(response),
        "measurement": measurement,
    }


def combine_phase_response_text(phase_results: list[dict[str, Any]]) -> str:
    parts = ["# Phased SWE-bench Agent Run", ""]
    for phase_result in phase_results:
        phase = str(phase_result.get("phase") or "unknown")
        text = str(phase_result.get("response_text") or "").strip()
        parts.extend([f"## {phase}", "", text or "(no response text)", ""])
    return "\n".join(parts).strip() + "\n"


# Main entry point for one task: build the prompt, run phased agent calls, and package artifacts.
def run_task_workflow(
    *,
    frontend_url: str,
    model: str,
    task: dict,
    base_hints: dict[str, Any] | None = None,
    step_limit: int = 4,
    workspace_dir: Path | None = None,
    app_variant: str = "local",
    task_index: int | None = None,
    task_source: str | None = None,
    parent_run_id: str | None = None,
) -> dict:
    """Run the active phased Deep Agents workflow for one task."""
    # Debugging note: this is the app-layer orchestration entry point.
    # The wrapper calls this once per run, and this function owns:
    # prompt building, phase-tagged Deep Agents requests, and returned artifacts.

    prompt = format_swebench_task_prompt(task)
    resolved_hints = dict(DEFAULT_DYNAMO_HINTS)
    if base_hints:
        resolved_hints.update(base_hints)
    resolved_hints = ensure_hint_probe_id(resolved_hints, parent_run_id=parent_run_id)
    task_metadata = {
        "instance_id": task.get("instance_id"),
        "repo": task.get("repo"),
        "app_variant": app_variant,
    }
    log_lifecycle_event(
        stage="task_workflow_started",
        payload={
            "event_kind": "workflow",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "parent_run_id": parent_run_id,
            "frontend_url": frontend_url,
            "model": model,
            "step_limit": step_limit,
            "workspace_dir": str(workspace_dir) if workspace_dir is not None else None,
            "app_variant": app_variant,
        },
    )
    log_lifecycle_event(
        stage="task_prompt_built",
        payload={
            "event_kind": "prompt",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "workspace_dir": str(workspace_dir) if workspace_dir is not None else None,
            **build_prompt_snapshot(prompt),
        },
    )
    log_lifecycle_event(
        stage="workflow_hints_resolved",
        payload={
            "event_kind": "hints",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "resolved_hints": resolved_hints,
            "step_limit": step_limit,
        },
    )
    if os.environ.get("AGENTBENCH_WORKFLOW_MODE", "phased").lower() in {"baseline", "single"}:
        result = execute_baseline_agent(
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            task_prompt=prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
        )
        measurements = [result["measurement"]]
        decomposition_plan = {
            "steps": [],
            "planning_hints": None,
            "planning_prompt": None,
            "planning_response_text": None,
            "measurement": None,
        }
        step_results: list[dict] = []
        phase_results = [result]
    else:
        phase_results: list[dict[str, Any]] = []
        planning_prompt = build_phase_prompt(phase="planning", task_prompt=prompt)
        planning_result = execute_phase_agent(
            phase="planning",
            sequence_index=0,
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            prompt=planning_prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
            step_title="Plan SWE-bench fix",
            expected_output_tokens=768,
        )
        phase_results.append(planning_result)

        execution_prompt = build_phase_prompt(
            phase="execution",
            task_prompt=prompt,
            planning_text=planning_result["response_text"],
        )
        execution_result = execute_phase_agent(
            phase="execution",
            sequence_index=0,
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            prompt=execution_prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
            step_title="Implement SWE-bench fix",
            expected_output_tokens=2048,
        )
        phase_results.append(execution_result)

        patch_prompt = build_phase_prompt(
            phase="patch_generation",
            task_prompt=prompt,
            planning_text=planning_result["response_text"],
            execution_text=execution_result["response_text"],
        )
        patch_result = execute_phase_agent(
            phase="patch_generation",
            sequence_index=0,
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            prompt=patch_prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
            step_title="Consolidate patch",
            expected_output_tokens=1024,
        )
        phase_results.append(patch_result)

        review_prompt = build_phase_prompt(
            phase="review",
            task_prompt=prompt,
            planning_text=planning_result["response_text"],
            execution_text=execution_result["response_text"],
            patch_text=patch_result["response_text"],
        )
        review_result = execute_phase_agent(
            phase="review",
            sequence_index=0,
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            prompt=review_prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
            step_title="Review patch",
            expected_output_tokens=1024,
        )
        phase_results.append(review_result)

        measurements = [phase_result["measurement"] for phase_result in phase_results]
        decomposition_plan = {
            "steps": [
                {
                    "phase": "planning",
                    "title": "Plan SWE-bench fix",
                    "hint_probe_id": planning_result["hints"].get("hint_probe_id"),
                },
                {
                    "phase": "execution",
                    "title": "Implement SWE-bench fix",
                    "hint_probe_id": execution_result["hints"].get("hint_probe_id"),
                },
                {
                    "phase": "patch_generation",
                    "title": "Consolidate patch",
                    "hint_probe_id": patch_result["hints"].get("hint_probe_id"),
                },
                {
                    "phase": "review",
                    "title": "Review patch",
                    "hint_probe_id": review_result["hints"].get("hint_probe_id"),
                },
            ],
            "planning_hints": planning_result["hints"],
            "planning_prompt": planning_result["prompt"],
            "planning_response_text": planning_result["response_text"],
            "measurement": planning_result["measurement"],
        }
        step_results = [
            {
                "phase": phase_result["phase"],
                "sequence_index": phase_result["sequence_index"],
                "request_context": phase_result["request_context"],
                "hints": phase_result["hints"],
                "response_text": phase_result["response_text"],
                "measurement": phase_result["measurement"],
            }
            for phase_result in phase_results
        ]
        primary_result = execution_result
        result = {
            **primary_result,
            "baseline_hints": primary_result["hints"],
            "baseline_prompt": primary_result["prompt"],
            "response_text": combine_phase_response_text(phase_results),
            "phase_results": [
                {
                    "phase": phase_result["phase"],
                    "sequence_index": phase_result["sequence_index"],
                    "request_context": phase_result["request_context"],
                    "hints": phase_result["hints"],
                    "prompt": phase_result["prompt"],
                    "response_text": phase_result["response_text"],
                    "measurement": phase_result["measurement"],
                }
                for phase_result in phase_results
            ],
        }
    phase_names = [str(phase_result.get("phase") or "") for phase_result in phase_results]
    log_lifecycle_event(
        stage="phased_requests_completed",
        payload={
            "event_kind": "workflow",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "parent_run_id": parent_run_id,
            "phases": phase_names,
            "phase_count": len(phase_names),
            "measurement_count": len(measurements),
        },
    )
    log_lifecycle_event(
        stage="task_workflow_completed",
        payload={
            "event_kind": "workflow",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "parent_run_id": parent_run_id,
            "step_count": len(step_results),
            "measurement_count": len(measurements),
            "plan_steps": decomposition_plan.get("steps", []),
            "final_response_preview": _prompt_preview(result["response_text"]),
        },
    )
    return {
        "prompt": prompt,
        "resolved_hints": resolved_hints,
        "app_variant": app_variant,
        "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        "decomposition_plan": decomposition_plan,
        "step_results": step_results,
        "phase_results": phase_results,
        "result": result,
        "measurements": measurements,
    }
